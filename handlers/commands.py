from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import Settings
from utils.session_manager import SessionManager

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    session_manager: SessionManager = context.bot_data['session_manager']
    session = session_manager.get_or_create_session(update.effective_user.id)
    session.stage = "initial"

    keyboard = [
        [KeyboardButton("🎓 Хочу учиться за границей")],
        [KeyboardButton("ℹ️ Узнать о процессе"), KeyboardButton("💬 Связаться с менеджером")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    await update.message.reply_text(Settings.WELCOME_MESSAGE, reply_markup=reply_markup)
    session_manager.save_session(session)