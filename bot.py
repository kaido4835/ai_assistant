import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from huggingface_hub import InferenceClient

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAMTOKEN")
HUGGINGFACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")  # ID чата менеджера для уведомлений

# Инициализация AI клиента
ai_client = InferenceClient(
    provider="fireworks-ai",
    api_key=HUGGINGFACE_TOKEN
)

# База данных программ
EDUCATION_DATABASE = [
    {
        "country": "Германия",
        "university": "Технический университет Мюнхена",
        "program": "MSc Artificial Intelligence",
        "degree": "магистратура",
        "field": "ИИ, ИТ",
        "language": "английский",
        "duration": "2 года",
        "cost_per_year": 0,
        "requirements": "IELTS 6.5+, диплом бакалавра в ИТ",
        "application_deadline": "15 июля",
        "website": "https://tum.de/ai"
    },
    {
        "country": "Нидерланды",
        "university": "Делфтский технический университет",
        "program": "MSc Computer Science - AI Track",
        "degree": "магистратура",
        "field": "ИИ, ИТ",
        "language": "английский",
        "duration": "2 года",
        "cost_per_year": 2314,
        "requirements": "IELTS 6.5+, техническое образование",
        "application_deadline": "1 февраля",
        "website": "https://tudelft.nl/ai"
    },
    {
        "country": "Чехия",
        "university": "Карлов университет",
        "program": "MSc Computer Science",
        "degree": "магистратура",
        "field": "ИТ, ИИ",
        "language": "английский",
        "duration": "2 года",
        "cost_per_year": 4000,
        "requirements": "IELTS 6.0+, диплом в ИТ/математике",
        "application_deadline": "30 апреля",
        "website": "https://cuni.cz/cs"
    },
    {
        "country": "Польша",
        "university": "Варшавский университет технологий",
        "program": "MSc Data Science and AI",
        "degree": "магистратура",
        "field": "ИИ, Data Science",
        "language": "английский",
        "duration": "1.5 года",
        "cost_per_year": 3000,
        "requirements": "IELTS 6.0+, бакалавр в технической области",
        "application_deadline": "31 мая",
        "website": "https://pw.edu.pl/datascience"
    },
    {
        "country": "Германия",
        "university": "RWTH Aachen",
        "program": "Computer Science",
        "degree": "бакалавриат",
        "field": "ИТ",
        "language": "английский",
        "duration": "3 года",
        "cost_per_year": 0,
        "requirements": "IELTS 6.0+, аттестат с математикой",
        "application_deadline": "15 июля",
        "website": "https://rwth-aachen.de/cs"
    },
    {
        "country": "Нидерланды",
        "university": "Университет Амстердама",
        "program": "BSc Artificial Intelligence",
        "degree": "бакалавриат",
        "field": "ИИ",
        "language": "английский",
        "duration": "3 года",
        "cost_per_year": 2314,
        "requirements": "IELTS 6.0+, математика на высоком уровне",
        "application_deadline": "1 мая",
        "website": "https://uva.nl/ai-bachelor"
    },
    {
        "country": "Швеция",
        "university": "Королевский технологический институт",
        "program": "MSc Machine Learning",
        "degree": "магистратура",
        "field": "ИИ, машинное обучение",
        "language": "английский",
        "duration": "2 года",
        "cost_per_year": 0,
        "requirements": "IELTS 6.5+, техническое/математическое образование",
        "application_deadline": "15 января",
        "website": "https://kth.se/ml"
    },
    {
        "country": "Финляндия",
        "university": "Университет Хельсинки",
        "program": "MSc Data Science",
        "degree": "магистратура",
        "field": "Data Science",
        "language": "английский",
        "duration": "2 года",
        "cost_per_year": 0,
        "requirements": "IELTS 6.5+, математическое/техническое образование",
        "application_deadline": "31 января",
        "website": "https://helsinki.fi/datascience"
    }
]

# Хранилище пользовательских сессий
user_sessions = {}


class UserSession:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.stage = "initial"
        self.profile = {}
        self.conversation_history = []
        self.interest_score = 0
        self.last_activity = datetime.now()


def get_or_create_session(user_id: int) -> UserSession:
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    return user_sessions[user_id]


def search_programs(filters: Dict) -> List[Dict]:
    """Поиск программ по фильтрам"""
    results = []

    for program in EDUCATION_DATABASE:
        match = True

        # Фильтр по уровню образования
        if 'degree' in filters and filters['degree']:
            if program['degree'].lower() != filters['degree'].lower():
                match = False

        # Фильтр по области
        if 'field' in filters and filters['field']:
            if not any(field.lower() in program['field'].lower() for field in filters['field']):
                match = False

        # Фильтр по бюджету
        if 'max_budget' in filters and filters['max_budget'] is not None:
            if program['cost_per_year'] > filters['max_budget']:
                match = False

        # Фильтр по языку
        if 'language' in filters and filters['language']:
            if filters['language'].lower() not in program['language'].lower():
                match = False

        if match:
            results.append(program)

    return results[:5]


async def extract_user_info(message: str, session: UserSession):
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

    # Ищем числа с валютами
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


async def get_ai_response(message: str, session: UserSession) -> tuple[str, int]:
    """Получение ответа от AI с оценкой интереса"""

    context = f"""
Ты дружелюбный консультант по образованию за рубежом. 

🎯 ТВОИ ЗАДАЧИ:
- Помогать студентам найти подходящие программы
- Отвечать на вопросы об учебе за границей  
- Мотивировать на конкретные действия
- Давать ПОЛНЫЕ и ЗАВЕРШЕННЫЕ ответы

💬 СТИЛЬ ОБЩЕНИЯ:
- Простой, дружелюбный язык
- ВСЕГДА заканчивай мысль полностью
- Отвечай в 2-4 предложениях
- Используй эмодзи умеренно
- Будь позитивным и мотивирующим

📊 ПРОФИЛЬ КЛИЕНТА: {json.dumps(session.profile, ensure_ascii=False)}

ВАЖНО: Обязательно завершай все предложения! Не обрывай ответ на полуслове.
Если упоминаешь страны или программы - дай конкретные примеры.
"""

    try:
        completion = ai_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": message}
            ],
            max_tokens=500,  # Увеличили лимит токенов
            temperature=0.8
        )

        response = completion.choices[0].message.content

        # Оценка интереса
        interest_keywords = {
            'high': ['хочу поступать', 'когда подавать', 'какие документы', 'помогите подать'],
            'medium': ['интересно', 'подходит', 'рассматриваю', 'думаю', 'планирую'],
            'low': ['просто узнать', 'в будущем', 'может быть']
        }

        interest_score = 0
        message_lower = message.lower()

        for level, keywords in interest_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            if level == 'high':
                interest_score += matches * 3
            elif level == 'medium':
                interest_score += matches * 2
            else:
                interest_score += matches * 1

        if '?' in message:
            interest_score += 1
        if any(word in message_lower for word in ['стоимость', 'цена', 'дедлайн', 'требования']):
            interest_score += 2

        return response, min(interest_score, 10)

    except Exception as e:
        print(f"Ошибка AI: {e}")
        return "Извини, небольшая техническая заминка 😅 Можешь повторить вопрос?", 0


async def handle_step_by_step_collection(user_message: str, session: UserSession) -> str:
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
            session.profile['question_stage'] = 'country'
            return """
Супер! А есть ли предпочтения по странам? 🌍

🇩🇪 Германия - много бесплатных программ
🇳🇱 Нидерланды - высокое качество образования  
🇨🇿 Чехия - доступные цены
🇵🇱 Польша - растущий рынок ИТ
🇫🇮 Финляндия - инновации и стартапы
🇸🇪 Швеция - бесплатное образование

Или может, рассмотреть все варианты? 🤷‍♂️
            """
        else:
            return "Не уловил сумму 🤔 Можешь написать примерный бюджет в евро или 'бесплатно'?"

    elif current_stage == 'country':
        session.profile['question_stage'] = 'language'
        return """
Ясно! И последний вопрос - на каком языке планируешь учиться? 🗣️

🇬🇧 Английский - больше всего программ
🇩🇪 Немецкий - если знаешь язык

Большинство международных программ на английском. У тебя есть IELTS/TOEFL или планируешь сдавать?
        """

    elif current_stage == 'language':
        session.profile['question_stage'] = 'complete'

        # Ищем подходящие программы
        programs = search_programs(session.profile)

        if programs:
            session.stage = "showing_results"

            response = "Отлично! Вот что нашел по твоим критериям 🎯\n\n"

            for i, program in enumerate(programs[:3], 1):
                cost_text = "Бесплатно" if program['cost_per_year'] == 0 else f"€{program['cost_per_year']:,}/год"
                response += f"""
**{i}. {program['program']}**
🏛️ {program['university']}, {program['country']}
💰 {cost_text}
⏱️ {program['duration']}
📅 Дедлайн: {program['application_deadline']}

"""

            response += "Какая программа интересует больше? Или хочешь узнать подробности о процессе поступления? 🤓"

            return response
        else:
            session.profile['question_stage'] = 'budget'
            return """
Хм, по таким критериям не нашел подходящих программ 🤔

Может, пересмотрим бюджет? Или расширим список стран?
Напиши, что хочешь изменить, и найдем варианты!
            """

    return "Что-то пошло не так 😅 Давай начнем сначала - какой уровень образования планируешь?"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    session = get_or_create_session(update.effective_user.id)
    session.stage = "initial"

    keyboard = [
        [KeyboardButton("🎓 Хочу учиться за границей")],
        [KeyboardButton("ℹ️ Узнать о процессе"), KeyboardButton("💬 Связаться с менеджером")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    welcome_text = """
🎓 Добро пожаловать в образовательное агентство!

Я помогу найти идеальную программу обучения за рубежом:
• Бакалавриат и магистратура
• Европа с отличными программами
• Бесплатные и доступные варианты
• Полное сопровождение поступления

Что вас интересует?
    """

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений"""
    user_message = update.message.text
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)

    session.conversation_history.append(f"Пользователь: {user_message}")
    session.last_activity = datetime.now()

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
        return

    elif "связаться с менеджером" in user_message.lower():
        await connect_to_manager(update, context)
        return

    elif "процессе" in user_message.lower():
        process_text = """
📋 **Как проходит поступление:**

1️⃣ **Консультация** (бесплатно)
   • Подбор программ под твои цели
   • Оценка шансов поступления

2️⃣ **Подготовка документов**
   • Переводы и нотариальное заверение
   • Мотивационные письма
   • Рекомендательные письма

3️⃣ **Подача заявок**
   • Заполнение онлайн-форм
   • Отправка документов
   • Отслеживание статуса

4️⃣ **Получение приглашения**
   • Ответ от университета
   • Подтверждение места

5️⃣ **Виза и переезд**
   • Помощь с визой
   • Поиск жилья
   • Подготовка к отъезду

⏰ **Сроки:** от 2 до 6 месяцев
💰 **Стоимость услуг:** от €300

Хочешь начать? 😊
        """
        await update.message.reply_text(process_text)
        return

    # Обработка специальных вопросов
    elif any(phrase in user_message.lower() for phrase in ['какие варианты', 'что есть', 'куда поступить']):
        if session.profile.get('max_budget') == 0:  # Бесплатное образование
            response = """
Для бесплатного образования отличные варианты:

🇩🇪 **Германия** - почти все программы бесплатны
• Технический университет Мюнхена (ИИ)
• RWTH Aachen (Computer Science)

🇫🇮 **Финляндия** - бесплатно для ЕС граждан
• Университет Хельсинки (Data Science)

🇸🇪 **Швеция** - бесплатные программы
• KTH (Machine Learning)

Хочешь подробности по какой-то стране? 🤔
            """
        else:
            response = """
У нас есть программы в разных ценовых категориях:

💰 **Бюджетные (до €5000/год):**
🇨🇿 Чехия - от €3000 (отличное качество)
🇵🇱 Польша - от €2500 (растущий IT-рынок)

💰 **Средний сегмент (€5000-10000):**
🇳🇱 Нидерланды - €2314 для ЕС граждан
🇮🇹 Италия - от €3000

💰 **Премиум (€10000+):**
🇫🇷 Франция - топовые бизнес-школы
🇬🇧 Великобритания - мировые рейтинги

Какой бюджет рассматриваешь? 💭
            """
        await update.message.reply_text(response)
        return

    # Поэтапный сбор информации
    if session.stage == "collecting_info":
        response = await handle_step_by_step_collection(user_message, session)
        await update.message.reply_text(response)
        return

    # Основная логика AI для общего диалога
    ai_response, interest_score = await get_ai_response(user_message, session)
    session.interest_score = max(session.interest_score, interest_score)
    session.conversation_history.append(f"Бот: {ai_response}")

    # Проверяем, готов ли клиент к передаче менеджеру
    if session.interest_score >= 5 and session.stage == "showing_results":
        keyboard = [
            [InlineKeyboardButton("📞 Связаться с менеджером", callback_data="connect_manager")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        ai_response += "\n\n💡 Похоже, вы серьезно заинтересованы! Хотите обсудить детали с нашим менеджером?"
        await update.message.reply_text(ai_response, reply_markup=reply_markup)
    else:
        await update.message.reply_text(ai_response)


async def connect_to_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Передача клиента менеджеру"""
    if hasattr(update, 'callback_query') and update.callback_query:
        user = update.callback_query.from_user
        chat_id = update.callback_query.message.chat_id
    else:
        user = update.effective_user
        chat_id = update.effective_chat.id

    session = get_or_create_session(user.id)
    session.stage = "ready_for_manager"

    contact_text = """
✅ Отлично! Передаю вас нашему менеджеру.

👨‍💼 Наш специалист свяжется с вами в ближайшее время для:
• Детальной консультации
• Подбора оптимальных программ  
• Составления плана поступления

📱 Для быстрой связи можете оставить свой номер телефона.

⏰ Обычно отвечаем в течение 2 часов в рабочее время.
    """

    await context.bot.send_message(chat_id=chat_id, text=contact_text)

    # Уведомляем менеджера
    await notify_manager(session, context)


async def notify_manager(session: UserSession, context: ContextTypes.DEFAULT_TYPE):
    """Уведомление менеджера о новом лиде"""
    if not MANAGER_CHAT_ID:
        return

    user_info = f"""
🔥 **Новый лид!**

👤 **Клиент ID:** {session.user_id}
📊 **Интерес:** {session.interest_score}/10
🎯 **Профиль:**
{json.dumps(session.profile, ensure_ascii=False, indent=2)}

💬 **Последние сообщения:**
{chr(10).join(session.conversation_history[-3:]) if session.conversation_history else 'Нет сообщений'}

🕐 **Время:** {session.last_activity.strftime('%H:%M %d.%m.%Y')}
    """

    try:
        await context.bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=user_info
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления менеджеру: {e}")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == "connect_manager":
        await connect_to_manager(update, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    print(f"Ошибка: {context.error}")


def main():
    """Запуск бота"""
    print("🚀 Запускаю образовательного консультанта...")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    print("✅ Образовательный консультант запущен!")
    print("🎓 Готов помогать студентам найти программы обучения за рубежом")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()