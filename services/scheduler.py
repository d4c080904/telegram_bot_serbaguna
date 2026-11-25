import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database.db import get_db
from database.queries import set_user_premium
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

async def auto_cut_vip_expired():
    """Auto-cut masa aktif VIP yang sudah lewat tanggal setiap hari pukul 00:05"""
    logger.info("🔄 Mulai auto-cut masa aktif VIP yang lewat")
    try:
        async with await get_db() as conn:
            # Ambil user yang premium_until sudah lewat tapi masih is_banned = FALSE
            rows = await conn.fetch(
                "SELECT user_id FROM users WHERE premium_until <= CURRENT_TIMESTAMP AND is_banned = FALSE"
            )
            for row in rows:
                user_id = str(row['user_id'])
                try:
                    await set_user_premium(user_id, days=0)  # Hapus masa aktif (set ke sekarang)
                    logger.info(f"✅ VIP {user_id} auto-cut masa aktif (sudah lewat)")
                except Exception as e:
                    logger.error(f"Error auto-cut VIP {user_id}: {e}")
    except Exception as e:
        logger.error(f"Error mengambil data auto-cut: {e}")

def start_scheduler():
    # Jadwal Pagi (08:00)
    scheduler.add_job(send_reminder, CronTrigger(hour=8, minute=0), args=["pagi"])
    # Jadwal Siang (13:00)
    scheduler.add_job(send_reminder, CronTrigger(hour=13, minute=0), args=["siang"])
    # Jadwal Malam (20:00)
    scheduler.add_job(send_reminder, CronTrigger(hour=20, minute=0), args=["malam"])
    # Jadwal Auto-cut VIP (00:05 setiap hari - langsung setelah melewat malam)
    scheduler.add_job(auto_cut_vip_expired, CronTrigger(hour=0, minute=5), args=(), max_instances=1)

    scheduler.start()
    logger.info("✅ Scheduler Reminder (Pagi, Siang, Malam) dan Auto-cut VIP berhasil dijalankan")