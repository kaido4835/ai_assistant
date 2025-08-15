import os
import asyncio

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from huggingface_hub import InferenceClient

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAMTOKEN")
HUGGINGFACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# Инициализация AI клиента
ai_client = InferenceClient(
    provider="fireworks-ai",
    api_key=HUGGINGFACE_TOKEN
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "Привет! Я AI бот 🤖\n"
        "Просто напиши мне любой вопрос, и я отвечу!\n"
        "Используй /help для получения помощи."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🤖 Команды бота:
/start - Запустить бота
/help - Показать это сообщение
/model - Показать текущую модель

Просто напиши любой вопрос, и я отвечу с помощью AI!
    """
    await update.message.reply_text(help_text)


async def model_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о модели"""
    await update.message.reply_text("🧠 Текущая модель: openai/gpt-oss-120b via Fireworks AI")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений"""
    user_message = update.message.text
    user_name = update.effective_user.first_name

    # Показать, что бот печатает
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Отправить запрос к AI
        completion = ai_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "Ты полезный помощник. Отвечай кратко и по делу на русском языке."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=500,
            temperature=0.7
        )

        ai_response = completion.choices[0].message.content

        # Отправить ответ пользователю
        await update.message.reply_text(f"🤖 {ai_response}")

    except Exception as e:
        print(f"Ошибка AI: {e}")
        await update.message.reply_text(
            "😔 Извини, произошла ошибка при обращении к AI. Попробуй еще раз!"
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    print(f"Ошибка: {context.error}")


def main():
    """Запуск бота"""
    print("🚀 Запускаю Telegram бота...")

    # Создание приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("model", model_info))

    # Обработчик всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запуск бота
    print("✅ Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()