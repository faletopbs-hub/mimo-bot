import aiosqlite
import time
from pathlib import Path

DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "bot.db"

# Начальный список людей (ID, имя, род)
INITIAL_USERS = [
    (1644619383, "Глеб", "мужской"),
    (6657840585, "Маша", "женский"),
    (8940835512, "Вонючий", "мужской"),
    (7594982062, "Авет", "мужской"),
    (6218156939, "Вика", "женский"),
    (6240170022, "Никита", "мужской"),
    (1406530915, "Арсений", "мужской"),
    (5902922130, "Петя", "мужской"),
    (5657322363, "Лариса", "женский"),
    (7051335090, "Аня", "женский"),
    (2099208854, "Носок ебаный", "мужской"),
    (6036960495, "Марк", "мужской"),
    (5383028624, "Тимур", "мужской"),
    (5049104257, "Артем", "мужской"),
    (7517730859, "Дружище", "мужской"),
    (6444735563, "сглыпа", "бот"),
]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                text TEXT,
                date INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT,
                media_type TEXT,
                date INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                gender TEXT DEFAULT 'мужской'
            )
        """)
        await db.commit()

        # Заполняем users при первом запуске
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            count = (await c.fetchone())[0]
        if count == 0:
            await db.executemany(
                "INSERT OR IGNORE INTO users (user_id, name, gender) VALUES (?, ?, ?)",
                INITIAL_USERS
            )
            await db.commit()


async def save_message(user_id: int, username: str, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (user_id, username, text, date) VALUES (?, ?, ?, ?)",
            (user_id, username, text, int(time.time()))
        )
        await db.commit()


async def save_media(file_id: str, media_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO media (file_id, media_type, date) VALUES (?, ?, ?)",
            (file_id, media_type, int(time.time()))
        )
        await db.commit()


async def set_state(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        await db.commit()


async def get_state(key: str, default: str = None) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM state WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def get_last_messages(limit: int = 40):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT username, text FROM messages ORDER BY id DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return list(reversed(rows))


async def get_random_media():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT file_id, media_type FROM media ORDER BY RANDOM() LIMIT 1"
        ) as cursor:
            return await cursor.fetchone()


# --- Пользователи ---

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT name, gender FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()


async def add_user(user_id: int, name: str, gender: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, name, gender) VALUES (?, ?, ?)",
            (user_id, name, gender)
        )
        await db.commit()


async def del_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()


async def list_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, name, gender FROM users ORDER BY name") as cursor:
            return await cursor.fetchall()


# --- Промпт ---

async def get_prompt() -> str:
    return await get_state("system_prompt", "")


async def set_prompt(text: str):
    await set_state("system_prompt", text)
