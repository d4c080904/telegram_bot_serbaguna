import asyncio
import logging
from aiogram import Bot
from aiogram.types import BotCommand
from bot_instance import bot, dp
from database.db import create_pool, setup_db, close_pool

# IMPORT ROUTER
from handlers import start as start_router

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.FileHandler('bot.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Menu utama & perkenalan"),
        BotCommand(command="menu", description="🏠 Buka menu utama lagi"),
        BotCommand(command="help", description="❓ Panduan lengkap"),
        BotCommand(command="gym", description="💪 Asisten Gym pribadi"),
        BotCommand(command="cancel", description="❌ Batalin input yang lagi jalan"),
        BotCommand(command="stats", description="📊 Statistik pemakaian lu"),
    ]
    await bot.set_my_commands(commands)

async def main():
    logger.info("🚀 Memulai GymBot AI (Async Engine)...")
    
    await create_pool()
    await setup_db()
    await set_bot_commands(bot)
    
    # DAFTARIN ROUTER DI SINI
    dp.include_router(start_router.router)
    logger.info("✅ Router Start berhasil didaftarkan.")
    
    logger.info("✅ Bot berhasil jalan! (Mode Async)")
    try:
        await dp.start_polling(bot)
    finally:
        await close_pool()
        await bot.session.close()
        logger.info("🔌 Bot dimatikan dengan bersih.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot dihentikan manual.")