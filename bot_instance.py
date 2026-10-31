import telebot
from telebot import apihelper
from google import genai
from config import TELEGRAM_TOKEN, GEMINI_API_KEY

apihelper.SESSION_TIME_TO_LIVE = 5 * 60

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Inisialisasi Gemini Client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)