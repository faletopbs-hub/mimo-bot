from openai import AsyncOpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, MIMO_MODEL
import database as db

client = AsyncOpenAI(
    api_key=MIMO_API_KEY,
    base_url=MIMO_BASE_URL,
)

# Жёсткая инструкция — не меняется через /setprompt
HARD_RULES = """Твоё имя — Федя. Ты всегда Федя. Если к тебе обращаются "Федя" — отвечай обязательно, даже если сообщение начинается с этого слова.
Отвечай коротко — 1-2 предложения, максимум 15 слов. Не будь вежливым ассистентом — ты свой в этой компании.
Сейчас тебе пишет: {user_name} ({user_gender}). Обращайся к нему соответственно."""


async def generate_reply(user_id: int, user_message: str) -> str:
    history = await db.get_last_messages(limit=40)
    examples = "\n".join(f"{username}: {text}" for username, text in history if text)

    custom_prompt = await db.get_prompt()

    user = await db.get_user(user_id)
    if user:
        user_name, user_gender = user
    else:
        user_name, user_gender = "незнакомец", "неизвестно"

    parts = []
    if custom_prompt:
        parts.append(custom_prompt)
    parts.append(HARD_RULES.format(user_name=user_name, user_gender=user_gender))
    if examples:
        parts.append(f"Примеры стиля общения в чате:\n---\n{examples}\n---")

    system_content = "\n\n".join(parts)

    response = await client.chat.completions.create(
        model=MIMO_MODEL,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_message},
        ],
        temperature=0.9,
        max_tokens=60,
        frequency_penalty=0.5,
        presence_penalty=0.3,
    )

    return response.choices[0].message.content.strip()
