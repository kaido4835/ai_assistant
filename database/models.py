from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Program:
    id: Optional[int]
    country: str
    university: str
    program_name: str
    degree: str
    field: str
    language: str
    duration: str
    cost_per_year: float
    requirements: str
    application_deadline: str
    website: str


@dataclass
class UserSession:
    user_id: int
    stage: str = "initial"
    profile: Dict = None
    conversation_history: List[str] = None
    interest_score: int = 0
    last_activity: datetime = None

    def __post_init__(self):
        if self.profile is None:
            self.profile = {}
        if self.conversation_history is None:
            self.conversation_history = []
        if self.last_activity is None:
            self.last_activity = datetime.now()


@dataclass
class Lead:
    id: Optional[int]
    user_id: int
    status: str = 'new'
    score: int = 0
    manager_notes: str = ''
    created_at: datetime = None
    contacted_at: Optional[datetime] = None