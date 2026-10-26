import os
import tempfile
import logging
from bot_instance import bot, groq_client
from services.ai import transkripsi_audio, proses_voice_note, MODEL_GROQ_LIST
from database.queries import tambah_food_log, get_gym_profile, get_db
from handlers.calorie import tampil_dashboard_kalori
from utils.helpers import strip_markdown # TAMBAHAN IMPORT

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
        
        try: os.remove(temp_audio_path)
        except Exception: pass
            
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
        cr = hasil.get('chat_reply')
        
        # --- ROUTING AKSI ---
        
        if fd:
            berhasil = tambah_food_log(
                user_id, pesan_tunggu.message_id, pesan.message_id, "voice_hash", 
                fd.get('nama_makanan', 'Makanan'), fd.get('estimasi_porsi', '1 porsi'), 
                fd.get('kalori', 0), fd.get('protein', 0), fd.get('karbo', 0), 
                fd.get('lemak', 0), fd.get('gula', 0)
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
                
        elif gd:
            # --- UPDATE BARU: LANGSUNG EVALUASI PT AI ---
            bot.edit_message_text(f"💪 *Tercatat Latihan dari Suara:*\n_{gd}_\n\n⏳ _PT AI lagi ngecek data & mikir evaluasinya..._", pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
            
            profil = get_gym_profile(user_id)
            if not profil:
                bot.edit_message_text("⚠️ Lu belum punya profil Gym. Bikin dulu pakai `/gym daftar [BB] [TB] [Target]` ya.", pesan.chat.id, pesan_tunggu.message_id)
                return

            # Simpan ke log gym
            conn = get_db(); c = conn.cursor()
            c.execute("INSERT INTO gym_logs (user_id, log_teks) VALUES (?, ?)", (user_id, gd))
            conn.commit(); conn.close()
            
            mode = profil['mode']
            if mode == 'noob': 
                system_prompt = f"Kamu adalah asisten gym ramah untuk pemula. Klien: umur {profil['umur']}th, BB {profil['berat']}kg, TB {profil['tinggi']}cm. Evaluasi laporan latihan/makan dia dengan bahasa sederhana & motivasi. JANGAN pakai markdown (** atau * atau `). Tulis teks polos aja."
            else: 
                system_prompt = f"Kamu adalah personal trainer elite untuk klien berpengalaman. Klien: umur {profil['umur']}th, BB {profil['berat']}kg, TB {profil['tinggi']}cm, target {profil['target']}, level {profil['level']}, frekuensi {profil['frekuensi']}x/minggu, alat {profil['alat']}. Evaluasi laporan dia dengan detail teknis. JANGAN pakai markdown (** atau * atau `). Tulis teks polos aja."

            hasil_pt = None
            for model_name in MODEL_GROQ_LIST:
                try:
                    response = groq_client.chat.completions.create(
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": gd}],
                        model=model_name, temperature=0.7, max_tokens=1024
                    )
                    hasil_pt = response.choices[0].message.content.strip()
                    if hasil_pt: break
                except Exception: continue

            if hasil_pt:
                # --- PENGAMAN MARKDOWN ---
                # Coba kirim pakai markdown (biar bintang jadi tebal)
                try:
                    bot.edit_message_text(hasil_pt, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
                except Exception:
                    # Kalau AI bandel & formatnya rusak, hapus bintangnya
                    bot.edit_message_text(strip_markdown(hasil_pt), pesan.chat.id, pesan_tunggu.message_id)
            else:
                bot.edit_message_text("❌ AI lagi error nih bro.", pesan.chat.id, pesan_tunggu.message_id)
            
        elif cr:
            bot.edit_message_text(cr, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text("❓ Gw dengerin suara lu, tapi gw bingung itu makanan, olahraga, atau obrolan biasa. Coba ulangi ya bro.", pesan.chat.id, pesan_tunggu.message_id)
            
    except Exception as e:
        logger.error(f"Voice Handler Error: {e}")
        bot.edit_message_text("❌ Terjadi kesalahan saat memproses suara.", pesan.chat.id, pesan_tunggu.message_id)