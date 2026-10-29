import re
from bot_instance import bot
from telebot import types
from database.queries import tambah_air, get_total_air_hari_ini, tambah_berat_badan, get_berat_terakhir, hapus_semua_berat
import logging

logger = logging.getLogger(__name__)

BATAS_AIR_HARIAN = 2000

def tampil_dashboard_progress(chat_id, user_id, message_id=None):
    total_air = get_total_air_hari_ini(user_id)
    sisa_air = BATAS_AIR_HARIAN - total_air
    
    persen = (total_air / BATAS_AIR_HARIAN) * 100
    if persen > 100: persen = 100
    bar_length = 10
    filled = int(bar_length * persen / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    berat_data = get_berat_terakhir(user_id)
    if not berat_data:
        teks_berat = "⚖️ *Berat Badan:* Belum ada data."
    elif len(berat_data) == 1:
        teks_berat = f"⚖️ *Berat Badan Terakhir:* {berat_data[0][0]} kg"
    else:
        curr_berat = berat_data[0][0]
        prev_berat = berat_data[1][0]
        selisih = curr_berat - prev_berat
        
        if selisih > 0: status = f"🔴 Naik {selisih:.1f} kg"
        elif selisih < 0: status = f"🟢 Turun {abs(selisih):.1f} kg"
        else: status = "⚪ Stabil"
            
        teks_berat = f"⚖️ *Berat Badan Terakhir:* {curr_berat} kg ({status})"

    teks = (
        "📈 *PROGRESS & HYDRATION*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💧 *WATER TRACKER*\n"
        f"🎯 Target: {BATAS_AIR_HARIAN} ml\n"
        f"💦 Sudah Minum: *{total_air} ml*\n"
        f"📊 Progress: [{bar}] {int(persen)}%\n"
    )
    
    if sisa_air > 0:
        teks += f"⚠️ Kurang *{sisa_air} ml* lagi bro!\n\n"
    else:
        teks += "✅ *Hidrasi Hari Ini Tercukupi!* Mantap! 🔥\n\n"
        
    teks += f"{teks_berat}\n\n"
    teks += "Pilih aksi di bawah:"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_250 = types.InlineKeyboardButton("💧 Minum 250ml", callback_data="water_250")
    btn_500 = types.InlineKeyboardButton("💧 Minum 500ml", callback_data="water_500")
    btn_1000 = types.InlineKeyboardButton("🚰 Minum 1 Liter", callback_data="water_1000")
    
    # TOMBOL BARU
    btn_manual = types.InlineKeyboardButton("✍️ Input Manual", callback_data="water_manual")
    
    btn_berat = types.InlineKeyboardButton("⚖️ Catat Berat Badan", callback_data="input_berat")
    btn_reset = types.InlineKeyboardButton("🗑️ Reset Log Berat", callback_data="reset_berat")
    btn_kembali = types.InlineKeyboardButton("🔙 Kembali ke GYM MODE", callback_data="menu_gym_mode")
    
    markup.add(btn_250, btn_500)
    markup.add(btn_1000, btn_manual) # Tombol manual ditaruh di sini
    markup.add(btn_berat, btn_reset)
    markup.add(btn_kembali)
    
    try:
        if message_id: bot.edit_message_text(teks, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
        else: bot.send_message(chat_id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"tampil_dashboard_progress error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_progress")
def callback_menu_progress(call):
    try:
        bot.answer_callback_query(call.id)
        tampil_dashboard_progress(call.message.chat.id, call.from_user.id, call.message.message_id)
    except Exception as e: logger.error(f"menu_progress error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("water_"))
def callback_tambah_air(call):
    try:
        # Cek kalau yang dipencet tombol manual
        if call.data == "water_manual":
            bot.answer_callback_query(call.id)
            teks = (
                "✍️ *Input Air Manual*\n\n"
                "Silakan ketik jumlah air yang lu minum.\n\n"
                "📌 *Format:*\n"
                "Bisa ketik angka (dalam ml) atau pakai huruf L/liter.\n\n"
                "*Contoh:*\n"
                "`500` (untuk 500 ml)\n"
                "`1500` (untuk 1500 ml)\n"
                "`1.5 L` (untuk 1.5 Liter)\n"
                "`2 liter` (untuk 2 Liter)\n\n"
                "_Ketik /cancel kalau mau batal_"
            )
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Batal", callback_data="menu_progress"))
            bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
            bot.register_next_step_handler(call.message, proses_input_air_manual)
            return

        # Kalau tombol biasa (water_250, water_500, water_1000)
        ml = int(call.data.split("_")[1])
        if tambah_air(call.from_user.id, ml):
            bot.answer_callback_query(call.id, f"✅ +{ml}ml air berhasil dicatat!", show_alert=False)
            tampil_dashboard_progress(call.message.chat.id, call.from_user.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Gagal mencatat air.", show_alert=True)
    except Exception as e: logger.error(f"tambah_air error: {e}")

def proses_input_air_manual(pesan):
    if pesan.text == '/cancel':
        tampil_dashboard_progress(pesan.chat.id, pesan.from_user.id)
        return
        
    try:
        text = pesan.text.lower().strip()
        # Cari angka di dalam teks (bisa desimal)
        match = re.search(r'([\d\.]+)', text)
        if not match:
            bot.reply_to(pesan, "❌ Angka tidak ditemukan. Coba ketik angka ya (misal: 500).")
            return
            
        angka = float(match.group(1))
        
        # Cek apakah user ngetik 'l' atau 'liter'
        if 'l' in text or 'liter' in text:
            ml = int(angka * 1000)
        else:
            ml = int(angka)
            
        if ml <= 0:
            bot.reply_to(pesan, "❌ Jumlah air tidak boleh 0 atau minus.")
            return
            
        if ml > 10000:
            bot.reply_to(pesan, "❌ Jumlah air tidak wajar. Maksimal 10 Liter per input ya.")
            return
            
        if tambah_air(pesan.from_user.id, ml):
            bot.reply_to(pesan, f"✅ Berhasil mencatat minum *{ml} ml*!", parse_mode='Markdown')
        else:
            bot.reply_to(pesan, "❌ Gagal menyimpan data air.")
            
    except ValueError:
        bot.reply_to(pesan, "❌ Format angka salah. Coba lagi klik tombolnya.")
        
    tampil_dashboard_progress(pesan.chat.id, pesan.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == "input_berat")
def callback_input_berat(call):
    try:
        bot.answer_callback_query(call.id)
        teks = "⚖️ *Catat Berat Badan*\n\nSilakan ketik berat badan lu saat ini (dalam kg).\n_Contoh: 65.5_\n\n_Ketik /cancel kalau mau batal_"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Batal", callback_data="menu_progress"))
        bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        
        bot.register_next_step_handler(call.message, proses_input_berat)
    except Exception as e: logger.error(f"input_berat error: {e}")

def proses_input_berat(pesan):
    if pesan.text == '/cancel':
        tampil_dashboard_progress(pesan.chat.id, pesan.from_user.id)
        return
        
    try:
        berat_baru = float(pesan.text.replace(',', '.'))
        
        if tambah_berat_badan(pesan.from_user.id, berat_baru):
            bot.reply_to(pesan, f"✅ Berat badan *{berat_baru} kg* berhasil dicatat!", parse_mode='Markdown')
        else:
            bot.reply_to(pesan, "❌ Gagal menyimpan data berat badan.")
            
    except ValueError:
        bot.reply_to(pesan, "❌ Format salah bro. Tolong ketik angka aja ya (Contoh: 65.5). Coba lagi klik tombolnya.")
        
    tampil_dashboard_progress(pesan.chat.id, pesan.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == "reset_berat")
def callback_reset_berat(call):
    try:
        bot.answer_callback_query(call.id)
        if hapus_semua_berat(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ History berat badan berhasil dihapus!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Gagal menghapus history.", show_alert=True)
        tampil_dashboard_progress(call.message.chat.id, call.from_user.id, call.message.message_id)
    except Exception as e:
        logger.error(f"reset_berat error: {e}")