import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN belum diisi di file .env!")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY belum diisi di file .env!")

COOKIES_FILE = "cookies.txt"
DB_PATH = "bot_history.db"
BATAS_UKURAN_VIDEO = 49 * 1024 * 1024

RATE_LIMIT_MAX = 15
RATE_LIMIT_WINDOW = 60
CHAT_HISTORY_LIMIT = 20
CHAT_MAX_MESSAGES = 40

PRIORITAS_MODEL = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.3-70b-specdec",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}