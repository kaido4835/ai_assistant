import os
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import Update

from config.settings import Settings
from database.education_db import EducationDatabase
from services.ai_service import AIService
from services.program_search import ProgramSearchService
from services.lead_service import LeadService
from utils.session_manager import SessionManager
from handlers.commands import start_command
from handlers.messages import handle_message
from handlers.callbacks import callback_handler
from handlers.operator import OperatorHandler


def setup_bot_data(application: Application):
    """Инициализация сервисов"""
    # Создаем папку для данных если не существует
    os.makedirs('data', exist_ok=True)

    # Инициализация сервисов
    db = EducationDatabase(Settings.DATABASE_PATH)
    ai_service = AIService()
    program_search = ProgramSearchService(db)
    lead_service = LeadService(db)
    session_manager = SessionManager(db)

    # Инициализация обработчика операторов
    operator_handler = OperatorHandler()

    # Сохраняем в bot_data для доступа из хендлеров
    application.bot_data.update({
        'db': db,
        'ai_service': ai_service,
        'program_search': program_search,
        'lead_service': lead_service,
        'session_manager': session_manager,
        'operator_handler': operator_handler
    })


async def operator_start_command(update: Update, context):
    """Команда /start для оператора"""
    if str(update.effective_chat.id) == Settings.MANAGER_USER_ID:
        await update.message.reply_text(Settings.OPERATOR_WELCOME_MESSAGE)
    else:
        await start_command(update, context)


async def error_handler(update: Update, context):
    """Глобальный обработчик ошибок"""
    print(f"Произошла ошибка: {context.error}")

    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Произошла техническая ошибка. Попробуйте позже или обратитесь к оператору."
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение об ошибке: {e}")


def main():
    """Запуск образовательного консультанта"""
    print("🚀 Запускаю образовательного консультанта с поддержкой операторов...")

    if not Settings.TELEGRAM_TOKEN:
        print("❌ Ошибка: TELEGRAM_TOKEN не найден в переменных окружения!")
        print("💡 Добавьте TELEGRAM_TOKEN в файл .env")
        return

    if not Settings.MANAGER_USER_ID:
        print("⚠️ Предупреждение: MANAGER_USER_ID не настроен!")
        print("💡 Добавьте MANAGER_USER_ID в файл .env для работы с операторами")

    application = Application.builder().token(Settings.TELEGRAM_TOKEN).build()

    # Инициализация сервисов
    setup_bot_data(application)

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", operator_start_command))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("get_id", get_id_command))

    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    print("✅ Образовательный консультант запущен!")
    print("🎓 Готов помогать студентам найти программы обучения за рубежом")
    print("👨‍💼 Система операторов активирована")

    if Settings.MANAGER_USER_ID:
        print(f"📞 Операторский чат: {Settings.MANAGER_USER_ID}")

    print("\n🔧 Команды для операторов:")
    print("• /help_operator - справка")
    print("• /stats - статистика")
    print("• /reply_USER_ID текст - ответить клиенту")
    print("\n🚀 Бот работает...")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def get_id_command(update: Update, context):
    """Команда для получения ID пользователя и чата"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Не указан"

    info_text = f"""
🆔 **Ваши идентификаторы:**

👤 **User ID:** `{user_id}`
💬 **Chat ID:** `{chat_id}` 
📝 **Username:** @{username}

💡 **Для настройки операторов используйте User ID**
    """

    await update.message.reply_text(info_text)
if __name__ == "__main__":
    main()