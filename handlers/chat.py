from bot_instance import bot
from database.queries import set_chat_mode, hapus_chat_history, simpan_chat_message
from services.ai import chat_dengan_ai, terjemahkan_ke_inggris
from utils.decorators import rate_limited
from utils.helpers import strip_markdown
from keyboards.menus import buat_menu_utama
from telebot import types
import logging

logger = logging.getLogger(__name__)

@bot.message_handler(commands=['chat'])
@rate_limited
def mulai_chat(pesan):
    try:
        set_chat_mode(pesan.from_user.id, True)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🧹 Reset History", callback_data="chat_reset"), types.InlineKeyboardButton("🔚 Keluar Chat", callback_data="chat_exit"))
        markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama"))
        bot.reply_to(pesan, "💬 *Mode Chat AI Aktif!*\n━━━━━━━━━━━━━━━━━━━━\n\nSekarang lu bisa ngobrol bebas kayak ChatGPT. Gw bakal inget percakapan kita sebelumnya.\n\nKalau mau balik ke mode *Perapih Teks*, tinggal pencet tombol 🔚 *Keluar Chat* di bawah.\n\nGass mulai ngobrol! 🚀", parse_mode='Markdown', reply_markup=markup)
    except Exception as e: logger.error(f"[chat] error: {e}")

@bot.message_handler(commands=['exit', 'stopchat'])
@rate_limited
def keluar_chat(pesan):
    try:
        set_chat_mode(pesan.from_user.id, False)
        bot.reply_to(pesan, "👋 *Keluar dari Mode Chat.*\n\nBalik ke menu utama? Pencet tombol di bawah 👇", parse_mode='Markdown', reply_markup=buat_menu_utama())
    except Exception as e: logger.error(f"[exit] error: {e}")

@bot.message_handler(commands=['reset'])
@rate_limited
def reset_chat(pesan):
    try:
        hapus_chat_history(pesan.from_user.id)
        bot.reply_to(pesan, "🧹 *History Chat Dihapus!*\n\nKita mulai dari lembaran baru. Mau ngobrol apa? 😄", parse_mode='Markdown')
    except Exception as e: logger.error(f"[reset] error: {e}")

def proses_chat(pesan):
    user_id = pesan.from_user.id; teks = pesan.text.strip()
    bot.send_chat_action(pesan.chat.id, 'typing')
    pesan_tunggu = bot.reply_to(pesan, "💭 _AI lagi mikir..._", parse_mode="Markdown")
    simpan_chat_message(user_id, "user", teks)
    balasan = chat_dengan_ai(user_id, teks)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🔚 Keluar Chat", callback_data="chat_exit"), types.InlineKeyboardButton("🏠 Menu", callback_data="menu_utama"))
    if balasan:
        simpan_chat_message(user_id, "assistant", balasan)
        if len(balasan) > 4000: balasan = balasan[:4000] + "\n\n[...dipotong]"
        try: bot.edit_message_text(balasan, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception:
            try: bot.edit_message_text(strip_markdown(balasan), pesan.chat.id, pesan_tunggu.message_id, reply_markup=markup)
            except Exception: bot.reply_to(pesan, strip_markdown(balasan)[:4000], reply_markup=markup)
    else: bot.edit_message_text("❌ AI-nya lagi error nih bro. Coba lagi bentar ya.", pesan.chat.id, pesan_tunggu.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "menu_chat")
def callback_menu_chat(call):
    try:
        bot.answer_callback_query(call.id, "💬 Chat mode aktif!")
        set_chat_mode(call.from_user.id, True)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🧹 Reset History", callback_data="chat_reset"), types.InlineKeyboardButton("🔚 Keluar Chat", callback_data="chat_exit"))
        markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_utama"))
        teks = "💬 *MODE CHAT AI AKTIF*\n━━━━━━━━━━━━━━━━━━━━\n\nSekarang lu bisa ngobrol bebas kayak ChatGPT. Gw bakal inget percakapan kita.\n\n_Coba kirim: 'halo, perkenalkan diri lu'_ 👇"
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e: logger.error(f"[menu_chat] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "chat_exit")
def callback_chat_exit(call):
    try:
        set_chat_mode(call.from_user.id, False)
        
        # BUNGKUS ANSWER CALLBACK PAKE TRY EXCEPT
        try: bot.answer_callback_query(call.id, "✅ Keluar dari chat mode")
        except Exception: pass
        
        try: bot.edit_message_text("👋 *Keluar dari Mode Chat.*\n\nSekarang lu balik ke *mode normal*.\nKetik `/chat` kapan aja kalau mau ngobrol lagi. 🚀", call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=buat_menu_utama())
        except Exception: bot.send_message(call.message.chat.id, "👋 Keluar dari mode chat.", reply_markup=buat_menu_utama())
    except Exception as e: logger.error(f"[chat_exit] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "chat_reset")
def callback_chat_reset(call):
    try:
        hapus_chat_history(call.from_user.id)
        try: bot.answer_callback_query(call.id, "🧹 History dihapus!")
        except Exception: pass
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🔚 Keluar Chat", callback_data="chat_exit"), types.InlineKeyboardButton("🏠 Menu", callback_data="menu_utama"))
        try: bot.edit_message_text("🧹 *History Chat Dihapus!*\n\nKita mulai dari lembaran baru. Mau ngobrol apa? 😄", call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception: pass
    except Exception as e: logger.error(f"[chat_reset] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "terjemahkan")
@rate_limited
def proses_tombol_klik(call):
    try:
        try: bot.answer_callback_query(call.id, "Sedang menerjemahkan...")
        except Exception: pass
        bot.send_chat_action(call.message.chat.id, 'typing')
        teks_inggris = terjemahkan_ke_inggris(call.message.text)
        try: bot.reply_to(call.message, f"🗣️ *English:*\n{teks_inggris}", parse_mode='Markdown')
        except Exception: bot.reply_to(call.message, f"🗣️ English:\n{strip_markdown(teks_inggris)}")
    except Exception as e:
        logger.error(f"[callback] error: {e}")