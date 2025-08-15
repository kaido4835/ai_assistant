# handlers/callbacks.py
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import Settings


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == "connect_manager":
        await connect_to_manager(update, context)


async def connect_to_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Передача клиента менеджеру"""
    if hasattr(update, 'callback_query') and update.callback_query:
        user = update.callback_query.from_user
        chat_id = update.callback_query.message.chat_id
    else:
        user = update.effective_user
        chat_id = update.effective_chat.id

    # Получаем сервисы
    session_manager = context.bot_data['session_manager']
    lead_service = context.bot_data['lead_service']

    session = session_manager.get_or_create_session(user.id)
    session.stage = "ready_for_manager"

    await context.bot.send_message(chat_id=chat_id, text=Settings.CONTACT_MESSAGE)

    # Уведомляем менеджера
    await notify_manager(session, context, lead_service)
    session_manager.save_session(session)


async def notify_manager(session, context: ContextTypes.DEFAULT_TYPE, lead_service):
    """Уведомление менеджера о новом лиде"""
    if not Settings.MANAGER_CHAT_ID:
        print("MANAGER_CHAT_ID не настроен")
        return

    lead_report = lead_service.create_lead_report(session)

    try:
        await context.bot.send_message(
            chat_id=Settings.MANAGER_CHAT_ID,
            text=lead_report
        )

        # Создаем лид в БД
        score = lead_service.calculate_lead_score(session)
        lead_service.db.create_lead(session.user_id, score)

    except Exception as e:
        print(f"Ошибка отправки уведомления менеджеру: {e}")