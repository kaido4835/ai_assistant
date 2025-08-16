# handlers/messages.py
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import Settings
from utils.session_manager import SessionManager
from services.ai_service import AIService
from services.program_search import ProgramSearchService
from services.lead_service import LeadService
from handlers.operator import OperatorHandler


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""

    # Получаем обработчик операторов
    if 'operator_handler' not in context.bot_data:
        context.bot_data['operator_handler'] = OperatorHandler()

    operator_handler = context.bot_data['operator_handler']

    # Проверяем, не пытается ли оператор ответить пользователю
    if update.message.text.startswith('/reply_'):
        if await operator_handler.handle_operator_reply(update, context):
            return

    # Проверяем команды для операторов
    if update.message.text == '/help_operator':
        await send_operator_help(update, context)
        return
    elif update.message.text == '/stats':
        await operator_handler.get_operator_stats(update, context)
        return

    # Проверяем, не подключен ли пользователь к оператору
    user_id = update.effective_user.id
    if await operator_handler.handle_user_message_to_operator(update, context):
        return

    # Остальная логика обработки сообщений (ваш существующий код)
    user_message = update.message.text

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
        # Используем новую систему операторов
        await operator_handler.request_operator(update, context)
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


async def send_operator_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка справки для оператора"""
    help_text = """
📋 **Справка для операторов**

**Основные команды:**
• `/reply_USER_ID текст` - ответить клиенту
• `/stats` - статистика работы
• `/help_operator` - эта справка

**Примеры использования:**
• `/reply_123456 Добро пожаловать! Чем могу помочь?`
• `/reply_789012 Сейчас подберу программы под ваши критерии`

**Быстрые ответы:**
• "Добро пожаловать! Чем могу помочь?"
• "Сейчас подберу программы под ваши критерии"
• "Отправлю вам подробную информацию на email"
• "Давайте обсудим ваши образовательные цели"

**Правила работы:**
✅ Отвечайте в течение 2-3 минут
✅ Задавайте уточняющие вопросы
✅ Предлагайте конкретные решения
✅ Используйте кнопки для управления диалогами
❌ Не оставляйте клиентов без ответа
❌ Не давайте ложных обещаний

**Статусы клиентов:**
🔥 Горячий лид - готов подавать документы
🔶 Теплый лид - активно интересуется
🔵 Холодный лид - собирает информацию
    """

    await update.message.reply_text(help_text)


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
            elif 'долларов' in message_lower or '' in message_lower:
                budget = int(budget * 0.85)

            session.profile['max_budget'] = budget
            break

    # Бесплатное обучение
    if any(word in message_lower for word in ['бесплатно', 'без платы', 'даром', 'free', 'не платить', '0']):
        session.profile['max_budget'] = 0

    # Язык обучения
    if any(word in message_lower for word in ['английский', 'english', 'англ', 'ielts', 'toefl']):
        session.profile['language'] = 'английский'