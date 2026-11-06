from bot_instance import bot
from keyboards.menus import (
    buat_menu_utama, teks_menu_utama, 
    tombol_kembali, buat_tombol_gender
)
from utils.decorators import rate_limited
from utils.state import set_onboarding_wizard, get_onboarding_wizard, clear_onboarding_wizard
from database.queries import get_user_profile, save_user_profile, get_total_air_hari_ini, get_berat_terakhir, set_chat_mode
from database.db import get_db
import logging

logger = logging.getLogger(__name__)

def buat_ringkasan_dashboard(user_id):
    air = get_total_air_hari_ini(user_id)
    target_air = 2000
    persen = min((air / target_air) * 100, 100)
    
    bar_length = 10
    filled = int(bar_length * persen / 100)
    bar = "🟦" * filled + "⬜" * (bar_length - filled)
    
    berat_data = get_berat_terakhir(user_id)
    berat_str = f"{berat_data[0][0]} kg" if berat_data else "Belum diisi"
    
    return (
        "📊 *RINGKASAN HARI INI:*\n"
        f"💧 Air: {bar} {int(persen)}% ({air}/{target_air} ml)\n"
        f"⚖️ Berat: {berat_str}\n"
    )

@bot.message_handler(commands=['start', 'help', 'menu'])
@rate_limited
def kirim_sambutan(pesan):
    try:
        user_id = str(pesan.from_user.id)
        set_chat_mode(user_id, False) # Matiin mode Chat PT kalau user ngetik /start
        
        user = get_user_profile(user_id)
        
        if not user:
            set_onboarding_wizard(user_id, 'nama')
            bot.reply_to(pesan, "Halo bro! 👋 Sebelum mulai, kenalin diri lu dulu ya.\n\nSiapa **nama panggilan** lu?", parse_mode='Markdown')
            return
            
        ringkasan = buat_ringkasan_dashboard(user_id)
        teks = f"Halo *{user['nama']}*! 👋\n\n" + teks_menu_utama(ringkasan)
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
            bot.reply_to(pesan, "Terakhir nih, jenis kelamin lu apa? Pencet tombol di bawah ya 👇", reply_markup=buat_tombol_gender())
        except ValueError:
            bot.reply_to(pesan, "Tolong ketik angka aja ya.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("onboard_gender_"))
def callback_gender(call):
    try:
        bot.answer_callback_query(call.id)
        user_id = str(call.from_user.id)
        wizard = get_onboarding_wizard(user_id)
        
        if not wizard or wizard['step'] != 'gender':
            bot.send_message(call.message.chat.id, "Sesi onboarding lu udah berakhir. Ketik /start lagi ya.")
            return
            
        data = wizard['data']
        gender = "L" if call.data == "onboard_gender_L" else "P"
        
        save_user_profile(user_id, data['nama'], data['umur'], data['berat'], data['tinggi'], gender)
        clear_onboarding_wizard(user_id)
        
        ringkasan = buat_ringkasan_dashboard(user_id)
        teks = f"✅ Mantap! Data lu udah disimpen.\n\nHalo *{data['nama']}*! 👋\n\n" + teks_menu_utama(ringkasan)
        
        try:
            bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=buat_menu_utama())
        except Exception:
            bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=buat_menu_utama())
            
    except Exception as e:
        logger.error(f"[callback_gender] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_utama")
def callback_menu_utama(call):
    try:
        bot.answer_callback_query(call.id)
        user_id = str(call.from_user.id)
        set_chat_mode(user_id, False) # Matiin mode Chat PT kalau user pencet Menu Utama
        
        user = get_user_profile(user_id)
        nama = user['nama'] if user else "Bro"
        
        ringkasan = buat_ringkasan_dashboard(user_id)
        teks = f"Halo *{nama}*! 👋\n\n" + teks_menu_utama(ringkasan)
        
        try: 
            bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=buat_menu_utama())
        except Exception: 
            bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=buat_menu_utama())
    except Exception as e:
        logger.error(f"[menu_utama] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_stats")
def callback_menu_stats(call):
    try:
        user_id = call.from_user.id
        conn = get_db(); c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM food_logs WHERE user_id = ?", (str(user_id),))
        jumlah_makan = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM water_logs WHERE user_id = ?", (str(user_id),))
        jumlah_air = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM gym_logs WHERE user_id = ?", (str(user_id),))
        jumlah_gym = c.fetchone()[0]
        
        conn.close()

        bot.answer_callback_query(call.id)
        teks = (
            "📊 *STATISTIK GYM LU*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🍎 Log Makanan: *{jumlah_makan} kali*\n"
            f"💧 Log Air Minum: *{jumlah_air} kali*\n"
            f"💪 Log Latihan: *{jumlah_gym} kali*\n\n"
            "_Terus pakai bot ini biar badan makin gede!_ 🚀"
        )
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=tombol_kembali())
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_stats] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_help")
def callback_menu_help(call):
    try:
        bot.answer_callback_query(call.id)
        teks = (
            "❓ *BANTUAN & PANDUAN GYMBOT*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "*🍎 Kalori & Gula*\n→ Foto makanan buat hitung kalori otomatis.\n→ Bisa reply pesan hasil foto buat koreksi porsi.\n\n"
            "*💧 Progress & Air*\n→ Catat minum air & berat badan harian.\n\n"
            "*💪 Program Gym*\n→ Bikin program latihan (Noob/Pro).\n→ Catat log latihan harian.\n\n"
            "*💬 Chat PT AI*\n→ Tanya jawab seputar gym & nutrisi layaknya punya PT pribadi.\n\n"
            "*🔍 Scan Alat*\n→ Foto alat gym buat tau cara pakenya.\n\n"
            "*🍳 Meal Planner*\n→ Rekomendasi resep sesuai sisa kalori lu.\n\n"
            "*🎙️ Voice Note (Pesan Suara)*\n→ Kirim VN buat nyatet makanan atau latihan otomatis!\n\n"
            "*⚙️ Command Lain:*\n"
            "`/start` — Buka menu utama\n"
            "`/gym` — Langsung ke menu program gym\n"
            "`/cancel` — Batalin input yang lagi jalan"
        )
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=tombol_kembali())
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_help] error: {e}")