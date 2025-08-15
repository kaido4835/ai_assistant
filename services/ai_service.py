from huggingface_hub import InferenceClient
from config.settings import Settings, AIPrompts
import json


class AIService:
    def __init__(self):
        self.client = InferenceClient(
            provider=Settings.AI_PROVIDER,
            api_key=Settings.HUGGINGFACE_TOKEN
        )

    async def get_response(self, message: str, user_profile: dict) -> tuple[str, int]:
        """Получение ответа от AI с оценкой интереса"""

        context = AIPrompts.CONSULTANT_SYSTEM + f"\n\n📊 ПРОФИЛЬ КЛИЕНТА: {json.dumps(user_profile, ensure_ascii=False)}"

        try:
            completion = self.client.chat.completions.create(
                model=Settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": message}
                ],
                max_tokens=Settings.MAX_TOKENS,
                temperature=Settings.TEMPERATURE
            )

            response = completion.choices[0].message.content

            # Оценка интереса (ваша логика)
            interest_score = self._calculate_interest_score(message)

            return response, interest_score

        except Exception as e:
            print(f"Ошибка AI: {e}")
            return "Извини, небольшая техническая заминка 😅 Можешь повторить вопрос?", 0

    def _calculate_interest_score(self, message: str) -> int:
        """Расчет уровня заинтересованности"""
        interest_keywords = {
            'high': ['хочу поступать', 'когда подавать', 'какие документы', 'помогите подать'],
            'medium': ['интересно', 'подходит', 'рассматриваю', 'думаю', 'планирую'],
            'low': ['просто узнать', 'в будущем', 'может быть']
        }

        interest_score = 0
        message_lower = message.lower()

        for level, keywords in interest_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            if level == 'high':
                interest_score += matches * 3
            elif level == 'medium':
                interest_score += matches * 2
            else:
                interest_score += matches * 1

        if '?' in message:
            interest_score += 1
        if any(word in message_lower for word in ['стоимость', 'цена', 'дедлайн', 'требования']):
            interest_score += 2

        return min(interest_score, 10)