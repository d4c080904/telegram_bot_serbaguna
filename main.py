import asyncio
import logging
from aiogram import Bot
from aiogram.types import BotCommand
from bot_instance import bot, dp
from database.db import create_pool, setup_db, close_pool

# IMPORT ROUTER
from handlers import start as start_router
from handlers import calorie as calorie_router
from handlers import pt_chat as pt_chat_router
from handlers import gym as gym_router
from handlers import equipment as equipment_router
from handlers import progress as progress_router
from handlers import meal_planner as meal_router
from handlers import export as export_router 
from handlers import voice as voice_router
from handlers import barcode as barcode_router # <--- IMPORT BARU UNTUK BARCODE
from handlers import router as main_router 
from services.ai import init_models

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
    await init_models()
    await set_bot_commands(bot)
    
    # DAFTARIN ROUTER (URUTAN SANGAT PENTING!)
    dp.include_router(start_router.router)
    dp.include_router(calorie_router.router)
    dp.include_router(pt_chat_router.router)
    dp.include_router(gym_router.router)
    dp.include_router(equipment_router.router)
    dp.include_router(progress_router.router)
    dp.include_router(meal_router.router)
    dp.include_router(export_router.router)
    dp.include_router(voice_router.router)
    dp.include_router(barcode_router.router) # <--- DAFTARIN DI SINI
    dp.include_router(main_router.router) 
    
    logger.info("✅ Semua Router berhasil didaftarkan.")
    
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