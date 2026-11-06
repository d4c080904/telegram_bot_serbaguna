from bot_instance import bot
from database.queries import set_chat_mode, hapus_chat_history
from services.pt_chat import proses_chat_pt_core
from utils.helpers import strip_markdown
from telebot import types
import logging

logger = logging.getLogger(__name__)

def masuk_mode_pt(chat_id, user_id, message_id=None):
    set_chat_mode(user_id, True)
    teks = (
        "💬 *MODE CHAT PT AI AKTIF*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Sekarang lu bisa tanya apa aja seputar gym, latihan, nutrisi, atau minta saran program ke PT AI gw.\n\n"
        "_Contoh: 'Bro, bikin program latihan 3 hari buat pemula dong'_\n\n"
        "👇 *Silakan ketik pertanyaan lu langsung di chat!*"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🧹 Reset History", callback_data="pt_reset"),
        types.InlineKeyboardButton("🔚 Keluar Chat", callback_data="pt_exit")
    )
    
    try:
        if message_id:
            bot.edit_message_text(teks, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(chat_id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        logger.error(f"masuk_mode_pt error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_chat_pt")
def callback_menu_chat_pt(call):
    try:
        bot.answer_callback_query(call.id, "💬 PT AI siap mendengarkan!")
        masuk_mode_pt(call.message.chat.id, call.from_user.id, call.message.message_id)
    except Exception as e: logger.error(f"[menu_chat_pt] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "pt_exit")
def callback_pt_exit(call):
    try:
        set_chat_mode(call.from_user.id, False)
        try: bot.answer_callback_query(call.id, "✅ Keluar dari Chat PT")
        except Exception: pass
        
        teks = "👋 *Keluar dari Chat PT.*\n\nBalik ke menu utama? Pencet tombol di bawah 👇"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama"))
        
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e: logger.error(f"[pt_exit] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "pt_reset")
def callback_pt_reset(call):
    try:
        hapus_chat_history(call.from_user.id)
        try: bot.answer_callback_query(call.id, "🧹 History chat PT dihapus!")
        except Exception: pass
        masuk_mode_pt(call.message.chat.id, call.from_user.id, call.message.message_id)
    except Exception as e: logger.error(f"[pt_reset] error: {e}")

def proses_chat_pt(pesan):
    user_id = str(pesan.from_user.id)
    teks = pesan.text.strip()
    
    bot.send_chat_action(pesan.chat.id, 'typing')
    pesan_tunggu = bot.reply_to(pesan, "💭 _PT AI lagi mikir..._", parse_mode="Markdown")
    
    # Panggil Logic Bisnis (Service)
    result = proses_chat_pt_core(user_id=user_id, teks=teks)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔚 Keluar Chat", callback_data="pt_exit"),
        types.InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")
    )
    
    # Handle Hasil Response Service
    if result["status"] == "ai_failed":
        bot.edit_message_text("❌ PT AI-nya lagi error nih bro. Coba lagi bentar ya.", pesan.chat.id, pesan_tunggu.message_id, reply_markup=markup)
        return
        
    if result["status"] == "error":
        bot.edit_message_text("❌ Terjadi kesalahan sistem. Coba lagi ya.", pesan.chat.id, pesan_tunggu.message_id, reply_markup=markup)
        return
        
    # JIKA SUKSES
    balasan = result["data"]
    try:
        bot.edit_message_text(balasan, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown', reply_markup=markup)
    except Exception:
        # Fallback kalau Markdown bikin error
        try:
            bot.edit_message_text(strip_markdown(balasan), pesan.chat.id, pesan_tunggu.message_id, reply_markup=markup)
        except Exception:
            bot.reply_to(pesan, strip_markdown(balasan)[:4000], reply_markup=markup)