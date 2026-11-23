import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database.queries import get_users_for_reminder
from bot_instance import bot

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Asia/Jakarta")

async def send_reminder(context="malam"):
    logger.info(f"⏰ Menjalankan pengingat: {context}...")
    users = await get_users_for_reminder()
    
    for user_id in users:
        try:
            if context == "pagi":
                teks = "🌅 <b>SELAMAT PAGI!</b>\n\nJangan lupa sarapan bro. Yuk foto makanan lu sekarang biar api (streak) 🔥 lu tetep nyala!"
            elif context == "siang":
                teks = "☀️ <b>WAKTUNYA MAKAN SIANG!</b>\n\nUdah makan siang belum? Jangan lupa dicatat ya biar kalori harian lu seimbang."
            else:
                teks = "🌙 <b>PENGINGAT MALAM</b>\n\nBro, ini pengingat terakhir hari ini. Jangan sampe lu lupa catat makanan lu ya, biar api (streak) 🔥 lu gak padam besok!"
            
            await bot.send_message(chat_id=user_id, text=teks, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Gagal kirim reminder ke {user_id}: {e}")

def start_scheduler():
    # Jadwal Pagi (08:00)
    scheduler.add_job(lambda: send_reminder("pagi"), CronTrigger(hour=8, minute=0))
    # Jadwal Siang (13:00)
    scheduler.add_job(lambda: send_reminder("siang"), CronTrigger(hour=13, minute=0))
    # Jadwal Malam (20:00)
    scheduler.add_job(lambda: send_reminder("malam"), CronTrigger(hour=20, minute=0))
    
    scheduler.start()
    logger.info("✅ Scheduler Reminder (Pagi, Siang, Malam) berhasil dijalankan")