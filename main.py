import logging
from telebot.types import BotCommand
from bot_instance import bot
from database.db import setup_db

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.FileHandler('bot.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Set Commands
bot.set_my_commands([
    BotCommand("start", "🏠 Menu utama & perkenalan"),
    BotCommand("menu", "🏠 Buka menu utama lagi"),
    BotCommand("help", "❓ Panduan lengkap"),
    BotCommand("chat", "💬 Mode ngobrol bebas sama AI"),
    BotCommand("reset", "🧹 Hapus history chat"),
    BotCommand("exit", "👋 Keluar dari mode chat"),
    BotCommand("gym", "💪 Asisten Gym pribadi"),
    BotCommand("cancel", "❌ Batalin input yang lagi jalan"),
    BotCommand("stats", "📊 Statistik pemakaian lu"),
])

# IMPORT SEMUA HANDLERS DI SINI
import handlers.start
import handlers.chat
import handlers.gym
import handlers.calorie
import handlers.voice
import handlers.progress
import handlers.meal_planner # <--- TAMBAHAN BARU
import handlers.downloader
import handlers.router

if __name__ == "__main__":
    setup_db()
    logger.info("🚀 Bot Full Power V14 (GYM MODE) berhasil jalan!")
    bot.infinity_polling()