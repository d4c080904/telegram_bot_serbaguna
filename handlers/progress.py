from bot_instance import bot
from telebot import types
from database.queries import tambah_air, get_total_air_hari_ini, tambah_berat_badan, get_berat_terakhir
import logging

logger = logging.getLogger(__name__)

BATAS_AIR_HARIAN = 2000 # Target 2 Liter

def tampil_dashboard_progress(chat_id, user_id, message_id=None):
    total_air = get_total_air_hari_ini(user_id)
    sisa_air = BATAS_AIR_HARIAN - total_air
    
    # Progress bar air
    persen = (total_air / BATAS_AIR_HARIAN) * 100
    if persen > 100: persen = 100
    bar_length = 10
    filled = int(bar_length * persen / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    # Ambil data berat terakhir
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
    
    btn_berat = types.InlineKeyboardButton("⚖️ Catat Berat Badan", callback_data="input_berat") # TOMBOL BARU
    btn_kembali = types.InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="menu_utama")
    
    markup.add(btn_250, btn_500)
    markup.add(btn_1000)
    markup.add(btn_berat) # PASANG DI SINI
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
        ml = int(call.data.split("_")[1])
        if tambah_air(call.from_user.id, ml):
            bot.answer_callback_query(call.id, f"✅ +{ml}ml air berhasil dicatat!", show_alert=False)
            tampil_dashboard_progress(call.message.chat.id, call.from_user.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Gagal mencatat air.", show_alert=True)
    except Exception as e: logger.error(f"tambah_air error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "input_berat")
def callback_input_berat(call):
    try:
        bot.answer_callback_query(call.id)
        teks = "⚖️ *Catat Berat Badan*\n\nSilakan ketik berat badan lu saat ini (dalam kg).\n_Contoh: 65.5_\n\n_Ketik /cancel kalau mau batal_"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Batal", callback_data="menu_progress"))
        bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        
        # Daftarin state nunggu input berat badan
        bot.register_next_step_handler(call.message, proses_input_berat)
    except Exception as e: logger.error(f"input_berat error: {e}")

def proses_input_berat(pesan):
    if pesan.text == '/cancel':
        tampil_dashboard_progress(pesan.chat.id, pesan.from_user.id)
        return
        
    try:
        # Coba ubah teks jadi float
        berat_baru = float(pesan.text.replace(',', '.'))
        
        if tambah_berat_badan(pesan.from_user.id, berat_baru):
            bot.reply_to(pesan, f"✅ Berat badan *{berat_baru} kg* berhasil dicatat!", parse_mode='Markdown')
        else:
            bot.reply_to(pesan, "❌ Gagal menyimpan data berat badan.")
            
    except ValueError:
        bot.reply_to(pesan, "❌ Format salah bro. Tolong ketik angka aja ya (Contoh: 65.5). Coba lagi klik tombolnya.")
        
    # Tampilkan dashboard lagi
    tampil_dashboard_progress(pesan.chat.id, pesan.from_user.id)