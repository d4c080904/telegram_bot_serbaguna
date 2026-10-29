from bot_instance import bot
from keyboards.menus import buat_menu_utama, teks_menu_utama, buat_menu_gym_mode, teks_menu_gym_mode, tombol_kembali
from utils.decorators import rate_limited
from utils.state import set_onboarding_wizard, get_onboarding_wizard, clear_onboarding_wizard
from database.queries import get_user_profile, save_user_profile
from database.db import get_db
import logging

logger = logging.getLogger(__name__)

@bot.message_handler(commands=['start', 'help', 'menu'])
@rate_limited
def kirim_sambutan(pesan):
    try:
        user_id = str(pesan.from_user.id)
        user = get_user_profile(user_id)
        
        if not user:
            set_onboarding_wizard(user_id, 'nama')
            bot.reply_to(pesan, "Halo bro! 👋 Sebelum mulai, kenalin diri lu dulu ya.\n\nSiapa **nama panggilan** lu?", parse_mode='Markdown')
            return
            
        teks = f"Halo *{user['nama']}*! 👋\n\n" + teks_menu_utama()
        bot.reply_to(pesan, teks, parse_mode='Markdown', reply_markup=buat_menu_utama())
    except Exception as e:
        logger.error(f"[start] error: {e}")

def proses_onboarding(pesan):
    user_id = str(pesan.from_user.id)
    wizard = get_onboarding_wizard(user_id)
    step = wizard['step']
    data = wizard['data']
    teks = pesan.text.strip()
    
    if step == 'nama':
        data['nama'] = teks
        set_onboarding_wizard(user_id, 'umur', data)
        bot.reply_to(pesan, f"Oke *{teks}*! Umur lu berapa tahun? (Ketik angka aja)")
    elif step == 'umur':
        try:
            umur = int(teks)
            if umur < 10 or umur > 100:
                bot.reply_to(pesan, "Umur harus antara 10-100 ya.")
                return
            data['umur'] = umur
            set_onboarding_wizard(user_id, 'berat', data)
            bot.reply_to(pesan, "Berat badan lu berapa kg? (Contoh: 65.5)")
        except ValueError:
            bot.reply_to(pesan, "Tolong ketik angka aja ya.")
    elif step == 'berat':
        try:
            berat = float(teks.replace(',', '.'))
            data['berat'] = berat
            set_onboarding_wizard(user_id, 'tinggi', data)
            bot.reply_to(pesan, "Tinggi badan lu berapa cm? (Contoh: 170)")
        except ValueError:
            bot.reply_to(pesan, "Tolong ketik angka aja ya.")
    elif step == 'tinggi':
        try:
            tinggi = float(teks.replace(',', '.'))
            data['tinggi'] = tinggi
            set_onboarding_wizard(user_id, 'gender', data)
            bot.reply_to(pesan, "Jenis kelamin lu apa? Ketik **L** (Laki-laki) atau **P** (Perempuan).", parse_mode='Markdown')
        except ValueError:
            bot.reply_to(pesan, "Tolong ketik angka aja ya.")
    elif step == 'gender':
        gender = teks.upper()
        if gender not in ('L', 'P'):
            bot.reply_to(pesan, "Tolong ketik L atau P aja ya.")
            return
        data['jenis_kelamin'] = gender
        save_user_profile(user_id, data['nama'], data['umur'], data['berat'], data['tinggi'], data['jenis_kelamin'])
        clear_onboarding_wizard(user_id)
        bot.reply_to(pesan, f"✅ Mantap! Data lu udah disimpen.\n\nHalo *{data['nama']}*! 👋\n\n" + teks_menu_utama(), parse_mode='Markdown', reply_markup=buat_menu_utama())

@bot.callback_query_handler(func=lambda call: call.data == "menu_utama")
def callback_menu_utama(call):
    try:
        bot.answer_callback_query(call.id)
        user_id = str(call.from_user.id)
        user = get_user_profile(user_id)
        nama = user['nama'] if user else "Bro"
        
        teks = f"Halo *{nama}*! 👋\n\n" + teks_menu_utama()
        try: 
            bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=buat_menu_utama())
        except Exception: 
            bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=buat_menu_utama())
    except Exception as e:
        logger.error(f"[menu_utama] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_gym_mode")
def callback_menu_gym_mode(call):
    try:
        bot.answer_callback_query(call.id)
        try: 
            bot.edit_message_text(teks_menu_gym_mode(), call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=buat_menu_gym_mode())
        except Exception: 
            bot.send_message(call.message.chat.id, teks_menu_gym_mode(), parse_mode='Markdown', reply_markup=buat_menu_gym_mode())
    except Exception as e:
        logger.error(f"[menu_gym_mode] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_rapih")
def callback_menu_rapih(call):
    try:
        bot.answer_callback_query(call.id)
        teks = (
            "📝 *MODE PERAPIH TEKS*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Kirim teks berantakan / bahasa gaul, nanti gw ubah jadi bahasa Indonesia baku.\n\n"
            "*Contoh:*\n`gw lg males bgt nih mau ngerjain tugas`\n→ _Saya sedang sangat malas mengerjakan tugas._\n\n"
            "Gass kirim teksnya! 👇"
        )
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=tombol_kembali())
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_rapih] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_stats")
def callback_menu_stats(call):
    try:
        user_id = call.from_user.id
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM histori_chat WHERE user_id = ?", (str(user_id),))
        jumlah = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (str(user_id),))
        jumlah_chat = c.fetchone()[0]
        conn.close()

        bot.answer_callback_query(call.id)
        teks = f"📊 *STATISTIK LU*\n━━━━━━━━━━━━━━━━━━━━\n\n🔧 Pakai fitur: *{jumlah} kali*\n💬 Pesan chat AI: *{jumlah_chat} pesan*\n\n_Terus pakai bot ini biar angkanya naik!_ 🚀"
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=tombol_kembali())
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_stats] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_help")
def callback_menu_help(call):
    try:
        bot.answer_callback_query(call.id)
        teks = (
            "❓ *BANTUAN & PANDUAN*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "*📝 Perapih Teks*\n→ Kirim teks berantakan, dirapihin otomatis\n\n"
            "*💬 AI Chat*\n→ Ketik `/chat` atau pencet tombol di menu\n→ `/reset` hapus history\n→ `/exit` keluar dari chat\n\n"
            "*🏋️‍♂️ GYM MODE*\n→ Fitur lengkap Kalori, Air, Meal Planner, dll.\n\n"
            "*📥 Downloader*\n→ Paste link TikTok/IG/YouTube\n\n"
            "*⚙️ Command lain:*\n`/start` — menu utama\n`/menu` — buka menu lagi"
        )
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=tombol_kembali())
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_help] error: {e}")