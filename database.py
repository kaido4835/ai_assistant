# database.py - Расширенная база данных и утилиты

import json
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class EducationDatabase:
    """Класс для работы с базой данных образовательных программ"""

    def __init__(self, db_path: str = "education.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица программ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                university TEXT NOT NULL,
                program_name TEXT NOT NULL,
                degree TEXT NOT NULL,
                field TEXT NOT NULL,
                language TEXT NOT NULL,
                duration TEXT NOT NULL,
                cost_per_year REAL NOT NULL,
                requirements TEXT NOT NULL,
                application_deadline TEXT NOT NULL,
                website TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                profile TEXT,  -- JSON с профилем
                stage TEXT DEFAULT 'initial',
                interest_score INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица взаимодействий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_type TEXT,  -- user_message, bot_response, button_click
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Таблица лидов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT DEFAULT 'new',  -- new, contacted, converted, lost
                manager_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                contacted_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        conn.commit()
        conn.close()

        # Заполняем базовыми данными если пуста
        self.populate_sample_data()

    def populate_sample_data(self):
        """Заполнение базы примерами программ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Проверяем, есть ли данные
        cursor.execute("SELECT COUNT(*) FROM programs")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return

        sample_programs = [
            # Германия
            ("Германия", "Технический университет Мюнхена", "MSc Artificial Intelligence", "магистратура", "ИИ, ИТ",
             "английский", "2 года", 0, "IELTS 6.5+, диплом бакалавра в ИТ", "15 июля", "https://tum.de/ai"),
            ("Германия", "RWTH Aachen", "Computer Science", "бакалавриат", "ИТ", "английский", "3 года", 0,
             "IELTS 6.0+, аттестат с математикой", "15 июля", "https://rwth-aachen.de/cs"),
            ("Германия", "Университет Фрайбурга", "MSc Computer Science", "магистратура", "ИТ", "английский", "2 года",
             1500, "IELTS 6.5+, техническое образование", "1 марта", "https://uni-freiburg.de/cs"),

            # Нидерланды
            ("Нидерланды", "Делфтский технический университет", "MSc Computer Science - AI Track", "магистратура",
             "ИИ, ИТ", "английский", "2 года", 2314, "IELTS 6.5+, техническое образование", "1 февраля",
             "https://tudelft.nl/ai"),
            ("Нидерланды", "Университет Амстердама", "BSc Artificial Intelligence", "бакалавриат", "ИИ", "английский",
             "3 года", 2314, "IELTS 6.0+, математика на высоком уровне", "1 мая", "https://uva.nl/ai-bachelor"),
            ("Нидерланды", "Эйндховенский технический университет", "MSc Data Science", "магистратура",
             "Data Science, ИТ", "английский", "2 года", 2314, "IELTS 6.5+, математическое/техническое образование",
             "1 февраля", "https://tue.nl/datascience"),

            # Чехия
            ("Чехия", "Карлов университет", "MSc Computer Science", "магистратура", "ИТ, ИИ", "английский", "2 года",
             4000, "IELTS 6.0+, диплом в ИТ/математике", "30 апреля", "https://cuni.cz/computer-science"),
            ("Чехия", "Чешский технический университет", "BSc Computer Science", "бакалавриат", "ИТ", "английский",
             "3 года", 3500, "IELTS 6.0+, аттестат с математикой", "31 марта", "https://cvut.cz/cs"),
            ("Чехия", "Масариков университет", "MSc Applied Informatics", "магистратура", "ИТ, Data Science",
             "английский", "2 года", 3000, "IELTS 6.0+, техническое образование", "28 февраля",
             "https://muni.cz/informatics"),

            # Польша
            ("Польша", "Варшавский университет технологий", "MSc Data Science and AI", "магистратура",
             "ИИ, Data Science", "английский", "1.5 года", 3000, "IELTS 6.0+, бакалавр в технической области", "31 мая",
             "https://pw.edu.pl/datascience"),
            ("Польша", "Краковский технический университет", "BSc Computer Science", "бакалавриат", "ИТ", "английский",
             "3.5 года", 2500, "IELTS 6.0+, аттестат", "30 июня", "https://pk.edu.pl/cs"),
            ("Польша", "Вроцлавский университет", "MSc Computer Science", "магистратура", "ИТ", "английский", "2 года",
             2800, "IELTS 6.0+, диплом в ИТ", "15 мая", "https://uni.wroc.pl/cs"),

            # Франция
            ("Франция", "École Polytechnique", "MSc Data Science for Business", "магистратура", "Data Science, бизнес",
             "английский", "2 года", 12000, "IELTS 7.0+, GMAT/GRE", "15 марта",
             "https://polytechnique.edu/datascience"),
            ("Франция", "Сорбонна", "MSc Computer Science", "магистратура", "ИТ", "английский", "2 года", 8000,
             "IELTS 6.5+, техническое образование", "1 апреля", "https://sorbonne-universite.fr/cs"),

            # Италия
            ("Италия", "Политехнический университет Милана", "MSc Computer Science and Engineering", "магистратура",
             "ИТ", "английский", "2 года", 3900, "IELTS 6.0+, техническое образование", "31 марта",
             "https://polimi.it/cs"),
            ("Италия", "Университет Болоньи", "MSc Artificial Intelligence", "магистратура", "ИИ", "английский",
             "2 года", 2800, "IELTS 6.5+, техническое/математическое образование", "30 апреля", "https://unibo.it/ai"),

            # Испания
            ("Испания", "Политехнический университет Каталонии", "MSc in Data Science", "магистратура", "Data Science",
             "английский", "1 год", 7000, "IELTS 6.5+, техническое образование", "15 июня",
             "https://upc.edu/datascience"),
            ("Испания", "Университет Карлоса III", "BSc Computer Science", "бакалавриат", "ИТ", "английский", "4 года",
             5000, "IELTS 6.0+, аттестат", "31 мая", "https://uc3m.es/cs"),

            # Австрия
            ("Австрия", "Венский технический университет", "MSc Computer Science", "магистратура", "ИТ", "английский",
             "2 года", 1500, "IELTS 6.5+, техническое образование", "31 марта", "https://tuwien.at/cs"),

            # Бельгия
            ("Бельгия", "Католический университет Лёвена", "MSc Computer Science", "магистратура", "ИТ", "английский",
             "2 года", 4175, "IELTS 6.5+, техническое образование", "1 марта", "https://kuleuven.be/cs"),

            # Швеция
            ("Швеция", "Королевский технологический институт", "MSc Machine Learning", "магистратура",
             "ИИ, машинное обучение", "английский", "2 года", 0, "IELTS 6.5+, техническое/математическое образование",
             "15 января", "https://kth.se/ml"),
            ("Швеция", "Чалмерский технологический университет", "MSc Computer Science", "магистратура", "ИТ",
             "английский", "2 года", 0, "IELTS 6.5+, техническое образование", "15 января", "https://chalmers.se/cs"),

            # Финляндия
            ("Финляндия", "Университет Хельсинки", "MSc Data Science", "магистратура", "Data Science", "английский",
             "2 года", 0, "IELTS 6.5+, математическое/техническое образование", "31 января",
             "https://helsinki.fi/datascience"),
            ("Финляндия", "Университет Аалто", "MSc Computer Science", "магистратура", "ИТ", "английский", "2 года", 0,
             "IELTS 6.5+, техническое образование", "31 января", "https://aalto.fi/cs")
        ]

        cursor.executemany('''
            INSERT INTO programs (country, university, program_name, degree, field, language, 
                                duration, cost_per_year, requirements, application_deadline, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_programs)

        conn.commit()
        conn.close()

    def search_programs(self, filters: Dict) -> List[Dict]:
        """Поиск программ по фильтрам"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM programs WHERE 1=1"
        params = []

        if filters.get('degree'):
            query += " AND degree = ?"
            params.append(filters['degree'])

        if filters.get('field'):
            field_conditions = []
            for field in filters['field']:
                field_conditions.append("field LIKE ?")
                params.append(f"%{field}%")
            if field_conditions:
                query += f" AND ({' OR '.join(field_conditions)})"

        if filters.get('max_budget') is not None:
            query += " AND cost_per_year <= ?"
            params.append(filters['max_budget'])

        if filters.get('language'):
            query += " AND language LIKE ?"
            params.append(f"%{filters['language']}%")

        if filters.get('country'):
            query += " AND country = ?"
            params.append(filters['country'])

        query += " ORDER BY cost_per_year ASC LIMIT 10"

        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = []

        for row in cursor.fetchall():
            program = dict(zip(columns, row))
            results.append(program)

        conn.close()
        return results

    def save_user(self, user_id: int, user_data: Dict):
        """Сохранение данных пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, profile, stage, interest_score, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_data.get('username'),
            user_data.get('first_name'),
            user_data.get('last_name'),
            json.dumps(user_data.get('profile', {})),
            user_data.get('stage', 'initial'),
            user_data.get('interest_score', 0),
            datetime.now()
        ))

        conn.commit()
        conn.close()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение данных пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            columns = [description[0] for description in cursor.description]
            user_data = dict(zip(columns, row))
            user_data['profile'] = json.loads(user_data['profile'])
            conn.close()
            return user_data

        conn.close()
        return None

    def log_interaction(self, user_id: int, message_type: str, content: str):
        """Логирование взаимодействий"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO interactions (user_id, message_type, content)
            VALUES (?, ?, ?)
        ''', (user_id, message_type, content))

        conn.commit()
        conn.close()

    def create_lead(self, user_id: int) -> int:
        """Создание лида"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO leads (user_id, status)
            VALUES (?, 'new')
        ''', (user_id,))

        lead_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return lead_id

    def get_statistics(self) -> Dict:
        """Получение статистики"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(last_activity) = DATE('now')")
        active_today = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'new'")
        new_leads = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(interest_score) FROM users WHERE interest_score > 0")
        avg_interest = cursor.fetchone()[0] or 0

        # Топ стран
        cursor.execute('''
            SELECT country, COUNT(*) as searches 
            FROM interactions i
            JOIN users u ON i.user_id = u.user_id
            WHERE i.content LIKE '%country%' 
            GROUP BY country 
            ORDER BY searches DESC 
            LIMIT 5
        ''')
        top_countries = cursor.fetchall()

        conn.close()

        return {
            'total_users': total_users,
            'active_today': active_today,
            'new_leads': new_leads,
            'avg_interest': round(avg_interest, 1),
            'top_countries': top_countries
        }


class LeadScoring:
    """Система скоринга лидов"""

    @staticmethod
    def calculate_score(user_profile: Dict, interactions: List[str]) -> int:
        """Расчет скора лида от 0 до 100"""
        score = 0

        # Полнота профиля (0-30 баллов)
        profile_fields = ['degree', 'field', 'max_budget', 'language']
        filled_fields = sum(1 for field in profile_fields if user_profile.get(field))
        score += (filled_fields / len(profile_fields)) * 30

        # Активность в диалоге (0-25 баллов)
        if len(interactions) > 10:
            score += 25
        elif len(interactions) > 5:
            score += 15
        elif len(interactions) > 2:
            score += 10

        # Ключевые слова интереса (0-25 баллов)
        interest_keywords = [
            'хочу', 'планирую', 'готов', 'когда', 'как поступить',
            'стоимость', 'требования', 'документы', 'виза', 'сроки'
        ]

        total_text = ' '.join(interactions).lower()
        keyword_matches = sum(1 for keyword in interest_keywords if keyword in total_text)
        score += min(keyword_matches * 3, 25)

        # Конкретные вопросы (0-20 баллов)
        specific_keywords = [
            'дедлайн', 'заявка', 'поступление', 'университет',
            'программа', 'магистратура', 'бакалавриат'
        ]

        specific_matches = sum(1 for keyword in specific_keywords if keyword in total_text)
        score += min(specific_matches * 4, 20)

        return min(int(score), 100)

    @staticmethod
    def get_lead_priority(score: int) -> str:
        """Определение приоритета лида"""
        if score >= 70:
            return "🔥 Горячий"
        elif score >= 50:
            return "🌡️ Тёплый"
        elif score >= 30:
            return "❄️ Холодный"
        else:
            return "🧊 Очень холодный"


class ReportGenerator:
    """Генератор отчетов"""

    def __init__(self, db: EducationDatabase):
        self.db = db

    def generate_daily_report(self) -> str:
        """Ежедневный отчет"""
        stats = self.db.get_statistics()

        report = f"""
📊 **ЕЖЕДНЕВНЫЙ ОТЧЕТ**
📅 {datetime.now().strftime('%d.%m.%Y')}

👥 **Пользователи:**
• Всего: {stats['total_users']}
• Активных сегодня: {stats['active_today']}
• Средний интерес: {stats['avg_interest']}/10

🎯 **Лиды:**
• Новых: {stats['new_leads']}

🌍 **Популярные направления:**
{chr(10).join([f"• {country}: {count}" for country, count in stats['top_countries']])}

📈 **Конверсия:** {(stats['new_leads'] / max(stats['active_today'], 1) * 100):.1f}%
        """

        return report

    def generate_lead_report(self, user_id: int) -> str:
        """Отчет по конкретному лиду"""
        user_data = self.db.get_user(user_id)
        if not user_data:
            return "Пользователь не найден"

        # Получаем историю взаимодействий
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT content, timestamp FROM interactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', (user_id,))
        interactions = cursor.fetchall()
        conn.close()

        # Расчет скора
        interaction_texts = [interaction[0] for interaction in interactions]
        score = LeadScoring.calculate_score(user_data['profile'], interaction_texts)
        priority = LeadScoring.get_lead_priority(score)

        report = f"""
👤 **ПРОФИЛЬ ЛИДА**

🆔 **ID:** {user_id}
👤 **Имя:** {user_data.get('first_name', 'Не указано')}
📊 **Скор:** {score}/100 {priority}
🎯 **Стадия:** {user_data['stage']}

📋 **Профиль:**
{json.dumps(user_data['profile'], ensure_ascii=False, indent=2)}

💬 **Последние сообщения:**
{chr(10).join([f"• {content[:100]}..." for content, _ in interactions[:5]])}

🕐 **Последняя активность:** {user_data['last_activity']}
        """

        return report


# Конфигурация промптов для AI
AI_PROMPTS = {
    'consultant': """
Ты опытный консультант по образованию за рубежом. Твоя задача:

1. КВАЛИФИКАЦИЯ ЛИДОВ:
   - Отсеивай несерьезных клиентов (студенты без планов, просто интересующиеся)
   - Ищи мотивированных людей с конкретными целями

2. СБОР ИНФОРМАЦИИ:
   - Уровень образования (текущий/желаемый)
   - Область интересов
   - Бюджет (важно!)
   - Предпочтения по стране/языку
   - Сроки поступления

3. СТИЛЬ ОБЩЕНИЯ:
   - Дружелюбный, но профессиональный
   - Задавай уточняющие вопросы
   - Не перегружай информацией
   - Мотивируй к действию

4. КРАСНЫЕ ФЛАГИ (низкий приоритет):
   - "Просто интересно"
   - "Может быть когда-нибудь"
   - Уклонение от вопросов о бюджете
   - Нереалистичные ожидания

ПОМНИ: Твоя цель - найти готовых к поступлению клиентов и передать их менеджеру.
    """,

    'qualification': """
Оцени заинтересованность клиента по шкале 1-10 на основе:
- Конкретности вопросов
- Готовности предоставлять информацию
- Упоминания сроков/планов
- Вопросов о процедурах
- Реалистичности запросов

1-3: Просто интересуется
4-6: Рассматривает варианты  
7-8: Серьезно планирует
9-10: Готов к действиям
    """
}

if __name__ == "__main__":
    # Тестирование базы данных
    db = EducationDatabase()

    # Поиск программ
    filters = {
        'degree': 'магистратура',
        'field': ['ИИ'],
        'max_budget': 5000
    }

    results = db.search_programs(filters)
    print(f"Найдено программ: {len(results)}")

    for program in results[:3]:
        print(f"- {program['program_name']} в {program['university']}")

    # Генерация отчета
    reporter = ReportGenerator(db)
    print("\n" + reporter.generate_daily_report())