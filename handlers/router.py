import logging
from aiogram import Router, F
from aiogram.types import Message
from database.queries import cek_id_makanan, is_chat_mode, get_wizard_state
from utils.state import get_gym_wizard, get_onboarding_wizard
from handlers.start import proses_onboarding
from handlers.calorie import proses_foto_makanan, tampil_dashboard_kalori
from handlers.pt_chat import proses_chat_pt
from services.meal_tracker import proses_koreksi_makanan_core

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text)
async def respon_pesan(message: Message):
    try:
        teks_asli = message.text.strip()
        user_id = str(message.from_user.id)

        # 1. CEK ONBOARDING
        onboarding = await get_onboarding_wizard(user_id)
        if onboarding:
            await proses_onboarding(message, onboarding)
            return

        # 2. CEK GYM WIZARD (Sekarang udah aman pakai aiogram)
        wizard = await get_gym_wizard(user_id)
        if wizard:
            from handlers.gym import proses_gym_wizard
            await proses_gym_wizard(message, wizard)
            return

        # 3. CEK MODE CHAT PT AI
        if await is_chat_mode(user_id) and not teks_asli.startswith('/'):
            await proses_chat_pt(message)
            return

        # 4. FITUR KOREKSI KALORI
        if message.reply_to_message:
            if await cek_id_makanan(user_id, message.reply_to_message.message_id):
                await message.bot.send_chat_action(message.chat.id, 'typing')
                pesan_tunggu = await message.reply("⏳ <i>Oke bro, AI lagi ngitung ulang kalorinya...</i>", parse_mode="HTML")
                
                result = await proses_koreksi_makanan_core(user_id, message.reply_to_message.message_id, teks_asli)
                
                if result["status"] == "ai_failed":
                    await pesan_tunggu.edit_text("❌ AI gagal memproses koreksi.")
                    return
                if result["status"] == "db_failed":
                    await pesan_tunggu.edit_text("❌ Gagal update database.")
                    return
                if result["status"] == "error":
                    await pesan_tunggu.edit_text("❌ Terjadi kesalahan sistem.")
                    return
                    
                hasil_baru = result["data"]
                await pesan_tunggu.edit_text(
                    f"✅ <b>Koreksi Berhasil!</b>\n\n🍽️ Nama Baru: <b>{hasil_baru.get('nama_makanan')}</b>\n🔥 Kalori Baru: <b>{hasil_baru.get('kalori')} kcal</b>\n🍭 Gula: <b>{hasil_baru.get('gula')}g</b>\n", 
                    parse_mode="HTML"
                )
                await tampil_dashboard_kalori(message.chat.id, user_id, bot=message.bot)
                return
            
            elif message.reply_to_message.from_user.id == message.bot.id:
                if "FOOD & SUGAR TRACKER" in (message.reply_to_message.text or "") or "KALORI TRACKER" in (message.reply_to_message.text or ""):
                    await message.reply("⚠️ <b>Pesan yang lu reply itu Dashboard, bukan detail makanannya.</b>\n\nBiar bisa dikoreksi, tolong reply pesan <b>Foto Makanan</b> atau <b>✅ Berhasil Dicatat!</b> ya.", parse_mode="HTML")
                    return

        # 5. JIKA USER KIRIM TEKS SEMBARANG
        if teks_asli.startswith('/'):
            return
            
        await message.answer(
            "🤖 <b>Gw sekarang fokus jadi GymBot bro!</b>\n\n"
            "Kalau lu mau nyatet makanan, pake tombol <b>🍎 Kalori & Gula</b> di menu.\n"
            "Kalau mau nyatet latihan, ketik /gym [laporan latihan lu].\n\n"
            "Ketik /start buat buka menu ya! 💪", 
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"[respon_pesan] fatal error: {e}")
        try: await message.answer("❌ Ada error. Coba lagi ya bro.")
        except Exception: pass

@router.message(F.photo)
async def handle_photo(message: Message):
    user_id = str(message.from_user.id)
    
    if await get_wizard_state(user_id, "waiting_food_photo"):
        await proses_foto_makanan(message)
    elif await get_wizard_state(user_id, "waiting_equipment_photo"):
        from handlers.equipment import proses_foto_alat
        await proses_foto_alat(message)
    else:
        await message.reply("📸 Foto diterima. Kalau mau scan kalori, masuk ke menu 🍎 <b>Kalori & Gula</b>.", parse_mode="HTML")