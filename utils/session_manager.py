from datetime import datetime
from typing import Dict
from database.models import UserSession
from database.education_db import EducationDatabase

class SessionManager:
    def __init__(self, db: EducationDatabase):
        self.db = db
        self.active_sessions: Dict[int, UserSession] = {}

    def get_or_create_session(self, user_id: int) -> UserSession:
        """Получить или создать сессию пользователя"""
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            session.last_activity = datetime.now()
            return session

        # Попробовать загрузить из БД
        session = self.db.get_user_session(user_id)
        if not session:
            session = UserSession(user_id=user_id)

        session.last_activity = datetime.now()
        self.active_sessions[user_id] = session
        return session

    def save_session(self, session: UserSession):
        """Сохранить сессию"""
        self.db.save_user_session(session)
        self.active_sessions[session.user_id] = session

    async def extract_user_info(self, message: str, session: UserSession):
        """Извлечение информации о пользователе из сообщения (ваша логика)"""
        message_lower = message.lower()

        # Уровень образования
        if any(word in message_lower for word in ['магистр', 'магистратура', 'магистерская', 'второе высшее']):
            session.profile['degree'] = 'магистратура'
        elif any(word in message_lower for word in ['бакалавр', 'бакалавриат', 'первое высшее', 'первое образование']):
            session.profile['degree'] = 'бакалавриат'
        # ... остальная логика извлечения