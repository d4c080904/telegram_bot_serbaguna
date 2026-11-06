from bot_instance import bot
from telebot import types
from database.queries import (
    get_gym_profile, get_total_makro_hari_ini, get_history_makanan_hari_ini, 
    hapus_log_terakhir, save_wizard_state, delete_wizard_state
)
from utils.helpers import hitung_bmr_tdee
from services.meal_tracker import proses_foto_makanan_core
import logging
import datetime

logger = logging.getLogger(__name__)

HARI_INDONESIA = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
BULAN_INDONESIA = {'January': 'Januari', 'February': 'Februari', 'March': 'Maret', 'April': 'April', 'May': 'Mei', 'June': 'Juni', 'July': 'Juli', 'August': 'Agustus', 'September': 'September', 'October': 'Oktober', 'November': 'November', 'December': 'Desember'}
WIB_TZ = datetime.timezone(datetime.timedelta(hours=7))

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

    target = profil['target'] or 'recomp'
    batas_kalori = hitung_bmr_tdee(profil['umur'], profil['berat'], profil['tinggi'], profil['jenis_kelamin'] or 'L', target, profil['frekuensi'] or 3)
    
    batas_gula = 25 if target == 'cutting' else 50
    
    masuk_kalori, masuk_gula = get_total_makro_hari_ini(user_id)
    sisa_kalori = batas_kalori - masuk_kalori
    sisa_gula = batas_gula - masuk_gula
    
    now = datetime.datetime.now(WIB_TZ)
    hari_id = HARI_INDONESIA.get(now.strftime("%A"), now.strftime("%A"))
    bulan_id = BULAN_INDONESIA.get(now.strftime("%B"), now.strftime("%B"))
    waktu_str = f"{hari_id}, {now.day} {bulan_id} {now.year} | {now.strftime('%H:%M')} WIB"
    
    icon_gula = "✅" if sisa_gula >= 0 else "🚨"
    
    teks = (
        "🍎 *FOOD & SUGAR TRACKER*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *{waktu_str}*\n\n"
        f"*KALORI*\n"
        f"🎯 Batas: {batas_kalori} kcal\n"
        f"🍽️ Masuk: {masuk_kalori} kcal\n"
        f"🔥 Sisa: {sisa_kalori} kcal\n\n"
        f"*GULA (Target: {target.capitalize()})*\n"
        f"🎯 Batas: {batas_gula} g\n"
        f"🍭 Masuk: {masuk_gula} g\n"
        f"{icon_gula} Sisa: {sisa_gula} g\n\n"
        "Silakan pilih aksi di bawah:"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_foto = types.InlineKeyboardButton("📸 Foto Makanan", callback_data="kalori_foto")
    btn_hapus = types.InlineKeyboardButton("📝 Hapus Log Terakhir", callback_data="kalori_hapus")
    btn_history = types.InlineKeyboardButton("📊 Lihat History", callback_data="kalori_history")
    btn_kembali = types.InlineKeyboardButton("🔙 Kembali ke GYM MODE", callback_data="menu_gym_mode")
    
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
        save_wizard_state(str(call.from_user.id), "waiting_food_photo", "waiting", {})
        
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
        
        now = datetime.datetime.now(WIB_TZ)
        hari_id = HARI_INDONESIA.get(now.strftime("%A"), now.strftime("%A"))
        bulan_id = BULAN_INDONESIA.get(now.strftime("%B"), now.strftime("%B"))
        tanggal_str = f"{hari_id}, {now.day} {bulan_id} {now.year}"
        
        if not history:
            teks = f"📊 *HISTORY MAKANAN*\n📅 *{tanggal_str}*\n\nBelum ada makanan yang dicatat hari ini."
        else:
            teks = f"📊 *HISTORY MAKANAN*\n📅 *{tanggal_str}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for i, (nama, porsi, kal, gula, waktu_db) in enumerate(history, 1):
                try:
                    dt_utc = datetime.datetime.strptime(waktu_db, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
                    dt_wib = dt_utc.astimezone(WIB_TZ)
                    jam_str = dt_wib.strftime('%H:%M')
                except Exception:
                    jam_str = "--:--"
                teks += f"{i}. *{nama}* ({porsi})\n   └ {kal} kcal | 🍭 {gula}g Gula | 🕒 {jam_str} WIB\n"
        
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Kembali", callback_data="menu_kalori"))
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e: logger.error(f"kalori_history error: {e}")

def proses_foto_makanan(pesan):
    user_id = str(pesan.from_user.id)
    delete_wizard_state(user_id, "waiting_food_photo")
    
    bot.send_chat_action(pesan.chat.id, 'typing')
    pesan_tunggu = bot.reply_to(pesan, "⏳ _AI Ahli Gizi lagi menganalisis makanan & gulanya..._")
    
    try:
        file_info = bot.get_file(pesan.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        caption = pesan.caption or ""
        
        # Panggil Logic Bisnis (Service)
        result = proses_foto_makanan_core(
            user_id=user_id,
            image_bytes=downloaded_file,
            caption=caption,
            message_id=pesan_tunggu.message_id,
            photo_message_id=pesan.message_id
        )
        
        # Handle Hasil Response Service
        if result["status"] == "duplicate":
            bot.edit_message_text(
                "⚠️ *Foto Duplikat Terdeteksi!*\n\nFoto ini persis kayak yang udah lu kirim dan catat hari ini. Biar kalori lu nggak dobel, gw abaikan ya bro. 👍",
                pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown'
            )
            return
            
        if result["status"] == "ai_failed":
            bot.edit_message_text("❌ AI gagal menganalisis foto. Coba kirim ulang dengan foto yang lebih jelas.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        if result["status"] == "db_failed":
            bot.edit_message_text("❌ Gagal menyimpan data ke database.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        if result["status"] == "error":
            bot.edit_message_text("❌ Terjadi kesalahan sistem saat memproses foto.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        # JIKA SUKSES
        hasil = result["data"]
        teks_balasan = (
            f"✅ *Berhasil Dicatat!*\n\n"
            f"🍽️ Nama: *{hasil.get('nama_makanan')}*\n"
            f"🍛 Porsi: *{hasil.get('estimasi_porsi')}*\n"
            f"🔥 Kalori: *{hasil.get('kalori')} kcal*\n"
            f"🥩 Protein: *{hasil.get('protein')}g*\n"
            f"🍚 Karbo: *{hasil.get('karbo')}g*\n"
            f"🧈 Lemak: *{hasil.get('lemak')}g*\n"
            f"🍭 Gula: *{hasil.get('gula')}g*\n"
        )
        bot.edit_message_text(teks_balasan, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
        tampil_dashboard_kalori(pesan.chat.id, user_id)
        
    except Exception as e:
        logger.error(f"proses_foto_makanan error: {e}")
        bot.edit_message_text("❌ Terjadi kesalahan saat memproses foto.", pesan.chat.id, pesan_tunggu.message_id)