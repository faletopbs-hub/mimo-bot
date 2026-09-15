import aiosqlite
import time
from pathlib import Path

# Bothost создаёт /app/data как persistent storage
DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "bot.db"


async def init_db():
    """Создаёт таблицы, если их нет."""
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
    """Возвращает последние N сообщений (для будущего промпта)."""
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
