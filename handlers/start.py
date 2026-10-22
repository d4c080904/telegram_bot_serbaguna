from bot_instance import bot
from config import DB_PATH, CHAT_HISTORY_LIMIT
from database.db import get_db
from keyboards.menus import buat_menu_utama, teks_menu_utama, tombol_kembali
from utils.decorators import rate_limited
from utils.state import get_gym_wizard, clear_gym_wizard
import logging

logger = logging.getLogger(__name__)

@bot.message_handler(commands=['start', 'help', 'menu'])
@rate_limited
def kirim_sambutan(pesan):
    try: bot.reply_to(pesan, teks_menu_utama(), parse_mode='Markdown', reply_markup=buat_menu_utama())
    except Exception as e: logger.error(f"[start] error: {e}")

@bot.message_handler(commands=['cancel'])
@rate_limited
def cancel_handler(pesan):
    user_id = pesan.from_user.id
    if get_gym_wizard(user_id):
        clear_gym_wizard(user_id)
        bot.reply_to(pesan, "❌ *Input dibatalin.*\n\nMau ngapain lagi?", parse_mode='Markdown', reply_markup=buat_menu_utama())
    else: bot.reply_to(pesan, "ℹ️ Nggak ada yang lagi di-input kok.")

@bot.message_handler(commands=['stats'])
@rate_limited
def cek_statistik(pesan):
    try:
        conn = get_db(); cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM histori_chat WHERE user_id = ?", (str(pesan.from_user.id),))
        jumlah = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (str(pesan.from_user.id),))
        jumlah_chat = cursor.fetchone()[0]
        conn.close()
        bot.reply_to(pesan, f"📊 *Statistik Lu:*\n\n🔧 Pakai fitur: *{jumlah} kali*\n💬 Pesan chat AI: *{jumlah_chat} pesan*", parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[stats] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_utama")
def callback_menu_utama(call):
    try:
        bot.answer_callback_query(call.id)
        clear_gym_wizard(call.from_user.id)
        try: bot.edit_message_text(teks_menu_utama(), call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=buat_menu_utama())
        except Exception: bot.send_message(call.message.chat.id, teks_menu_utama(), parse_mode='Markdown', reply_markup=buat_menu_utama())
    except Exception as e: logger.error(f"[menu_utama] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_rapih")
def callback_menu_rapih(call):
    try:
        bot.answer_callback_query(call.id)
        teks = "📝 *MODE PERAPIH TEKS*\n━━━━━━━━━━━━━━━━━━━━\n\nKirim teks berantakan / bahasa gaul, nanti gw ubah jadi bahasa Indonesia baku.\n\n*Contoh:*\n`gw lg males bgt nih mau ngerjain tugas`\n→ _Saya sedang sangat malas mengerjakan tugas._\n\nSetelah dirapihin, bakal muncul tombol 🇬🇧 buat terjemahin ke bahasa Inggris.\n\nGass kirim teksnya! 👇"
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=tombol_kembali())
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_rapih] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_stats")
def callback_menu_stats(call):
    try:
        user_id = call.from_user.id
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM histori_chat WHERE user_id = ?", (str(user_id),)); jumlah = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (str(user_id),)); jumlah_chat = c.fetchone()[0]
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
        teks = "❓ *BANTUAN & PANDUAN*\n━━━━━━━━━━━━━━━━━━━━\n\n*📝 Perapih Teks*\n→ Kirim teks berantakan, dirapihin otomatis\n\n*💬 AI Chat*\n→ Ketik `/chat` atau pencet tombol di menu\n→ `/reset` hapus history\n→ `/exit` keluar dari chat\n\n*💪 Asisten Gym*\n→ Ketik `/gym` untuk menu (pilih Noob / Pro)\n→ `/gym [log]` buat log latihan/makan\n\n*📥 Downloader*\n→ Paste link TikTok/IG/YouTube\n\n*📊 Statistik*\n→ `/stats` atau via menu\n\n*⚙️ Command lain:*\n`/start` — menu utama\n`/menu` — buka menu lagi\n`/cancel` — batalin input"
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=tombol_kembali())
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_help] error: {e}")