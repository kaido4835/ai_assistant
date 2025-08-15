from datetime import datetime
from database.education_db import EducationDatabase
from database.models import UserSession
from config.settings import Settings

class LeadService:
    def __init__(self, db: EducationDatabase):
        self.db = db

    def should_notify_manager(self, session: UserSession) -> bool:
        """Проверка, нужно ли уведомить менеджера"""
        return (session.interest_score >= Settings.MANAGER_NOTIFICATION_THRESHOLD and
                session.stage == "showing_results")

    def create_lead_report(self, session: UserSession) -> str:
        """Создание отчета о лиде для менеджера"""
        return f"""
🔥 **Новый лид!**

👤 **Клиент ID:** {session.user_id}
📊 **Интерес:** {session.interest_score}/10
🎯 **Профиль:**
{session.profile}

💬 **Последние сообщения:**
{chr(10).join(session.conversation_history[-3:]) if session.conversation_history else 'Нет сообщений'}

🕐 **Время:** {session.last_activity.strftime('%H:%M %d.%m.%Y')}
        """

    def calculate_lead_score(self, session: UserSession) -> int:
        """Расчет скора лида от 0 до 100"""
        score = 0

        # Полнота профиля (0-30 баллов)
        profile_fields = ['degree', 'field', 'max_budget', 'language']
        filled_fields = sum(1 for field in profile_fields if session.profile.get(field))
        score += (filled_fields / len(profile_fields)) * 30

        # Активность в диалоге (0-25 баллов)
        if len(session.conversation_history) > 10:
            score += 25
        elif len(session.conversation_history) > 5:
            score += 15
        elif len(session.conversation_history) > 2:
            score += 10

        # Интерес (0-45 баллов)
        score += session.interest_score * 4.5

        return min(int(score), 100)