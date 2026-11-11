import logging
import os
import tempfile
import hashlib
from aiogram import Router, F
from aiogram.types import Message

from services.ai import transkripsi_audio, proses_voice_note, analisis_gym_noob, analisis_gym_pro
from database.queries import tambah_food_log, get_gym_profile
from database.db import get_db
from utils.helpers import strip_markdown
from handlers.calorie import tampil_dashboard_kalori

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.voice)
async def handle_voice(message: Message):
    user_id = str(message.from_user.id)
    await message.bot.send_chat_action(message.chat.id, 'record_voice')
    
    pesan_tunggu = await message.reply("🎙️ <i>Lagi dengerin voice note lu...</i>", parse_mode="HTML")
    
    try:
        # 1. Download file VN
        file_id = message.voice.file_id
        file_info = await message.bot.get_file(file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        
        # 2. Simpan ke temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(downloaded_file.read())
            temp_audio_path = temp_audio.name
            
        # 3. Transkrip
        teks_transkrip = await transkripsi_audio(temp_audio_path)
        
        # Hapus temp file
        try:
            os.remove(temp_audio_path)
        except Exception:
            pass
            
        if not teks_transkrip:
            await pesan_tunggu.edit_text("❌ Gagal transkrip suara. Coba bicara lebih jelas ya.")
            return
            
        await pesan_tunggu.edit_text(f"🎙️ <b>Lu bilang:</b>\n<i>{teks_transkrip}</i>\n\n⏳ <i>AI lagi mikir...</i>", parse_mode="HTML")
        
        # 4. Proses Teks
        hasil = await proses_voice_note(teks_transkrip)
        
        if not hasil:
            await pesan_tunggu.edit_text("❌ AI gagal memahami perintah suara.")
            return
            
        fd = hasil.get('food_data')
        gd = hasil.get('gym_data')
        
        # KALAU LAGI NYATET MAKANAN
        if fd:
            berhasil = await tambah_food_log(
                user_id, 
                pesan_tunggu.message_id, 
                message.message_id, 
                hashlib.md5(downloaded_file.read()).hexdigest(),
                fd.get('nama_makanan', 'Makanan'), 
                fd.get('estimasi_porsi', '1 porsi'), 
                fd.get('kalori', 0), 
                fd.get('protein', 0), 
                fd.get('karbo', 0), 
                fd.get('lemak', 0), 
                fd.get('gula', 0)
            )
            if berhasil:
                await pesan_tunggu.edit_text(
                    f"✅ <b>Berhasil Dicatat dari Suara!</b>\n\n"
                    f"🍽️ Nama: <b>{fd.get('nama_makanan')}</b>\n"
                    f"🍛 Porsi: <b>{fd.get('estimasi_porsi')}</b>\n"
                    f"🔥 Kalori: <b>{fd.get('kalori')} kcal</b>\n"
                    f"🍭 Gula: <b>{fd.get('gula')}g</b>\n",
                    parse_mode="HTML"
                )
                await tampil_dashboard_kalori(message.chat.id, user_id, bot=message.bot)
            else:
                await pesan_tunggu.edit_text("❌ Gagal simpan data makanan ke database.")
                
        # KALAU LAGI NYATET GYM
        elif gd:
            await pesan_tunggu.edit_text(f"💪 <b>Tercatat Latihan dari Suara:</b>\n<i>{gd}</i>\n\n⏳ <i>PT AI lagi ngecek data & mikir evaluasinya...</i>", parse_mode="HTML")
            
            profil = await get_gym_profile(user_id)
            if not profil:
                await pesan_tunggu.edit_text("⚠️ Lu belum punya profil Gym. Bikin dulu pakai /gym ya.")
                return

            async with await get_db() as conn:
                await conn.execute("INSERT INTO gym_logs (user_id, log_teks) VALUES ($1, $2)", user_id, gd)
            
            if profil['mode'] == 'noob':
                hasil_pt = await analisis_gym_noob(profil['umur'], profil['berat'], profil['tinggi'])
            else:
                hasil_pt = await analisis_gym_pro(profil)

            if hasil_pt:
                try:
                    await pesan_tunggu.edit_text(hasil_pt, parse_mode="HTML")
                except Exception:
                    await pesan_tunggu.edit_text(strip_markdown(hasil_pt))
            else:
                await pesan_tunggu.edit_text("❌ AI lagi error nih bro.")
            
        # KALAU CUMA NGOBROL
        else:
            await pesan_tunggu.edit_text("❓ Gw dengerin suara lu, tapi gw bingung itu makanan atau olahraga. Coba ulangi ya bro.")
            
    except Exception as e:
        logger.error(f"Voice Handler Error: {e}")
        await pesan_tunggu.edit_text("❌ Terjadi kesalahan saat memproses suara.")