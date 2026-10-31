from bot_instance import bot
from keyboards.menus import buat_menu_utama, teks_menu_utama, buat_menu_gym_mode, teks_menu_gym_mode, tombol_kembali, buat_tombol_gender
from utils.decorators import rate_limited
from utils.state import set_onboarding_wizard, get_onboarding_wizard, clear_onboarding_wizard
from database.queries import get_user_profile, save_user_profile, get_total_air_hari_ini, get_berat_terakhir
from database.db import get_db
import logging

logger = logging.getLogger(__name__)

def buat_ringkasan_dashboard(user_id):
    """Fungsi buat bikin progress bar visual di menu utama"""
    air = get_total_air_hari_ini(user_id)
    target_air = 2000
    persen = min((air / target_air) * 100, 100)
    
    bar_length = 10
    filled = int(bar_length * persen / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    berat_data = get_berat_terakhir(user_id)
    berat_str = f"{berat_data[0][0]} kg" if berat_data else "Belum diisi"
    
    return (
        "📊 *RINGKASAN HARI INI:*\n"
        f"💧 Air: [{bar}] {int(persen)}% ({air}/{target_air} ml)\n"
        f"⚖️ Berat: {berat_str}\n"
    )

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
            # PAKAI TOMBOL SEKARANG
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

# ... (handler menu_rapih, menu_stats, menu_help biarin sama kayak sebelumnya) ...