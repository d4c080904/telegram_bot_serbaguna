import re
import html as html_lib

def strip_markdown(text):
    if not text: return text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'__(.+?)__', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'```(.+?)```', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    return text

def buat_caption(judul, ikon="🎥", status="Sukses didownload!"):
    judul = html_lib.escape((judul or "Tanpa judul").strip()[:200])
    return f"{ikon} <b>{judul}</b>\n\n✅ <i>{html_lib.escape(status)}</i>"

def ambil_url_pertama(teks):
    hasil = re.findall(r'https?://[^\s]+', teks)
    return hasil[0] if hasil else None

def ambil_shortcode(url):
    m = re.search(r'instagram\.com/(?:[^/?#]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)', url)
    return m.group(1) if m else None

def hitung_bmi(berat, tinggi):
    try:
        tinggi_m = float(tinggi) / 100
        return round(float(berat) / (tinggi_m ** 2), 1)
    except Exception: return None

def kategori_bmi(bmi):
    if bmi is None: return "N/A"
    if bmi < 18.5: return "Kurus"
    elif bmi < 25: return "Normal"
    elif bmi < 30: return "Overweight"
    else: return "Obesitas"