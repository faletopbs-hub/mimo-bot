import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MIMO_API_KEY = os.getenv("MIMO_API_KEY")
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2-flash")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1644619383"))
GROUP_ID = int(os.getenv("GROUP_ID", "0")) if os.getenv("GROUP_ID") else None
LEARNING_DAYS = int(os.getenv("LEARNING_DAYS", "3"))