import logging
from bot_instance import bot
from telebot import types
from services.equipment import proses_foto_alat_core
from utils.decorators import rate_limited
from database.queries import save_wizard_state, delete_wizard_state

logger = logging.getLogger(__name__)

@bot.callback_query_handler(func=lambda call: call.data == "menu_scan_alat")
def callback_scan_alat(call):
    try:
        bot.answer_callback_query(call.id)
        save_wizard_state(str(call.from_user.id), "waiting_equipment_photo", "waiting", {})
        
        teks = (
            "🔍 *SCAN ALAT GYM*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Silakan kirim foto alat gym yang mau lu pake. "
            "Gw bakal kasih tau nama alat, otot yang dilatih, dan cara pakenya yang bener."
        )
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Batal", callback_data="menu_gym_mode"))
        bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    except Exception as e: 
        logger.error(f"scan_alat error: {e}")

def proses_foto_alat(pesan):
    user_id = str(pesan.from_user.id)
    delete_wizard_state(user_id, "waiting_equipment_photo")
    
    bot.send_chat_action(pesan.chat.id, 'typing')
    pesan_tunggu = bot.reply_to(pesan, "⏳ _AI lagi ngenalin alat gym lu..._")
    
    try:
        file_info = bot.get_file(pesan.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Panggil Logic Bisnis (Service)
        result = proses_foto_alat_core(image_bytes=downloaded_file)
        
        # Handle Hasil Response Service
        if result["status"] == "ai_failed":
            bot.edit_message_text("❌ AI gagal ngenalin alatnya. Coba foto dari sudut yang lebih jelas.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        if result["status"] == "error":
            bot.edit_message_text("❌ Terjadi kesalahan sistem saat memproses foto.", pesan.chat.id, pesan_tunggu.message_id)
            return
            
        # JIKA SUKSES
        hasil = result["data"]
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Kembali ke GYM MODE", callback_data="menu_gym_mode"))
        
        try:
            bot.edit_message_text(hasil, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception:
            # Fallback kalau format teks dari AI bikin error Markdown
            bot.edit_message_text(hasil, pesan.chat.id, pesan_tunggu.message_id, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"proses_foto_alat error: {e}")
        bot.edit_message_text("❌ Terjadi kesalahan saat memproses foto.", pesan.chat.id, pesan_tunggu.message_id)