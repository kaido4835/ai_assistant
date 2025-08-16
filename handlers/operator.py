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
        self.active_conversations = {}  # user_id -> operator_user_id
        self.operator_sessions = {}  # operator_user_id -> [user_ids]
        self.operator_workload = {}  # operator_user_id -> count
        self.operator_queue = []  # очередь пользователей ожидающих оператора

    async def request_operator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запрос на подключение к оператору"""
        user_id = update.effective_user.id

        # Получаем сервисы
        session_manager: SessionManager = context.bot_data['session_manager']
        lead_service: LeadService = context.bot_data['lead_service']

        session = session_manager.get_or_create_session(user_id)

        # Проверяем, не подключен ли уже пользователь
        if user_id in self.active_conversations:
            await update.message.reply_text(
                "📞 Вы уже подключены к оператору!\n\n"
                "💬 Просто напишите ваш вопрос - оператор получит сообщение."
            )
            return

        # Сохраняем тип запроса
        session.profile['operator_request_type'] = 'подключение через кнопку'
        session_manager.save_session(session)

        # Проверяем рабочее время
        current_hour = datetime.now().hour
        if (current_hour < Settings.OPERATOR_WORKING_HOURS_START or
                current_hour >= Settings.OPERATOR_WORKING_HOURS_END):
            await update.message.reply_text(
                f"🕐 **Сейчас нерабочее время**\n\n"
                f"⏰ Операторы работают с {Settings.OPERATOR_WORKING_HOURS_START}:00 "
                f"до {Settings.OPERATOR_WORKING_HOURS_END}:00\n\n"
                f"📧 Для срочных вопросов: info@example.com\n"
                f"📱 Telegram: @education_support\n\n"
                f"🔔 Завтра утром оператор обязательно с вами свяжется!"
            )
            return

        # Пытаемся найти доступного оператора
        if await self.find_available_operator(session, context, lead_service):
            return

        # Добавляем в очередь
        if user_id not in self.operator_queue:
            self.operator_queue.append(user_id)
            queue_position = len(self.operator_queue)

            keyboard = [
                [InlineKeyboardButton("❌ Отменить ожидание", callback_data="cancel_operator_queue")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"⏳ **Все операторы заняты**\n\n"
                f"📍 Ваше место в очереди: {queue_position}\n"
                f"⏰ Ожидаемое время: 3-5 минут\n\n"
                f"💡 Пока ждете, можете написать ваш вопрос - "
                f"оператор увидит его сразу при подключении.",
                reply_markup=reply_markup
            )

    async def handle_user_message_to_operator(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка сообщения пользователя, подключенного к оператору"""
        user_id = update.effective_user.id

        # Проверяем, подключен ли пользователь к оператору
        if user_id not in self.active_conversations:
            return False

        operator_user_id = self.active_conversations[user_id]
        user_message = update.message.text

        # Отправляем сообщение оператору
        try:
            operator_message = f"""💬 **Сообщение от клиента {user_id}:**

"{user_message}"

⏰ Время: {datetime.now().strftime('%H:%M')}

💡 **Ответить:** `/reply_{user_id} ваш_ответ`
"""

            keyboard = [
                [InlineKeyboardButton(f"📞 Быстрый ответ", callback_data=f"quick_reply_{user_id}")],
                [InlineKeyboardButton(f"✅ Завершить диалог", callback_data=f"end_chat_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=operator_user_id,
                text=operator_message,
                reply_markup=reply_markup
            )

            # Подтверждение пользователю
            await update.message.reply_text(
                "✅ Сообщение передано оператору\n"
                "⏰ Обычно отвечаем в течение 2-3 минут"
            )

            return True

        except Exception as e:
            print(f"❌ Ошибка отправки сообщения оператору {operator_user_id}: {e}")

            # Если оператор недоступен, отключаем пользователя
            await self.disconnect_user(user_id, operator_user_id)

            await update.message.reply_text(
                "⚠️ **Оператор временно недоступен**\n\n"
                "Попробуйте подключиться к другому оператору или "
                "обратитесь позже.\n\n"
                "📧 Email: info@example.com"
            )

            return True

    async def find_available_operator(self, session, context: ContextTypes.DEFAULT_TYPE, lead_service) -> bool:
        """Поиск доступного оператора"""
        available_operators = Settings.get_available_operators()

        if not available_operators:
            print("❌ Нет настроенных операторов")
            return False

        # Находим оператора с наименьшей нагрузкой
        best_operator = None
        min_workload = float('inf')

        for operator_id in available_operators:
            current_workload = self.operator_workload.get(operator_id, 0)
            if current_workload < Settings.MAX_CONCURRENT_CHATS and current_workload < min_workload:
                best_operator = operator_id
                min_workload = current_workload

        if best_operator:
            try:
                await self.connect_to_operator(session.user_id, best_operator, context, lead_service, session)
                return True
            except Exception as e:
                print(f"❌ Ошибка подключения к оператору {best_operator}: {e}")
                return False

        return False

    async def connect_to_operator(self, user_id: int, operator_user_id: int,
                                  context: ContextTypes.DEFAULT_TYPE, lead_service, session):
        """Подключение пользователя к оператору"""

        # Записываем активное соединение
        self.active_conversations[user_id] = operator_user_id

        if operator_user_id not in self.operator_sessions:
            self.operator_sessions[operator_user_id] = []
        self.operator_sessions[operator_user_id].append(user_id)

        # Увеличиваем нагрузку оператора
        self.operator_workload[operator_user_id] = self.operator_workload.get(operator_user_id, 0) + 1

        # Убираем пользователя из очереди, если он там был
        if user_id in self.operator_queue:
            self.operator_queue.remove(user_id)

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
        request_type = session.profile.get('operator_request_type', 'общая консультация')

        operator_keyboard = [
            [InlineKeyboardButton(f"📞 Быстрые ответы", callback_data=f"quick_responses_{user_id}")],
            [InlineKeyboardButton(f"✅ Завершить диалог", callback_data=f"end_chat_{user_id}")],
            [InlineKeyboardButton("📊 Статистика", callback_data="operator_stats")]
        ]
        operator_reply_markup = InlineKeyboardMarkup(operator_keyboard)

        operator_message = f"""🔔 **Новый клиент подключен!**

**ID клиента:** {user_id}
**Тип запроса:** {request_type}
**Время:** {datetime.now().strftime('%H:%M')}

{lead_report}

💬 **Как отвечать:**
Просто напишите: `/reply_{user_id} ваш_ответ`

**Пример:**
`/reply_{user_id} Добро пожаловать! Чем могу помочь?`
"""

        try:
            await context.bot.send_message(
                chat_id=operator_user_id,
                text=operator_message,
                reply_markup=operator_reply_markup
            )
            print(f"✅ Пользователь {user_id} подключен к оператору {operator_user_id}")
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения оператору {operator_user_id}: {e}")
            # Если не удалось отправить сообщение оператору, отменяем подключение
            await self.disconnect_user(user_id, operator_user_id)
            raise e

    async def disconnect_user(self, user_id: int, operator_user_id: int):
        """Отключение пользователя от оператора"""
        # Удаляем из активных разговоров
        if user_id in self.active_conversations:
            del self.active_conversations[user_id]

        # Удаляем из сессий оператора
        if (operator_user_id in self.operator_sessions and
                user_id in self.operator_sessions[operator_user_id]):
            self.operator_sessions[operator_user_id].remove(user_id)

        # Уменьшаем нагрузку оператора
        if operator_user_id in self.operator_workload:
            self.operator_workload[operator_user_id] = max(0,
                                                           self.operator_workload[operator_user_id] - 1)

    async def handle_operator_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ответа оператора пользователю"""
        message_text = update.message.text
        operator_user_id = update.effective_user.id

        # Проверяем, является ли отправитель оператором
        if not Settings.is_operator(operator_user_id):
            return False

        # Парсим команду /reply_USER_ID
        if not message_text.startswith('/reply_'):
            return False

        try:
            parts = message_text.split(' ', 1)
            user_id = int(parts[0].replace('/reply_', ''))
            reply_text = parts[1] if len(parts) > 1 else "Оператор подключен"
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ **Неверный формат команды**\n\n"
                "✅ Правильно: `/reply_USER_ID ваш_ответ`\n"
                "📝 Пример: `/reply_123456 Добро пожаловать!`"
            )
            return False

        # Проверяем, что оператор работает с этим пользователем
        if (user_id not in self.active_conversations or
                self.active_conversations[user_id] != operator_user_id):
            await update.message.reply_text(
                f"❌ **Пользователь {user_id} не подключен к вам**\n\n"
                f"🔍 Ваши активные клиенты:\n"
                f"{', '.join(map(str, self.operator_sessions.get(operator_user_id, []))) or 'Нет активных'}"
            )
            return False

        # Отправляем ответ пользователю
        keyboard = [
            [InlineKeyboardButton("👍 Спасибо", callback_data="thanks_operator")],
            [InlineKeyboardButton("❓ Уточнить", callback_data="clarify_operator")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"👨‍💼 **Ответ оператора:**\n\n{reply_text}",
                reply_markup=reply_markup
            )

            # Подтверждаем оператору
            await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}")
            return True

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка отправки сообщения пользователю {user_id}: {e}")
            return False

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
        await self.disconnect_user(user_id, operator_chat_id)

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
        try:
            await context.bot.send_message(
                chat_id=operator_chat_id,
                text=f"✅ Диалог с пользователем {user_id} завершен"
            )
        except Exception as e:
            print(f"❌ Ошибка уведомления оператора: {e}")

    async def get_operator_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика для оператора"""
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            await query.answer()
            operator_chat_id = query.message.chat_id
            edit_message = True
        else:
            operator_chat_id = update.effective_chat.id
            edit_message = False

        active_chats = len(self.operator_sessions.get(operator_chat_id, []))
        queue_length = len(self.operator_queue)

        stats_text = f"""📊 **Статистика оператора**

👥 **Активных диалогов:** {active_chats}/{Settings.MAX_CONCURRENT_CHATS}
⏳ **В очереди:** {queue_length} человек
⏰ **Время работы:** {datetime.now().strftime('%H:%M')}
📈 **Статус:** {'🟢 Доступен' if active_chats < Settings.MAX_CONCURRENT_CHATS else '🔴 Занят'}

🔔 **Быстрые команды:**
• `/reply_USER_ID текст` - ответить клиенту
• `/stats` - показать статистику
• `/help_operator` - справка для операторов

📋 **Активные клиенты:**
{', '.join(map(str, self.operator_sessions.get(operator_chat_id, []))) or 'Нет активных'}
        """

        if edit_message and hasattr(update, 'callback_query'):
            await query.edit_message_text(stats_text)
        else:
            await update.message.reply_text(stats_text)

    async def handle_operator_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка запросов операторов через callback"""
        query = update.callback_query
        await query.answer()

        if query.data.startswith("quick_responses_"):
            user_id = int(query.data.replace("quick_responses_", ""))
            await self.show_quick_responses(query, user_id)
        elif query.data.startswith("quick_reply_"):
            user_id = int(query.data.replace("quick_reply_", ""))
            await self.show_quick_responses(query, user_id)

    async def show_quick_responses(self, query, user_id: int):
        """Показать быстрые ответы оператору"""
        keyboard = [
            [InlineKeyboardButton("👋 Добро пожаловать!", callback_data=f"send_quick_{user_id}_welcome")],
            [InlineKeyboardButton("📋 Расскажите о целях", callback_data=f"send_quick_{user_id}_goals")],
            [InlineKeyboardButton("💰 Обсудим бюджет", callback_data=f"send_quick_{user_id}_budget")],
            [InlineKeyboardButton("📄 Нужны документы", callback_data=f"send_quick_{user_id}_documents")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_client_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"⚡ **Быстрые ответы для клиента {user_id}:**\n\n"
            "Выберите готовый ответ или напишите свой:\n"
            f"`/reply_{user_id} ваш_текст`",
            reply_markup=reply_markup
        )

    async def send_quick_response(self, query, user_id: int, response_type: str, context: ContextTypes.DEFAULT_TYPE):
        """Отправить быстрый ответ"""
        responses = {
            'welcome': "👋 Добро пожаловать! Я ваш персональный консультант по образованию за рубежом. Чем могу помочь?",
            'goals': "📋 Расскажите подробнее о ваших образовательных целях: какая область интересует, какой уровень образования планируете?",
            'budget': "💰 Давайте обсудим бюджет. Сколько примерно готовы тратить в год на обучение? Есть бесплатные варианты в Германии и Скандинавии.",
            'documents': "📄 Для подачи документов потребуется: диплом с оценками, языковой сертификат, мотивационное письмо. Подробности обсудим индивидуально."
        }

        response_text = responses.get(response_type, "Здравствуйте! Чем могу помочь?")

        # Отправляем ответ пользователю
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"👨‍💼 **Ответ оператора:**\n\n{response_text}"
            )

            await query.edit_message_text(f"✅ Быстрый ответ отправлен пользователю {user_id}")

        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка отправки: {e}")