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

    # Сохраняем в bot_data для доступа из хендлеров
    application.bot_data.update({
        'db': db,
        'ai_service': ai_service,
        'program_search': program_search,
        'lead_service': lead_service,
        'session_manager': session_manager
    })


def main():
    """Запуск образовательного консультанта"""
    print("🚀 Запускаю образовательного консультанта...")

    if not Settings.TELEGRAM_TOKEN:
        print("❌ Ошибка: TELEGRAM_TOKEN не найден!")
        return

    application = Application.builder().token(Settings.TELEGRAM_TOKEN).build()

    # Инициализация сервисов
    setup_bot_data(application)

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Образовательный консультант запущен!")
    print("🎓 Готов помогать студентам найти программы обучения за рубежом")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()