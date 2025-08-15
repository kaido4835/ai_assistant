from telegram import Update
from telegram.ext import ContextTypes


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    print(f"Произошла ошибка: {context.error}")

    if update and update.message:
        await update.message.reply_text(
            "⚠️ Произошла техническая ошибка. Попробуйте позже."
        )


def log_user_activity(update: Update, action: str):
    """Логирование активности пользователей"""
    user = update.effective_user
    chat_id = update.effective_chat.id

    print(f"[{action}] Пользователь: {user.first_name} (@{user.username}) | Chat ID: {chat_id}")