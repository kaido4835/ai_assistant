import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from .models import Program, UserSession, Lead


class EducationDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
        self.populate_sample_data()

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
                profile TEXT,
                stage TEXT DEFAULT 'initial',
                interest_score INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица лидов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT DEFAULT 'new',
                score INTEGER DEFAULT 0,
                manager_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                contacted_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        conn.commit()
        conn.close()

    def populate_sample_data(self):
        """Заполнение примерами из исходного кода"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM programs")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return

        # Ваши программы из EDUCATION_DATABASE
        sample_programs = [
            ("Германия", "Технический университет Мюнхена", "MSc Artificial Intelligence", "магистратура", "ИИ, ИТ",
             "английский", "2 года", 0, "IELTS 6.5+, диплом бакалавра в ИТ", "15 июля", "https://tum.de/ai"),
            ("Нидерланды", "Делфтский технический университет", "MSc Computer Science - AI Track", "магистратура",
             "ИИ, ИТ", "английский", "2 года", 2314, "IELTS 6.5+, техническое образование", "1 февраля",
             "https://tudelft.nl/ai"),
            ("Чехия", "Карлов университет", "MSc Computer Science", "магистратура", "ИТ, ИИ", "английский", "2 года",
             4000, "IELTS 6.0+, диплом в ИТ/математике", "30 апреля", "https://cuni.cz/cs"),
            ("Польша", "Варшавский университет технологий", "MSc Data Science and AI", "магистратура",
             "ИИ, Data Science", "английский", "1.5 года", 3000, "IELTS 6.0+, бакалавр в технической области", "31 мая",
             "https://pw.edu.pl/datascience"),
            ("Германия", "RWTH Aachen", "Computer Science", "бакалавриат", "ИТ", "английский", "3 года", 0,
             "IELTS 6.0+, аттестат с математикой", "15 июля", "https://rwth-aachen.de/cs"),
            ("Нидерланды", "Университет Амстердама", "BSc Artificial Intelligence", "бакалавриат", "ИИ", "английский",
             "3 года", 2314, "IELTS 6.0+, математика на высоком уровне", "1 мая", "https://uva.nl/ai-bachelor"),
            ("Швеция", "Королевский технологический институт", "MSc Machine Learning", "магистратура",
             "ИИ, машинное обучение", "английский", "2 года", 0, "IELTS 6.5+, техническое/математическое образование",
             "15 января", "https://kth.se/ml"),
            ("Финляндия", "Университет Хельсинки", "MSc Data Science", "магистратура", "Data Science", "английский",
             "2 года", 0, "IELTS 6.5+, математическое/техническое образование", "31 января",
             "https://helsinki.fi/datascience")
        ]

        cursor.executemany('''
            INSERT INTO programs (country, university, program_name, degree, field, language, 
                                duration, cost_per_year, requirements, application_deadline, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_programs)

        conn.commit()
        conn.close()

    def search_programs(self, filters: Dict) -> List[Program]:
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

        query += " ORDER BY cost_per_year ASC LIMIT 5"

        cursor.execute(query, params)
        programs = []

        for row in cursor.fetchall():
            program = Program(
                id=row[0], country=row[1], university=row[2], program_name=row[3],
                degree=row[4], field=row[5], language=row[6], duration=row[7],
                cost_per_year=row[8], requirements=row[9], application_deadline=row[10],
                website=row[11]
            )
            programs.append(program)

        conn.close()
        return programs

    def save_user_session(self, session: UserSession):
        """Сохранение сессии пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, profile, stage, interest_score, last_activity)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            session.user_id,
            json.dumps(session.profile),
            session.stage,
            session.interest_score,
            session.last_activity
        ))

        conn.commit()
        conn.close()

    def get_user_session(self, user_id: int) -> Optional[UserSession]:
        """Получение сессии пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return UserSession(
                user_id=row[0],
                profile=json.loads(row[4]) if row[4] else {},
                stage=row[5],
                interest_score=row[6],
                last_activity=datetime.fromisoformat(row[8]) if row[8] else datetime.now()
            )
        return None

    def create_lead(self, user_id: int, score: int) -> int:
        """Создание лида"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO leads (user_id, score, status)
            VALUES (?, ?, 'new')
        ''', (user_id, score))

        lead_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return lead_id