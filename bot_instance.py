import telebot
from telebot import apihelper
from groq import Groq
from config import TELEGRAM_TOKEN, GROQ_API_KEY

apihelper.SESSION_TIME_TO_LIVE = 5 * 60

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Inisialisasi Groq Client
groq_client = Groq(api_key=GROQ_API_KEY)