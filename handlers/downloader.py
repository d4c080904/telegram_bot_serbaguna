from bot_instance import bot
from keyboards.menus import tombol_kembali
import logging

logger = logging.getLogger(__name__)

@bot.callback_query_handler(func=lambda call: call.data == "menu_downloader")
def callback_menu_downloader(call):
    try:
        bot.answer_callback_query(call.id)
        teks = "📥 *DOWNLOADER ALL-IN-ONE*\n━━━━━━━━━━━━━━━━━━━━\n\nTinggal paste link-nya aja, gw yang urus! 🚀\n\n🎵 *TikTok* — video + slideshow foto\n📸 *Instagram* — Reels, foto, carousel\n▶️ *YouTube* — video & Shorts\n\n*Cara pakai:*\nCopy link → paste ke chat → kirim ✈️\n\n_Catatan: video max 50 MB (limit Telegram)_"
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=tombol_kembali())
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_downloader] error: {e}")