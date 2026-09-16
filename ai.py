from openai import AsyncOpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, MIMO_MODEL
import database as db

client = AsyncOpenAI(
    api_key=MIMO_API_KEY,
    base_url=MIMO_BASE_URL,
)

SYSTEM_PROMPT = """Ты — участник Telegram-чата. Твоя задача — отвечать в стиле этой группы.

Вот примеры сообщений из чата (для изучения стиля, сленга и манеры общения):
---
{examples}
---

Правила:
1. Отвечай КОРОТКО — 1-2 предложения, максимум 15 слов.
2. Используй тот же сленг, маты, манеру, что в примерах.
3. НЕ копируй примеры дословно — комбинируй их элементы по-новому.
4. Если не знаешь, что ответить — ответь коротко и в тему.
5. Не будь вежливым ассистентом — ты свой в этой компании.
"""


async def generate_reply(user_message: str) -> str:
    history = await db.get_last_messages(limit=40)
    examples = "\n".join(f"{username}: {text}" for username, text in history if text)

    if not examples:
        return ""

    prompt = SYSTEM_PROMPT.format(examples=examples)

    response = await client.chat.completions.create(
        model=MIMO_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.9,
        max_tokens=60,
        frequency_penalty=0.5,
        presence_penalty=0.3,
    )

    return response.choices[0].message.content.strip()
