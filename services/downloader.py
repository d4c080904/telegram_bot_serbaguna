import os
import re
import json
import shutil
import tempfile
import html as html_lib
import requests
import yt_dlp
from telebot.types import InputMediaPhoto, InputMediaVideo
from bot_instance import bot
from config import COOKIES_FILE, BATAS_UKURAN_VIDEO, BROWSER_HEADERS
from utils.helpers import buat_caption, ambil_shortcode
import logging

logger = logging.getLogger(__name__)
try:
    import instaloader; INSTALOADER_OK = True
except ImportError: INSTALOADER_OK = False

def unduh_file(url, path):
    with requests.get(url, headers=BROWSER_HEADERS, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)

def download_video_ytdlp(url_vid, file_name):
    ydl_opts = {
        'outtmpl': file_name, 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4', 'quiet': True, 'noplaylist': True, 'nocheckcertificate': True,
        'socket_timeout': 30, 'retries': 3, 'extractor_args': {'youtube': ['player_client=android']}
    }
    if os.path.exists(COOKIES_FILE): ydl_opts['cookiefile'] = COOKIES_FILE
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_vid, download=True)
        return (info.get('title') or 'Video') if info else 'Video'

def ambil_media_instaloader(shortcode):
    if not INSTALOADER_OK: return "", []
    L = instaloader.Instaloader(quiet=True, download_pictures=False, download_videos=False, download_video_thumbnails=False, download_geotags=False, download_comments=False, save_metadata=False, compress_json=False)
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    media = []
    if post.typename == 'GraphSidecar':
        for node in post.get_sidecar_nodes():
            if node.is_video: media.append(('video', node.video_url))
            else: media.append(('image', node.display_url))
    elif post.is_video: media.append(('video', post.video_url))
    else: media.append(('image', post.url))
    return (post.caption or ""), media

def ambil_media_embed(shortcode):
    r = requests.get(f"https://www.instagram.com/p/{shortcode}/embed/captioned/", headers=BROWSER_HEADERS, timeout=20)
    if r.status_code != 200: return "", []
    teks = r.text; urls = []
    m = re.search(r'<img[^>]*class="[^"]*EmbeddedMediaImage[^"]*"[^>]*src="([^"]+)"', teks)
    if m: urls.append(html_lib.unescape(m.group(1)))
    for m in re.finditer(r'"display_url"\s*:\s*"([^"]+)"', teks):
        try: u = json.loads('"' + m.group(1) + '"')
        except Exception: u = m.group(1).replace('\\u0026', '&').replace('\\/', '/')
        urls.append(u)
    unik, terlihat = [], set()
    for u in urls:
        kunci = u.split('?')[0]
        if kunci not in terlihat: terlihat.add(kunci); unik.append(u)
    return "", [('image', u) for u in unik]

def _kirim_satu(chat_id, tipe, path, caption):
    with open(path, 'rb') as f:
        if tipe == 'video': bot.send_video(chat_id, f, caption=caption, parse_mode='HTML', timeout=300)
        else: bot.send_photo(chat_id, f, caption=caption, parse_mode='HTML', timeout=120)

def kirim_kumpulan_media(chat_id, media, judul, ikon="🖼️", status="Sukses didownload!"):
    folder = tempfile.mkdtemp(prefix="dl_"); file_terbuka = []
    try:
        items = []
        for i, (tipe, url) in enumerate(media):
            ext = "mp4" if tipe == "video" else "jpg"
            path = os.path.join(folder, f"{i}.{ext}")
            try: unduh_file(url, path)
            except Exception as e: logger.warning(f"Gagal unduh media ke-{i}: {e}"); continue
            if tipe == "video" and os.path.getsize(path) > BATAS_UKURAN_VIDEO: continue
            items.append((tipe, path))
        if not items: raise Exception("Tidak ada media yang berhasil diunduh")
        caption = buat_caption(judul, ikon, status)
        for start in range(0, len(items), 10):
            potongan = items[start:start + 10]; cap_potongan = caption if start == 0 else None
            if len(potongan) == 1: _kirim_satu(chat_id, potongan[0][0], potongan[0][1], cap_potongan); continue
            grup = []
            for j, (tipe, path) in enumerate(potongan):
                f = open(path, 'rb'); file_terbuka.append(f)
                cap = cap_potongan if j == 0 else None; pm = 'HTML' if cap else None
                if tipe == 'video': grup.append(InputMediaVideo(f, caption=cap, parse_mode=pm))
                else: grup.append(InputMediaPhoto(f, caption=cap, parse_mode=pm))
            bot.send_media_group(chat_id, grup, timeout=300)
    finally:
        for f in file_terbuka:
            try: f.close()
            except Exception: pass
        shutil.rmtree(folder, ignore_errors=True)

def download_instagram_gambar(pesan, url_vid, pesan_tunggu):
    shortcode = ambil_shortcode(url_vid)
    if not shortcode: return False
    caption, media = "", []
    try: caption, media = ambil_media_instaloader(shortcode)
    except Exception as e: logger.warning(f"[instaloader] gagal: {e}")
    if not media:
        try: caption, media = ambil_media_embed(shortcode)
        except Exception as e: logger.warning(f"[embed] gagal: {e}")
    if not media: return False
    jumlah_gambar = sum(1 for t, _ in media if t == 'image'); jumlah_video = len(media) - jumlah_gambar
    if len(media) > 1: info_tipe = f"🖼️ Terdeteksi: *Carousel* ({jumlah_gambar} foto, {jumlah_video} video). Lagi didownload..."
    else: info_tipe = "🖼️ Terdeteksi: *Foto*. Lagi didownload..."
    try: bot.edit_message_text(info_tipe, pesan.chat.id, pesan_tunggu.message_id, parse_mode="Markdown")
    except Exception: pass
    bot.send_chat_action(pesan.chat.id, 'upload_photo')
    judul = caption.strip().split('\n')[0] if caption and caption.strip() else "Postingan Instagram"
    kirim_kumpulan_media(pesan.chat.id, media, judul, "🖼️", "Mendarat dengan selamat!")
    return True