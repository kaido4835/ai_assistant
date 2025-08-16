# handlers/callbacks.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

    # Новые обработчики для быстрых ответов
    elif query.data.startswith("quick_responses_"):
        await operator_handler.handle_operator_request(update, context)
    elif query.data.startswith("quick_reply_"):
        await operator_handler.handle_operator_request(update, context)
    elif query.data.startswith("send_quick_"):
        await handle_quick_response(update, context, operator_handler)
    elif query.data.startswith("back_to_client_"):
        await handle_back_to_client(update, context, operator_handler)
    elif query.data == "cancel_operator_queue":
        await handle_cancel_queue(update, context, operator_handler)
    elif query.data.startswith("rate_"):
        await handle_operator_rating(update, context)


async def handle_quick_response(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                operator_handler: OperatorHandler):
    """Обработка быстрых ответов"""
    query = update.callback_query
    data_parts = query.data.split("_")

    if len(data_parts) >= 4:
        user_id = int(data_parts[2])
        response_type = data_parts[3]
        await operator_handler.send_quick_response(query, user_id, response_type, context)


async def handle_back_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                operator_handler: OperatorHandler):
    """Возврат к информации о клиенте"""
    query = update.callback_query
    user_id = int(query.data.replace("back_to_client_", ""))

    # Получаем информацию о клиенте
    session_manager = context.bot_data['session_manager']
    lead_service = context.bot_data['lead_service']
    session = session_manager.get_or_create_session(user_id)

    operator_keyboard = [
        [InlineKeyboardButton(f"📞 Быстрые ответы", callback_data=f"quick_responses_{user_id}")],
        [InlineKeyboardButton(f"✅ Завершить диалог", callback_data=f"end_chat_{user_id}")],
        [InlineKeyboardButton("📊 Статистика", callback_data="operator_stats")]
    ]
    operator_reply_markup = InlineKeyboardMarkup(operator_keyboard)

    lead_report = lead_service.create_lead_report(session)

    operator_message = f"""🔔 **Информация о клиенте {user_id}:**

{lead_report}

💬 **Как отвечать:**
Просто напишите: `/reply_{user_id} ваш_ответ`
"""

    await query.edit_message_text(operator_message, reply_markup=operator_reply_markup)


async def handle_cancel_queue(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              operator_handler: OperatorHandler):
    """Отмена ожидания в очереди"""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id in operator_handler.operator_queue:
        operator_handler.operator_queue.remove(user_id)

    await query.edit_message_text(
        "❌ **Ожидание отменено**\n\n"
        "Вы можете попробовать связаться с оператором позже или "
        "продолжить общение с AI-консультантом.\n\n"
        "📧 Для срочных вопросов: info@example.com"
    )


async def handle_operator_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка оценки оператора"""
    query = update.callback_query
    rating = int(query.data.replace("rate_", ""))

    # Здесь можно сохранить оценку в базу данных
    # db = context.bot_data['db']
    # db.save_operator_rating(query.from_user.id, rating)

    thanks_messages = {
        1: "Извините, что не оправдали ожидания. Мы работаем над улучшением сервиса.",
        2: "Спасибо за отзыв. Мы учтем ваши пожелания для улучшения работы.",
        3: "Благодарим за оценку! Мы стремимся стать лучше.",
        4: "Отлично! Рады, что смогли помочь. Спасибо за высокую оценку!",
        5: "Превосходно! ⭐ Благодарим за максимальную оценку!"
    }

    await query.edit_message_text(
        f"⭐ **Оценка: {rating}/5**\n\n"
        f"{thanks_messages.get(rating, 'Спасибо за оценку!')}\n\n"
        "💙 Ваше мнение помогает нам становиться лучше!"
    )


async def handle_operator_end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   operator_handler: OperatorHandler):
    """Обработка завершения диалога оператором"""
    query = update.callback_query
    user_id = int(query.data.replace("end_chat_", ""))
    operator_chat_id = query.message.chat_id

    # Удаляем соединение
    if user_id in operator_handler.active_conversations:
        await operator_handler.disconnect_user(user_id, operator_chat_id)

    # Уведомляем оператора
    await query.edit_message_text(f"✅ Диалог с пользователем {user_id} завершен")

    # Уведомляем пользователя
    keyboard = [
        [InlineKeyboardButton("⭐ Оценить работу оператора", callback_data="rate_operator")],
        [InlineKeyboardButton("🔁 Связаться с оператором снова", callback_data="connect_manager")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="📞 **Диалог завершен оператором**\n\n"
                 "Спасибо за обращение! Если у вас остались вопросы, "
                 "всегда можете обратиться снова.\n\n"
                 "📧 Email: info@example.com\n"
                 "📱 Поддержка: @education_support",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления пользователю {user_id}: {e}")


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
    if not Settings.MANAGER_USER_ID:
        print("MANAGER_USER_ID не настроен")
        return

    lead_report = lead_service.create_lead_report(session)

    try:
        await context.bot.send_message(
            chat_id=int(Settings.MANAGER_USER_ID),
            text=lead_report
        )

        # Создаем лид в БД
        score = lead_service.calculate_lead_score(session)
        lead_service.db.create_lead(session.user_id, score)

    except Exception as e:
        print(f"Ошибка отправки уведомления менеджеру: {e}")


# Дополнительные функции для обработки специфических callback-ов
async def handle_program_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса деталей программы"""
    query = update.callback_query
    # Здесь можно добавить логику для показа подробностей программы
    await query.edit_message_text("📋 Подробная информация о программе будет отправлена...")


async def handle_application_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса о процессе поступления"""
    query = update.callback_query

    process_text = """
📋 **Процесс поступления:**

1️⃣ **Консультация и подбор программ** (1-2 недели)
2️⃣ **Подготовка документов** (2-4 недели)  
3️⃣ **Подача заявления** (1 неделя)
4️⃣ **Ожидание ответа** (2-8 недель)
5️⃣ **Получение приглашения** (1 день)
6️⃣ **Подача на визу** (2-4 недели)

💡 Хотите начать процесс? Свяжитесь с нашим консультантом!
    """

    keyboard = [
        [InlineKeyboardButton("📞 Связаться с консультантом", callback_data="connect_manager")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(process_text, reply_markup=reply_markup)