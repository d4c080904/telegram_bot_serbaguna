import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from groq import Groq
from config import TELEGRAM_TOKEN, GROQ_API_KEY

logger = logging.getLogger(__name__)

# --- INIT BOT AIOGRAM ---
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# --- INIT GROQ CLIENT ---
groq_client = Groq(api_key=GROQ_API_KEY)