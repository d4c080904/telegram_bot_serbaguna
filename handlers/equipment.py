import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.equipment import proses_foto_alat_core
from database.queries import save_wizard_state, delete_wizard_state

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "menu_scan_alat")
async def callback_scan_alat(callback: CallbackQuery):
    try:
        await callback.answer()
        await save_wizard_state(str(callback.from_user.id), "waiting_equipment_photo", "waiting", {})
        
        teks = (
            "🔍 <b>SCAN ALAT GYM</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Silakan kirim foto alat gym yang mau lu pake. "
            "Gw bakal kasih tau nama alat, otot yang dilatih, dan cara pakenya yang bener."
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Batal", callback_data="menu_gym_mode")
        try:
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception:
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: 
        logger.error(f"scan_alat error: {e}")

async def proses_foto_alat(message: Message):
    user_id = str(message.from_user.id)
    await delete_wizard_state(user_id, "waiting_equipment_photo")
    
    await message.bot.send_chat_action(message.chat.id, 'typing')
    pesan_tunggu = await message.reply("⏳ <i>AI lagi ngenalin alat gym lu...</i>", parse_mode="HTML")
    
    try:
        file_id = message.photo[-1].file_id
        file_info = await message.bot.get_file(file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        image_bytes = downloaded_file.read()
        
        result = await proses_foto_alat_core(image_bytes=image_bytes)
        
        if result["status"] == "ai_failed":
            await pesan_tunggu.edit_text("❌ AI gagal ngenalin alatnya. Coba foto dari sudut yang lebih jelas.")
            return
            
        if result["status"] == "error":
            await pesan_tunggu.edit_text("❌ Terjadi kesalahan sistem saat memproses foto.")
            return
            
        hasil = result["data"]
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Kembali ke GYM MODE", callback_data="menu_gym_mode")
        
        try:
            await pesan_tunggu.edit_text(hasil, reply_markup=builder.as_markup())
        except Exception:
            await pesan_tunggu.edit_text(hasil, reply_markup=builder.as_markup())
            
    except Exception as e:
        logger.error(f"proses_foto_alat error: {e}")
        await pesan_tunggu.edit_text("❌ Terjadi kesalahan saat memproses foto.")