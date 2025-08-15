# handlers/messages.py
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import Settings
from utils.session_manager import SessionManager
from services.ai_service import AIService
from services.program_search import ProgramSearchService
from services.lead_service import LeadService


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_message = update.message.text
    user_id = update.effective_user.id

    # Получаем сервисы из bot_data
    session_manager: SessionManager = context.bot_data['session_manager']
    ai_service: AIService = context.bot_data['ai_service']
    program_search: ProgramSearchService = context.bot_data['program_search']
    lead_service: LeadService = context.bot_data['lead_service']

    # Получаем сессию пользователя
    session = session_manager.get_or_create_session(user_id)
    session.conversation_history.append(f"Пользователь: {user_message}")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Специальные команды
    if "хочу учиться" in user_message.lower():
        session.stage = "collecting_info"
        session.profile['question_stage'] = 'degree'

        response = """
Супер! Поможем найти отличный вариант 🎯

Для начала - какой уровень образования планируешь?
🎓 Бакалавриат (первое высшее)
🎓 Магистратура (уже есть диплом бакалавра)
        """
        await update.message.reply_text(response)
        session_manager.save_session(session)
        return

    elif "связаться с менеджером" in user_message.lower():
        await update.message.reply_text(Settings.CONTACT_MESSAGE)
        # TODO: Уведомить менеджера
        return

    elif "процессе" in user_message.lower():
        await update.message.reply_text(Settings.PROCESS_INFO)
        return

    # Поэтапный сбор информации
    if session.stage == "collecting_info":
        response = await handle_step_by_step_collection(user_message, session, program_search)
        await update.message.reply_text(response)
        session_manager.save_session(session)
        return

    # Основная логика AI
    ai_response, interest_score = await ai_service.get_response(user_message, session.profile)
    session.interest_score = max(session.interest_score, interest_score)
    session.conversation_history.append(f"Бот: {ai_response}")

    # Проверяем готовность к передаче менеджеру
    if lead_service.should_notify_manager(session):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("📞 Связаться с менеджером", callback_data="connect_manager")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        ai_response += "\n\n💡 Похоже, вы серьезно заинтересованы! Хотите обсудить детали с нашим менеджером?"
        await update.message.reply_text(ai_response, reply_markup=reply_markup)
    else:
        await update.message.reply_text(ai_response)

    session_manager.save_session(session)


async def handle_step_by_step_collection(user_message: str, session, program_search) -> str:
    """Поэтапный сбор информации о пользователе"""
    current_stage = session.profile.get('question_stage', 'degree')

    # Извлекаем информацию из ответа
    await extract_user_info(user_message, session)

    if current_stage == 'degree':
        if 'degree' in session.profile:
            session.profile['question_stage'] = 'field'
            return """
Понятно! А какая область тебя интересует? 🤔

Например:
💻 ИТ и программирование
🤖 Искусственный интеллект  
📊 Data Science и аналитика
💼 Бизнес и менеджмент

Или что-то другое? Просто напиши своими словами!
            """
        else:
            return "Не совсем понял 🤔 Бакалавриат или магистратура?"

    elif current_stage == 'field':
        if 'field' in session.profile:
            session.profile['question_stage'] = 'budget'
            return """
Отлично! Теперь важный вопрос про бюджет 💰

Сколько примерно готов тратить в год на обучение?

💡 Подсказка: есть бесплатные программы в Германии, Финляндии, Швеции
💰 Платные варианты от €2000 в Чехии до €15000+ в частных вузах

Напиши примерную сумму или "хочу бесплатно" 😊
            """
        else:
            return "Какая область интересует больше всего? ИТ, бизнес, медицина или что-то другое?"

    elif current_stage == 'budget':
        if 'max_budget' in session.profile or any(
                word in user_message.lower() for word in ['бесплатно', 'без платы', 'даром']):
            session.profile['question_stage'] = 'complete'
            session.stage = "showing_results"

            # Ищем подходящие программы
            programs = program_search.search_programs(session.profile)
            return program_search.format_programs_response(programs)
        else:
            return "Не уловил сумму 🤔 Можешь написать примерный бюджет в евро или 'бесплатно'?"

    return "Что-то пошло не так 😅 Давай начнем сначала - какой уровень образования планируешь?"


async def extract_user_info(message: str, session):
    """Извлечение информации о пользователе из сообщения"""
    message_lower = message.lower()

    # Уровень образования
    if any(word in message_lower for word in ['магистр', 'магистратура', 'магистерская', 'второе высшее']):
        session.profile['degree'] = 'магистратура'
    elif any(word in message_lower for word in ['бакалавр', 'бакалавриат', 'первое высшее', 'первое образование']):
        session.profile['degree'] = 'бакалавриат'
    elif any(word in message_lower for word in ['школу', 'школы', 'окончил школу', 'выпускник', '11 класс']):
        session.profile['degree'] = 'бакалавриат'
    elif any(word in message_lower for word in ['диплом', 'высшее', 'университет окончил']):
        session.profile['degree'] = 'магистратура'

    # Область интересов
    fields = []
    if any(word in message_lower for word in ['ит', 'программирование', 'компьютер', 'софт', 'разработка', 'кодинг']):
        fields.append('ИТ')
    if any(word in message_lower for word in ['ии', 'искусственный интеллект', 'ai', 'машинное обучение', 'ml']):
        fields.append('ИИ')
    if any(word in message_lower for word in
           ['data science', 'данные', 'аналитика', 'большие данные', 'анализ данных']):
        fields.append('Data Science')
    if any(word in message_lower for word in ['бизнес', 'менеджмент', 'управление', 'mba', 'экономика']):
        fields.append('бизнес')

    if fields:
        session.profile['field'] = fields

    # Бюджет
    import re
    budget_patterns = [
        r'(\d+)[^\d]*(?:евро|€|euro)',
        r'(\d+)[^\d]*(?:долларов?|\$|usd)',
        r'(\d+)[^\d]*(?:тысяч?|k)',
        r'до\s*(\d+)',
        r'(\d+)\s*в\s*год'
    ]

    for pattern in budget_patterns:
        budget_match = re.search(pattern, message_lower)
        if budget_match:
            budget = int(budget_match.group(1))

            if 'тысяч' in message_lower or 'k' in message_lower:
                budget *= 1000
            elif 'долларов' in message_lower or '$' in message_lower:
                budget = int(budget * 0.85)

            session.profile['max_budget'] = budget
            break

    # Бесплатное обучение
    if any(word in message_lower for word in ['бесплатно', 'без платы', 'даром', 'free', 'не платить', '0']):
        session.profile['max_budget'] = 0

    # Язык обучения
    if any(word in message_lower for word in ['английский', 'english', 'англ', 'ielts', 'toefl']):
        session.profile['language'] = 'английский'