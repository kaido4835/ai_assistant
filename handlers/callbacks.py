# handlers/callbacks.py
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import Settings
from handlers.operator import OperatorHandler


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()

    # Получаем обработчик операторов
    if 'operator_handler' not in context.bot_data:
        context.bot_data['operator_handler'] = OperatorHandler()

    operator_handler = context.bot_data['operator_handler']

    # Связь с оператором
    if query.data == "connect_manager":
        await operator_handler.request_operator(update, context)
    elif query.data.startswith("operator_"):
        await operator_handler.handle_operator_request(update, context)
    elif query.data == "end_operator_chat":
        await operator_handler.end_operator_chat(update, context)
    elif query.data == "operator_stats":
        await operator_handler.get_operator_stats(update, context)
    elif query.data.startswith("end_chat_"):
        # Оператор завершает диалог
        await handle_operator_end_chat(update, context, operator_handler)
    elif query.data == "thanks_operator":
        await query.edit_message_text("💝 Спасибо за оценку! Мы ценим ваше мнение.")
    elif query.data == "clarify_operator":
        await query.edit_message_text("❓ Уточните ваш вопрос, и оператор ответит подробнее.")
    elif query.data == "rate_operator":
        await show_operator_rating(update, context)


async def handle_operator_end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   operator_handler: OperatorHandler):
    """Обработка завершения диалога оператором"""
    query = update.callback_query
    user_id = int(query.data.replace("end_chat_", ""))
    operator_chat_id = query.message.chat_id

    # Удаляем соединение
    if user_id in operator_handler.active_conversations:
        del operator_handler.active_conversations[user_id]

    if operator_chat_id in operator_handler.operator_sessions:
        if user_id in operator_handler.operator_sessions[operator_chat_id]:
            operator_handler.operator_sessions[operator_chat_id].remove(user_id)

    # Уведомляем оператора
    await query.edit_message_text(f"✅ Диалог с пользователем {user_id} завершен")

    # Уведомляем пользователя
    await context.bot.send_message(
        chat_id=user_id,
        text="📞 **Диалог завершен оператором**\n\n"
             "Спасибо за обращение! Если у вас остались вопросы, "
             "всегда можете обратиться снова.\n\n"
             "📧 Email: info@example.com\n"
             "📱 Поддержка: @education_support"
    )


async def show_operator_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать варианты оценки оператора"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = [
        [
            InlineKeyboardButton("⭐", callback_data="rate_1"),
            InlineKeyboardButton("⭐⭐", callback_data="rate_2"),
            InlineKeyboardButton("⭐⭐⭐", callback_data="rate_3")
        ],
        [
            InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate_4"),
            InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate_5")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        "⭐ **Оцените работу оператора:**\n\n"
        "Ваша оценка поможет нам улучшить качество обслуживания!",
        reply_markup=reply_markup
    )


async def connect_to_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Передача клиента менеджеру (старая функция, теперь вызывает новую систему)"""
    # Получаем обработчик операторов
    if 'operator_handler' not in context.bot_data:
        context.bot_data['operator_handler'] = OperatorHandler()

    operator_handler = context.bot_data['operator_handler']
    await operator_handler.request_operator(update, context)


async def notify_manager(session, context: ContextTypes.DEFAULT_TYPE, lead_service):
    """Уведомление менеджера о новом лиде (старая функция)"""
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