# handlers/operator.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import Settings
from utils.session_manager import SessionManager
from services.lead_service import LeadService
import asyncio
from datetime import datetime, timedelta


class OperatorHandler:
    def __init__(self):
        self.active_conversations = {}  # user_id -> operator_chat_id
        self.operator_sessions = {}  # operator_chat_id -> [user_ids]

    async def request_operator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запрос на связь с оператором"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Получаем сервисы
        session_manager: SessionManager = context.bot_data['session_manager']
        lead_service: LeadService = context.bot_data['lead_service']

        session = session_manager.get_or_create_session(user_id)
        session.stage = "waiting_for_operator"

        # Проверяем, не подключен ли уже к оператору
        if user_id in self.active_conversations:
            await update.message.reply_text(
                "✅ Вы уже подключены к оператору! Просто напишите ваш вопрос."
            )
            return

        # Создаем кнопки для выбора причины обращения
        keyboard = [
            [InlineKeyboardButton("📚 Консультация по программам", callback_data="operator_programs")],
            [InlineKeyboardButton("📄 Помощь с документами", callback_data="operator_documents")],
            [InlineKeyboardButton("💰 Вопросы по стоимости", callback_data="operator_pricing")],
            [InlineKeyboardButton("🚀 Готов подавать документы", callback_data="operator_apply")],
            [InlineKeyboardButton("❓ Другой вопрос", callback_data="operator_other")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔗 **Связь с оператором**\n\n"
            "Укажите, с чем вам помочь, чтобы мы подключили подходящего специалиста:",
            reply_markup=reply_markup
        )

        session_manager.save_session(session)

    async def handle_operator_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора типа запроса к оператору"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        chat_id = query.message.chat_id
        request_type = query.data.replace("operator_", "")

        # Получаем сервисы
        session_manager: SessionManager = context.bot_data['session_manager']
        lead_service: LeadService = context.bot_data['lead_service']

        session = session_manager.get_or_create_session(user_id)

        # Определяем тип запроса
        request_types = {
            "programs": "📚 Консультация по программам",
            "documents": "📄 Помощь с документами",
            "pricing": "💰 Вопросы по стоимости",
            "apply": "🚀 Готов подавать документы",
            "other": "❓ Другой вопрос"
        }

        session.profile['operator_request_type'] = request_type
        session.profile['operator_request_time'] = datetime.now().isoformat()

        # Уведомляем пользователя
        await query.edit_message_text(
            f"✅ **Запрос принят!**\n\n"
            f"**Тип:** {request_types.get(request_type, 'Консультация')}\n"
            f"**Статус:** Ищем свободного оператора...\n\n"
            f"⏱️ Среднее время ответа: 2-5 минут\n"
            f"📱 Пока ожидаете, можете написать подробнее о вашем вопросе."
        )

        # Пытаемся найти свободного оператора
        operator_found = await self.find_available_operator(session, context, lead_service)

        if not operator_found:
            # Если операторы заняты, ставим в очередь
            await self.add_to_queue(session, context)

        session_manager.save_session(session)

    async def find_available_operator(self, session, context: ContextTypes.DEFAULT_TYPE, lead_service) -> bool:
        """Поиск доступного оператора"""
        if not Settings.MANAGER_CHAT_ID:
            return False

        # Проверяем, не занят ли основной оператор
        operator_chat_id = int(Settings.MANAGER_CHAT_ID)

        # Для демо используем основной чат менеджера
        # В реальной системе здесь была бы логика проверки доступности

        try:
            await self.connect_to_operator(session.user_id, operator_chat_id, context, lead_service, session)
            return True
        except Exception as e:
            print(f"Ошибка подключения к оператору: {e}")
            return False

    async def connect_to_operator(self, user_id: int, operator_chat_id: int, context: ContextTypes.DEFAULT_TYPE,
                                  lead_service, session):
        """Подключение пользователя к оператору"""
        # Записываем активное соединение
        self.active_conversations[user_id] = operator_chat_id

        if operator_chat_id not in self.operator_sessions:
            self.operator_sessions[operator_chat_id] = []
        self.operator_sessions[operator_chat_id].append(user_id)

        # Уведомляем пользователя
        user_keyboard = [
            [InlineKeyboardButton("❌ Завершить диалог с оператором", callback_data="end_operator_chat")]
        ]
        user_reply_markup = InlineKeyboardMarkup(user_keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Подключен оператор!**\n\n"
                 "👨‍💼 Сейчас с вами будет работать наш специалист.\n"
                 "💬 Просто пишите ваши вопросы - они будут переданы оператору.\n\n"
                 "⚡ Для быстрого решения вопроса поделитесь:\n"
                 "• Вашими образовательными целями\n"
                 "• Предпочтениями по странам/программам\n"
                 "• Бюджетом и временными рамками",
            reply_markup=user_reply_markup
        )

        # Уведомляем оператора
        lead_report = lead_service.create_lead_report(session)
        request_type = session.profile.get('operator_request_type', 'general')

        operator_keyboard = [
            [InlineKeyboardButton(f"📞 Ответить пользователю {user_id}", callback_data=f"reply_to_{user_id}")],
            [InlineKeyboardButton(f"✅ Завершить диалог с {user_id}", callback_data=f"end_chat_{user_id}")],
            [InlineKeyboardButton("📊 Статистика диалогов", callback_data="operator_stats")]
        ]
        operator_reply_markup = InlineKeyboardMarkup(operator_keyboard)

        await context.bot.send_message(
            chat_id=operator_chat_id,
            text=f"🔔 **Новый клиент подключен!**\n\n"
                 f"**ID:** {user_id}\n"
                 f"**Тип запроса:** {request_type}\n"
                 f"**Время:** {datetime.now().strftime('%H:%M')}\n\n"
                 f"{lead_report}\n\n"
                 f"💬 Чтобы ответить клиенту, просто напишите сообщение в этот чат, начав с /reply_{user_id}",
            reply_markup=operator_reply_markup
        )

    async def add_to_queue(self, session, context: ContextTypes.DEFAULT_TYPE):
        """Добавление в очередь ожидания"""
        await context.bot.send_message(
            chat_id=session.user_id,
            text="⏳ **В очереди**\n\n"
                 "Все операторы сейчас заняты с другими клиентами.\n"
                 "📍 Ваш номер в очереди: 1-2\n"
                 "⏱️ Ожидаемое время: 5-10 минут\n\n"
                 "🔔 Мы уведомим вас, как только оператор освободится!\n"
                 "💬 Пока можете написать ваш вопрос подробнее."
        )

        # Устанавливаем таймер для повторной проверки
        asyncio.create_task(self.recheck_queue_later(session, context))

    async def recheck_queue_later(self, session, context: ContextTypes.DEFAULT_TYPE):
        """Повторная проверка очереди через время"""
        await asyncio.sleep(300)  # 5 минут

        # Проверяем, не подключился ли уже пользователь
        if session.user_id not in self.active_conversations:
            lead_service = context.bot_data['lead_service']
            operator_found = await self.find_available_operator(session, context, lead_service)

            if not operator_found:
                await context.bot.send_message(
                    chat_id=session.user_id,
                    text="⏳ Операторы все еще заняты. Ожидайте, пожалуйста.\n"
                         "📞 Для срочных вопросов можете позвонить: +7 XXX XXX XX XX"
                )

    async def handle_user_message_to_operator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пересылка сообщения пользователя оператору"""
        user_id = update.effective_user.id

        if user_id not in self.active_conversations:
            return False  # Пользователь не подключен к оператору

        operator_chat_id = self.active_conversations[user_id]
        user_message = update.message.text

        # Пересылаем сообщение оператору
        await context.bot.send_message(
            chat_id=operator_chat_id,
            text=f"💬 **Сообщение от клиента {user_id}:**\n\n{user_message}\n\n"
                 f"📝 *Ответить: /reply_{user_id} ваш_ответ*"
        )

        # Подтверждаем пользователю
        await update.message.reply_text("✅ Сообщение отправлено оператору")
        return True

    async def handle_operator_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ответа оператора пользователю"""
        message_text = update.message.text

        # Парсим команду /reply_USER_ID
        if not message_text.startswith('/reply_'):
            return False

        try:
            parts = message_text.split(' ', 1)
            user_id = int(parts[0].replace('/reply_', ''))
            reply_text = parts[1] if len(parts) > 1 else "Оператор подключен"
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Неверный формат. Используйте: /reply_USER_ID ваш_ответ")
            return False

        # Проверяем, что оператор работает с этим пользователем
        operator_chat_id = update.effective_chat.id
        if user_id not in self.active_conversations or self.active_conversations[user_id] != operator_chat_id:
            await update.message.reply_text("❌ Этот пользователь не подключен к вам")
            return False

        # Отправляем ответ пользователю
        keyboard = [
            [InlineKeyboardButton("👍 Спасибо", callback_data="thanks_operator")],
            [InlineKeyboardButton("❓ Уточнить", callback_data="clarify_operator")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"👨‍💼 **Ответ оператора:**\n\n{reply_text}",
            reply_markup=reply_markup
        )

        # Подтверждаем оператору
        await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}")
        return True

    async def end_operator_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершение диалога с оператором"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id

        if user_id not in self.active_conversations:
            await query.edit_message_text("❌ Вы не подключены к оператору")
            return

        operator_chat_id = self.active_conversations[user_id]

        # Удаляем соединение
        del self.active_conversations[user_id]
        if operator_chat_id in self.operator_sessions:
            if user_id in self.operator_sessions[operator_chat_id]:
                self.operator_sessions[operator_chat_id].remove(user_id)

        # Уведомляем пользователя
        keyboard = [
            [InlineKeyboardButton("⭐ Оценить работу оператора", callback_data="rate_operator")],
            [InlineKeyboardButton("🔁 Связаться с оператором снова", callback_data="connect_manager")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "✅ **Диалог завершен**\n\n"
            "Спасибо за обращение! Если остались вопросы, "
            "мы всегда готовы помочь.\n\n"
            "📧 Email: info@example.com\n"
            "📱 Telegram: @education_support",
            reply_markup=reply_markup
        )

        # Уведомляем оператора
        await context.bot.send_message(
            chat_id=operator_chat_id,
            text=f"✅ Диалог с пользователем {user_id} завершен"
        )

    async def get_operator_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика для оператора"""
        query = update.callback_query
        await query.answer()

        operator_chat_id = query.message.chat_id
        active_chats = len(self.operator_sessions.get(operator_chat_id, []))

        stats_text = f"""
📊 **Статистика оператора**

👥 **Активных диалогов:** {active_chats}
⏰ **Время работы:** {datetime.now().strftime('%H:%M')}
📈 **Всего за сегодня:** 12 диалогов
⭐ **Средняя оценка:** 4.8/5

🔔 **Быстрые команды:**
• /reply_USER_ID - ответить клиенту
• /stats - показать статистику
• /help_operator - справка для операторов
        """

        await query.edit_message_text(stats_text)