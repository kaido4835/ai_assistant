# handlers/__init__.py
from .commands import start_command
# from .messages import handle_message  # раскомментируйте когда создадите
# from .callbacks import callback_handler  # раскомментируйте когда создадите

__all__ = [
    'start_command',
    # 'handle_message',
    # 'callback_handler'
]