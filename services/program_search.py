from typing import Dict, List
from database.education_db import EducationDatabase
from database.models import Program

class ProgramSearchService:
    def __init__(self, db: EducationDatabase):
        self.db = db

    def search_programs(self, filters: Dict) -> List[Program]:
        """Поиск программ по фильтрам"""
        return self.db.search_programs(filters)

    def format_programs_response(self, programs: List[Program]) -> str:
        """Форматирование ответа с программами"""
        if not programs:
            return """
Хм, по таким критериям не нашел подходящих программ 🤔

Может, пересмотрим бюджет? Или расширим список стран?
Напиши, что хочешь изменить, и найдем варианты!
            """

        response = "Отлично! Вот что нашел по твоим критериям 🎯\n\n"

        for i, program in enumerate(programs[:3], 1):
            cost_text = "Бесплатно" if program.cost_per_year == 0 else f"€{program.cost_per_year:,}/год"
            response += f"""
**{i}. {program.program_name}**
🏛️ {program.university}, {program.country}
💰 {cost_text}
⏱️ {program.duration}
📅 Дедлайн: {program.application_deadline}

"""

        response += "Какая программа интересует больше? Или хочешь узнать подробности о процессе поступления? 🤓"
        return response