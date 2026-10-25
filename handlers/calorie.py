from bot_instance import bot
from telebot import types
from database.queries import get_gym_profile, get_total_kalori_hari_ini, get_history_makanan_hari_ini, hapus_log_terakhir
from utils.helpers import hitung_bmr_tdee
from utils.decorators import rate_limited
from keyboards.menus import tombol_kembali
import logging
import datetime

logger = logging.getLogger(__name__)

# Kamus Bahasa Indonesia
HARI_INDONESIA = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
BULAN_INDONESIA = {'January': 'Januari', 'February': 'Februari', 'March': 'Maret', 'April': 'April', 'May': 'Mei', 'June': 'Juni', 'July': 'Juli', 'August': 'Agustus', 'September': 'September', 'October': 'Oktober', 'November': 'November', 'December': 'Desember'}

# Set Timezone WIB (UTC+7)
WIB_TZ = datetime.timezone(datetime.timedelta(hours=7))

_waiting_food_photo = set()

def tampil_dashboard_kalori(chat_id, user_id, message_id=None):
    profil = get_gym_profile(user_id)
    
    if not profil or not profil['berat'] or not profil['tinggi']:
        teks = "⚠️ *Lu belum lengkap ngisi profil Gym!*\n\nBiar AI bisa ngitung kalori harian lu, isi dulu profil Gym lu ya."
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💪 Ke Menu Gym", callback_data="menu_gym"))
        try:
            if message_id: bot.edit_message_text(teks, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
            else: bot.send_message(chat_id, teks, parse_mode='Markdown', reply_markup=markup)
        except Exception: pass
        return

    batas = hitung_bmr_tdee(profil['umur'], profil['berat'], profil['tinggi'], profil['jenis_kelamin'] or 'L', profil['target'] or 'recomp', profil['frekuensi'] or 3)
    masuk = get_total_kalori_hari_ini(user_id)
    sisa = batas - masuk
    
    # Ambil Waktu Real-Time (WIB)
    now = datetime.datetime.now(WIB_TZ)
    hari_id = HARI_INDONESIA.get(now.strftime("%A"), now.strftime("%A"))
    bulan_id = BULAN_INDONESIA.get(now.strftime("%B"), now.strftime("%B"))
    waktu_str = f"{hari_id}, {now.day} {bulan_id} {now.year} | {now.strftime('%H:%M')} WIB"
    
    teks = (
        "🍎 *KALORI TRACKER*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *{waktu_str}*\n\n"
        f"🎯 Batas Harian: *{batas} kcal*\n"
        f"🍽️ Sudah Masuk: *{masuk} kcal*\n"
        f"🔥 Sisa Kalori: *{sisa} kcal*\n\n"
        "Silakan pilih aksi di bawah:"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_foto = types.InlineKeyboardButton("📸 Foto Makanan", callback_data="kalori_foto")
    btn_hapus = types.InlineKeyboardButton("📝 Hapus Log Terakhir", callback_data="kalori_hapus")
    btn_history = types.InlineKeyboardButton("📊 Lihat History", callback_data="kalori_history")
    btn_kembali = types.InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="menu_utama")
    markup.add(btn_foto)
    markup.add(btn_hapus, btn_history)
    markup.add(btn_kembali)
    
    try:
        if message_id: bot.edit_message_text(teks, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
        else: bot.send_message(chat_id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"tampil_dashboard_kalori error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_kalori")
def callback_menu_kalori(call):
    try:
        bot.answer_callback_query(call.id)
        tampil_dashboard_kalori(call.message.chat.id, call.from_user.id, call.message.message_id)
    except Exception as e: logger.error(f"menu_kalori error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "kalori_foto")
def callback_kalori_foto(call):
    try:
        bot.answer_callback_query(call.id)
        _waiting_food_photo.add(str(call.from_user.id))
        teks = "📸 *Silakan kirim foto makanan lu sekarang.*\n\n_(Boleh tambahkan caption nama makanannya biar AI makin akurat)_"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Batal", callback_data="menu_kalori"))
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e: logger.error(f"kalori_foto error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "kalori_hapus")
def callback_kalori_hapus(call):
    try:
        bot.answer_callback_query(call.id)
        if hapus_log_terakhir(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ Log terakhir berhasil dihapus!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "⚠️ Tidak ada log makanan hari ini.", show_alert=True)
        tampil_dashboard_kalori(call.message.chat.id, call.from_user.id, call.message.message_id)
    except Exception as e: logger.error(f"kalori_hapus error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "kalori_history")
def callback_kalori_history(call):
    try:
        bot.answer_callback_query(call.id)
        history = get_history_makanan_hari_ini(call.from_user.id)
        
        # Ambil Waktu Real-Time (WIB)
        now = datetime.datetime.now(WIB_TZ)
        hari_id = HARI_INDONESIA.get(now.strftime("%A"), now.strftime("%A"))
        bulan_id = BULAN_INDONESIA.get(now.strftime("%B"), now.strftime("%B"))
        tanggal_str = f"{hari_id}, {now.day} {bulan_id} {now.year}"
        
        if not history:
            teks = f"📊 *HISTORY MAKANAN*\n📅 *{tanggal_str}*\n\nBelum ada makanan yang dicatat hari ini."
        else:
            teks = f"📊 *HISTORY MAKANAN*\n📅 *{tanggal_str}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for i, (nama, porsi, kal, waktu_db) in enumerate(history, 1):
                # Waktu dari SQLite formatnya UTC, kita ubah ke WIB
                try:
                    dt_utc = datetime.datetime.strptime(waktu_db, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
                    dt_wib = dt_utc.astimezone(WIB_TZ)
                    jam_str = dt_wib.strftime('%H:%M')
                except Exception:
                    jam_str = "--:--"
                teks += f"{i}. *{nama}* ({porsi})\n   └ {kal} kcal | 🕒 {jam_str} WIB\n"
        
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Kembali", callback_data="menu_kalori"))
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e: logger.error(f"kalori_history error: {e}")

def proses_foto_makanan(pesan):
    user_id = str(pesan.from_user.id)
    _waiting_food_photo.discard(user_id)
    
    bot.send_chat_action(pesan.chat.id, 'typing')
    pesan_tunggu = bot.reply_to(pesan, "⏳ _AI Ahli Gizi lagi menganalisis makanan lu..._")
    
    try:
        file_info = bot.get_file(pesan.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        caption = pesan.caption or ""
        
        from services.ai import analisis_foto_makanan
        hasil = analisis_foto_makanan(downloaded_file, caption)
        
        if not hasil:
            bot.edit_message_text("❌ AI gagal menganalisis foto. Coba kirim ulang dengan foto yang lebih jelas.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        from database.queries import tambah_food_log
        berhasil = tambah_food_log(
            user_id, 
            pesan_tunggu.message_id, 
            pesan.message_id, 
            hasil.get('nama_makanan', 'Makanan'), 
            hasil.get('estimasi_porsi', '1 porsi'), 
            hasil.get('kalori', 0), 
            hasil.get('protein', 0), 
            hasil.get('karbo', 0), 
            hasil.get('lemak', 0)
        )
        
        if not berhasil:
            bot.edit_message_text("❌ Gagal menyimpan data ke database.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        teks_balasan = (
            f"✅ *Berhasil Dicatat!*\n\n"
            f"🍽️ Nama: *{hasil.get('nama_makanan')}*\n"
            f"🍛 Porsi: *{hasil.get('estimasi_porsi')}*\n"
            f"🔥 Kalori: *{hasil.get('kalori')} kcal*\n"
            f"🥩 Protein: *{hasil.get('protein')}g*\n"
            f"🍚 Karbo: *{hasil.get('karbo')}g*\n"
            f"🧈 Lemak: *{hasil.get('lemak')}g*\n"
        )
        bot.edit_message_text(teks_balasan, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
        tampil_dashboard_kalori(pesan.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"proses_foto_makanan error: {e}")
        bot.edit_message_text("❌ Terjadi kesalahan saat memproses foto.", pesan.chat.id, pesan_tunggu.message_id)