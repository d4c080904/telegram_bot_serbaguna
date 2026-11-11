import logging
import hashlib
from aiogram import Router, F
from aiogram.types import Message
from database.queries import cek_id_makanan, is_chat_mode, get_wizard_state, tambah_food_log
from utils.state import get_gym_wizard, get_onboarding_wizard
from handlers.start import proses_onboarding
from handlers.calorie import proses_foto_makanan, tampil_dashboard_kalori
from handlers.pt_chat import proses_chat_pt
from services.meal_tracker import proses_koreksi_makanan_core
from services.ai import analisis_teks_makanan

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text)
async def respon_pesan(message: Message):
    try:
        teks_asli = message.text.strip()
        user_id = str(message.from_user.id)

        # 1. JIKA USER KIRIM COMMAND (/start, /gym, dll), ABAIKAN DI SINI
        if teks_asli.startswith('/'):
            return

        # 2. CEK ONBOARDING
        onboarding = await get_onboarding_wizard(user_id)
        if onboarding:
            await proses_onboarding(message, onboarding)
            return

        # 3. CEK GYM WIZARD
        wizard = await get_gym_wizard(user_id)
        if wizard:
            from handlers.gym import proses_gym_wizard
            await proses_gym_wizard(message, wizard)
            return

        # 4. CEK MODE CHAT PT AI
        if await is_chat_mode(user_id):
            await proses_chat_pt(message)
            return

        # 5. FITUR KOREKSI KALORI (Reply pesan)
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

        # 6. FITUR TEKS JADI MAKANAN
        # Cek kalau teksnya lebih dari 2 kata (kemungkinan besar ini catatan makanan, bukan "halo" atau "p")
        if len(teks_asli.split()) >= 3:
            await message.bot.send_chat_action(message.chat.id, 'typing')
            hasil_ai = await analisis_teks_makanan(teks_asli)
            
            if hasil_ai and hasil_ai.get("is_food"):
                pesan_tunggu = await message.reply("⏳ <i>Menganalisis makanan dari teks lu...</i>", parse_mode="HTML")
                
                # Bikin hash dari teks biar bot gak bisa di-spam teks yang sama persis hari ini
                text_hash = hashlib.md5(teks_asli.encode()).hexdigest()
                
                berhasil = await tambah_food_log(
                    user_id, 
                    pesan_tunggu.message_id, 
                    message.message_id, 
                    text_hash, 
                    hasil_ai.get('nama_makanan', 'Makanan'), 
                    hasil_ai.get('estimasi_porsi', '1 porsi'), 
                    hasil_ai.get('kalori', 0), 
                    hasil_ai.get('protein', 0), 
                    hasil_ai.get('karbo', 0), 
                    hasil_ai.get('lemak', 0), 
                    hasil_ai.get('gula', 0)
                )
                
                if berhasil:
                    gula_rapi = round(float(hasil_ai.get('gula', 0)), 1)
                    await pesan_tunggu.edit_text(
                        f"✅ <b>Berhasil Dicatat dari Teks!</b>\n\n"
                        f"🍽️ Nama: <b>{hasil_ai.get('nama_makanan')}</b>\n"
                        f"🍛 Porsi: <b>{hasil_ai.get('estimasi_porsi')}</b>\n"
                        f"🔥 Kalori: <b>{hasil_ai.get('kalori')} kcal</b>\n"
                        f"🍭 Gula: <b>{gula_rapi}g</b>\n\n"
                        f"<i>Tips: Lain kali pake fitur Foto atau Voice Note biar lebih akurat!</i>",
                        parse_mode="HTML"
                    )
                    await tampil_dashboard_kalori(message.chat.id, user_id, bot=message.bot)
                    return
                else:
                    await pesan_tunggu.edit_text("⚠️ Sepertinya lu udah nyatet makanan ini hari ini (terdeteksi duplikat).")
                    return

        # 7. TEKS SEMBARANG
        await message.answer(
            "🤖 <b>Gw sekarang fokus jadi GymBot bro!</b>\n\n"
            "Kalau lu mau nyatet makanan, lu bisa:\n"
            "1. Pake tombol <b>🍎 Kalori & Gula</b> (Foto)\n"
            "2. Kirim <b>Voice Note</b> (Rekam suara)\n"
            "3. Atau ketik langsung kayak: <i>\"Makan nasi padang 1 porsi\"</i>", 
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