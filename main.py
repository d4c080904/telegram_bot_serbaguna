import asyncio
import logging
import uvicorn
from aiogram import Bot
from aiogram.types import BotCommand
from bot_instance import bot, dp
from database.db import create_pool, setup_db, close_pool
from api_server import app as fastapi_app 

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
from handlers import barcode as barcode_router
from handlers import premium as premium_router
from handlers import admin as admin_router 
from handlers import commands as commands_router # ✅ IMPORT ROUTER BARU
from handlers import router as main_router 
from services.ai import init_models
from middlewares.premium_gate import PremiumGateMiddleware

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S', handlers=[logging.FileHandler('bot.log', encoding='utf-8'), logging.StreamHandler()])
logger = logging.getLogger(__name__) 

async def set_bot_commands(bot: Bot):
    # ✅ SEKARANG MENU SAMPING LENGKAP
    commands = [
        BotCommand(command="start", description="🏠 Menu Utama"),
        BotCommand(command="kalori", description="🍎 Catat Kalori & Gula"),
        BotCommand(command="air", description="💧 Progress & Air"),
        BotCommand(command="gym", description="💪 Program Gym"),
        BotCommand(command="pt", description="💬 Chat PT AI"),
        BotCommand(command="scan", description="🔍 Scan Alat Gym"),
        BotCommand(command="meal", description="🍳 Meal Planner"),
        BotCommand(command="pdf", description="📄 Laporan PDF"),
        BotCommand(command="stats", description="📊 Statistik"),
        BotCommand(command="myprogress", description="📊 Progres sepanjang masa"),
        BotCommand(command="help", description="❓ Bantuan"),
        BotCommand(command="cancel", description="❌ Batalin Aksi"),
    ]
    await bot.set_my_commands(commands)

async def main():
    logger.info("🚀 Memulai GymBot AI (Async Engine)...")
    await create_pool()
    await setup_db()
    await init_models()
    await set_bot_commands(bot)
    
    dp.message.middleware(PremiumGateMiddleware())
    dp.callback_query.middleware(PremiumGateMiddleware())
    
    dp.include_router(start_router.router)
    dp.include_router(commands_router.router) # ✅ DAFTARIN DI SINI
    dp.include_router(calorie_router.router)
    dp.include_router(pt_chat_router.router)
    dp.include_router(gym_router.router)
    dp.include_router(equipment_router.router)
    dp.include_router(progress_router.router)
    dp.include_router(meal_router.router)
    dp.include_router(export_router.router)
    dp.include_router(voice_router.router)
    dp.include_router(barcode_router.router)
    dp.include_router(premium_router.router)
    dp.include_router(admin_router.router)
    dp.include_router(main_router.router) 
    
    logger.info("✅ Semua Router berhasil didaftarkan.")
    
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve()) 
    
    logger.info("✅ Bot & Web Server berhasil jalan! (Mode Async)")
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