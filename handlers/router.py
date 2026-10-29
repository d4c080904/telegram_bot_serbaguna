import os
import glob
import requests
import logging
from bot_instance import bot
from config import BROWSER_HEADERS, BATAS_UKURAN_VIDEO
from database.queries import simpan_ke_db, is_chat_mode, update_food_log, cek_id_makanan
from services.ai import perbaiki_teks_dengan_ai, koreksi_foto_makanan
from services.downloader import download_video_ytdlp, download_instagram_gambar, kirim_kumpulan_media, ambil_shortcode, unduh_file
from utils.helpers import ambil_url_pertama, buat_caption, strip_markdown
from utils.decorators import rate_limited
from utils.state import get_gym_wizard, get_onboarding_wizard
from handlers.chat import proses_chat
from handlers.gym import proses_gym_wizard
from handlers.start import proses_onboarding
from handlers.calorie import _waiting_food_photo, proses_foto_makanan, tampil_dashboard_kalori
from telebot import types

logger = logging.getLogger(__name__)

@bot.message_handler(content_types=["text"])
@rate_limited
def respon_pesan(pesan):
    try:
        teks_asli = pesan.text.strip()
        user_id = pesan.from_user.id

        # 1. CEK ONBOARDING DULU
        onboarding = get_onboarding_wizard(user_id)
        if onboarding:
            proses_onboarding(pesan)
            return

        # 2. CEK GYM WIZARD
        wizard = get_gym_wizard(user_id)
        if wizard:
            proses_gym_wizard(pesan, wizard)
            return

        # 3. FITUR KOREKSI KALORI
        if pesan.reply_to_message:
            if cek_id_makanan(user_id, pesan.reply_to_message.message_id):
                bot.send_chat_action(pesan.chat.id, 'typing')
                pesan_tunggu = bot.reply_to(pesan, "⏳ _Oke bro, AI lagi ngitung ulang kalorinya..._")
                hasil_baru = koreksi_foto_makanan(teks_asli)
                if hasil_baru:
                    berhasil = update_food_log(
                        user_id, pesan.reply_to_message.message_id,
                        hasil_baru.get('nama_makanan', 'Makanan'), hasil_baru.get('estimasi_porsi', '1 porsi'), 
                        hasil_baru.get('kalori', 0), hasil_baru.get('protein', 0), 
                        hasil_baru.get('karbo', 0), hasil_baru.get('lemak', 0), hasil_baru.get('gula', 0)
                    )
                    if berhasil:
                        bot.edit_message_text(f"✅ *Koreksi Berhasil!*\n\n🍽️ Nama Baru: *{hasil_baru.get('nama_makanan')}*\n🔥 Kalori Baru: *{hasil_baru.get('kalori')} kcal*\n🍭 Gula: *{hasil_baru.get('gula')}g*\n", pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
                        tampil_dashboard_kalori(pesan.chat.id, user_id)
                        return
                    else:
                        bot.edit_message_text("❌ Gagal update database. Pastikan lu reply pesan *✅ Berhasil Dicatat!* atau *Foto Makanan* ya.", pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
                        return
                else:
                    bot.edit_message_text("❌ AI gagal memproses koreksi.", pesan.chat.id, pesan_tunggu.message_id)
                    return
            
            elif pesan.reply_to_message.from_user.id == bot.get_me().id:
                if "FOOD & SUGAR TRACKER" in (pesan.reply_to_message.text or "") or "KALORI TRACKER" in (pesan.reply_to_message.text or ""):
                    bot.reply_to(pesan, "⚠️ *Pesan yang lu reply itu Dashboard, bukan detail makanannya.*\n\nBiar bisa dikoreksi, tolong reply pesan *Foto Makanan* lu, atau reply pesan *✅ Berhasil Dicatat!* dari bot.", parse_mode='Markdown')
                    return

        ada_link = ("tiktok.com" in teks_asli.lower() or "instagram.com" in teks_asli.lower() or "youtu" in teks_asli.lower())

        if is_chat_mode(user_id) and not ada_link:
            proses_chat(pesan)
            return

        # 4. DOWNLOADER & TEKS BIASA
        if "tiktok.com" in teks_asli.lower():
            bot.send_chat_action(pesan.chat.id, 'upload_video')
            pesan_tunggu = bot.reply_to(pesan, "⏳ _Sedot video TikTok dulu bos, bentar yak..._", parse_mode="Markdown")
            try:
                url_tiktok = ambil_url_pertama(teks_asli)
                api_url = f"https://www.tikwm.com/api/?url={url_tiktok}"
                response = requests.get(api_url, timeout=30).json()
                if response.get("code") == 0:
                    data = response["data"]
                    judul = data.get("title") or "Video TikTok"
                    gambar_list = data.get("images") or []
                    if gambar_list:
                        media = [('image', u) for u in gambar_list]
                        kirim_kumpulan_media(pesan.chat.id, media, judul, "🖼️", "Sukses didownload!")
                        simpan_ke_db(user_id, pesan.from_user.username, teks_asli, "Download Foto TikTok")
                    else:
                        video_url = data["play"]
                        video_bytes = requests.get(video_url, timeout=120).content
                        bot.send_video(pesan.chat.id, video_bytes, caption=buat_caption(judul, "🎥", "Sukses didownload!"), parse_mode="HTML", timeout=120)
                        simpan_ke_db(user_id, pesan.from_user.username, teks_asli, "Download Video TikTok")
                else:
                    bot.reply_to(pesan, "❌ Gagal ngambil TikTok.")
            except Exception as e:
                logger.error(f"[TikTok] error: {e}")
                try: bot.reply_to(pesan, "❌ Gagal ngambil TikTok.")
                except Exception: pass
            finally:
                try: bot.delete_message(pesan.chat.id, pesan_tunggu.message_id)
                except Exception: pass

        elif "instagram.com" in teks_asli.lower() or "youtu" in teks_asli.lower():
            bot.send_chat_action(pesan.chat.id, 'upload_video')
            pesan_tunggu = bot.reply_to(pesan, "⏳ _Tunggu bentar, narik video IG/YT..._", parse_mode="Markdown")
            file_name = f"video_{pesan.chat.id}_{pesan.message_id}.mp4"
            try:
                url_vid = ambil_url_pertama(teks_asli)
                adalah_ig = "instagram.com" in url_vid.lower()
                berhasil = False
                tipe_db = "Download Video IG/YT"
                judul = None
                try: judul = download_video_ytdlp(url_vid, file_name)
                except Exception as e: logger.warning(f"[yt-dlp] gagal / bukan video: {e}")

                if judul is not None and os.path.exists(file_name):
                    if os.path.getsize(file_name) > BATAS_UKURAN_VIDEO:
                        bot.reply_to(pesan, "❌ Videonya kegedean (limit upload bot Telegram 50 MB).")
                    else:
                        with open(file_name, 'rb') as video_file:
                            bot.send_video(pesan.chat.id, video_file, caption=buat_caption(judul, "🎥", "Mendarat dengan selamat!"), parse_mode="HTML", timeout=300)
                        berhasil = True
                elif adalah_ig:
                    try: bot.edit_message_text("⏳ _Bukan video, ngecek apakah ini foto/carousel..._", pesan.chat.id, pesan_tunggu.message_id, parse_mode="Markdown")
                    except Exception: pass
                    ok = download_instagram_gambar(pesan, url_vid, pesan_tunggu)
                    if ok:
                        berhasil = True
                        tipe_db = "Download Gambar IG"
                    else:
                        bot.reply_to(pesan, "❌ Gagal ambil postingan IG. Kemungkinan akunnya private, link salah, atau IG nge-blok bot.")
                else:
                    bot.reply_to(pesan, "❌ Gagal sedot video.")
                if berhasil:
                    simpan_ke_db(user_id, pesan.from_user.username, teks_asli, tipe_db)
            except Exception as e:
                logger.error(f"[IG/YT] error: {e}")
                try: bot.reply_to(pesan, "❌ Gagal sedot video.")
                except Exception: pass
            finally:
                try: bot.delete_message(pesan.chat.id, pesan_tunggu.message_id)
                except Exception: pass
                for sisa in glob.glob(f"video_{pesan.chat.id}_{pesan.message_id}*"):
                    try: os.remove(sisa)
                    except Exception: pass

        else:
            bot.send_chat_action(pesan.chat.id, 'typing')
            teks_rapi = perbaiki_teks_dengan_ai(teks_asli)
            if not teks_rapi: return
            simpan_ke_db(user_id, pesan.from_user.username, teks_asli, teks_rapi)
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🇬🇧 Terjemahkan ke Inggris", callback_data="terjemahkan"))
            try: bot.reply_to(pesan, teks_rapi, reply_markup=markup)
            except Exception: bot.reply_to(pesan, strip_markdown(teks_rapi), reply_markup=markup)

    except Exception as e:
        logger.error(f"[respon_pesan] fatal error: {e}")
        try: bot.reply_to(pesan, "❌ Ada error. Coba lagi ya bro.")
        except Exception: pass

@bot.message_handler(content_types=['photo'])
def handle_photo(pesan):
    user_id = str(pesan.from_user.id)
    if user_id in _waiting_food_photo:
        proses_foto_makanan(pesan)
    else:
        bot.reply_to(pesan, "📸 Foto diterima. Kalau mau scan kalori, masuk ke menu 🍎 *Kalori & Gula* dulu ya.", parse_mode='Markdown')