import os
import tempfile
import logging
import hashlib
from bot_instance import bot
from services.ai import transkripsi_audio, proses_voice_note
from database.queries import tambah_food_log
from handlers.calorie import tampil_dashboard_kalori
from utils.helpers import strip_markdown

logger = logging.getLogger(__name__)

@bot.message_handler(content_types=['voice'])
def handle_voice(pesan):
    user_id = str(pesan.from_user.id)
    
    bot.send_chat_action(pesan.chat.id, 'typing')
    pesan_tunggu = bot.reply_to(pesan, "🎙️ _Lagi dengerin voice note lu..._")
    
    try:
        file_info = bot.get_file(pesan.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(downloaded_file)
            temp_audio_path = temp_audio.name
            
        teks_transkrip = transkripsi_audio(temp_audio_path)
        
        try:
            os.remove(temp_audio_path)
        except Exception:
            pass
            
        if not teks_transkrip:
            bot.edit_message_text("❌ Gagal transkrip suara. Coba bicara lebih jelas ya.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        bot.edit_message_text(f"🎙️ *Lu bilang:*\n_{teks_transkrip}_\n\n⏳ _AI lagi mikir..._", pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
        
        hasil = proses_voice_note(teks_transkrip)
        
        if not hasil:
            bot.edit_message_text("❌ AI gagal memahami perintah suara.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        fd = hasil.get('food_data')
        gd = hasil.get('gym_data')
        
        # KALAU LAGI NYATET MAKANAN
        if fd:
            berhasil = tambah_food_log(
                user_id, 
                pesan_tunggu.message_id, 
                pesan.message_id, 
                hashlib.md5(downloaded_file).hexdigest(),
                fd.get('nama_makanan', 'Makanan'), 
                fd.get('estimasi_porsi', '1 porsi'), 
                fd.get('kalori', 0), 
                fd.get('protein', 0), 
                fd.get('karbo', 0), 
                fd.get('lemak', 0), 
                fd.get('gula', 0)
            )
            if berhasil:
                bot.edit_message_text(
                    f"✅ *Berhasil Dicatat dari Suara!*\n\n"
                    f"🍽️ Nama: *{fd.get('nama_makanan')}*\n"
                    f"🍛 Porsi: *{fd.get('estimasi_porsi')}*\n"
                    f"🔥 Kalori: *{fd.get('kalori')} kcal*\n"
                    f"🍭 Gula: *{fd.get('gula')}g*\n",
                    pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown'
                )
                tampil_dashboard_kalori(pesan.chat.id, user_id)
            else:
                bot.edit_message_text("❌ Gagal simpan data makanan ke database.", pesan.chat.id, pesan_tunggu.message_id)
                
        # KALAU LAGI NYATET GYM
        elif gd:
            bot.edit_message_text(f"💪 *Tercatat Latihan dari Suara:*\n_{gd}_\n\n⏳ _PT AI lagi ngecek data & mikir evaluasinya..._", pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
            
            from database.queries import get_gym_profile, get_db
            from services.ai import analisis_gym_noob, analisis_gym_pro
            
            profil = get_gym_profile(user_id)
            if not profil:
                bot.edit_message_text("⚠️ Lu belum punya profil Gym. Bikin dulu pakai `/gym` ya.", pesan.chat.id, pesan_tunggu.message_id)
                return

            conn = get_db(); c = conn.cursor()
            c.execute("INSERT INTO gym_logs (user_id, log_teks) VALUES (?, ?)", (user_id, gd))
            conn.commit(); conn.close()
            
            if profil['mode'] == 'noob':
                hasil_pt = analisis_gym_noob(profil['umur'], profil['berat'], profil['tinggi'])
            else:
                hasil_pt = analisis_gym_pro(profil)

            if hasil_pt:
                try:
                    bot.edit_message_text(hasil_pt, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
                except Exception:
                    bot.edit_message_text(strip_markdown(hasil_pt), pesan.chat.id, pesan_tunggu.message_id)
            else:
                bot.edit_message_text("❌ AI lagi error nih bro.", pesan.chat.id, pesan_tunggu.message_id)
            
        # KALAU CUMA NGOBROL (FITUR CHAT UDAH DIHAPUS)
        else:
            bot.edit_message_text("❓ Gw dengerin suara lu, tapi gw bingung itu makanan atau olahraga. Coba ulangi ya bro.", pesan.chat.id, pesan_tunggu.message_id)
            
    except Exception as e:
        logger.error(f"Voice Handler Error: {e}")
        bot.edit_message_text("❌ Terjadi kesalahan saat memproses suara.", pesan.chat.id, pesan_tunggu.message_id)