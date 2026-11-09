import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.queries import set_chat_mode, hapus_chat_history
from services.pt_chat import proses_chat_pt_core
from utils.helpers import strip_markdown

logger = logging.getLogger(__name__)
router = Router()

async def masuk_mode_pt(chat_id, user_id, message_id=None, bot=None):
    await set_chat_mode(user_id, True)
    teks = (
        "💬 <b>MODE CHAT PT AI AKTIF</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Sekarang lu bisa tanya apa aja seputar gym, latihan, nutrisi, atau minta saran program ke PT AI gw.\n\n"
        "<i>Contoh: 'Bro, bikin program latihan 3 hari buat pemula dong'</i>\n\n"
        "👇 <b>Silakan ketik pertanyaan lu langsung di chat!</b>"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🧹 Reset History", callback_data="pt_reset")
    builder.button(text="🔚 Keluar Chat", callback_data="pt_exit")
    builder.adjust(2)
    
    try:
        if message_id:
            await bot.edit_message_text(teks, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await bot.send_message(chat_id, teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"masuk_mode_pt error: {e}")

@router.callback_query(F.data == "menu_chat_pt")
async def callback_menu_chat_pt(callback: CallbackQuery):
    try:
        await callback.answer("💬 PT AI siap mendengarkan!")
        await masuk_mode_pt(callback.message.chat.id, str(callback.from_user.id), callback.message.message_id, callback.bot)
    except Exception as e: logger.error(f"[menu_chat_pt] error: {e}")

@router.callback_query(F.data == "pt_exit")
async def callback_pt_exit(callback: CallbackQuery):
    try:
        await set_chat_mode(str(callback.from_user.id), False)
        await callback.answer("✅ Keluar dari Chat PT")
        
        teks = "👋 <b>Keluar dari Chat PT.</b>\n\nBalik ke menu utama? Pencet tombol di bawah 👇"
        builder = InlineKeyboardBuilder()
        builder.button(text="🏠 Menu Utama", callback_data="menu_utama")
        
        try: 
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception: 
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: logger.error(f"[pt_exit] error: {e}")

@router.callback_query(F.data == "pt_reset")
async def callback_pt_reset(callback: CallbackQuery):
    try:
        await hapus_chat_history(str(callback.from_user.id))
        await callback.answer("🧹 History chat PT dihapus!")
        await masuk_mode_pt(callback.message.chat.id, str(callback.from_user.id), callback.message.message_id, callback.bot)
    except Exception as e: logger.error(f"[pt_reset] error: {e}")

async def proses_chat_pt(message: Message):
    user_id = str(message.from_user.id)
    teks = message.text.strip()
    
    await message.bot.send_chat_action(message.chat.id, 'typing')
    pesan_tunggu = await message.reply("💭 <i>PT AI lagi mikir...</i>", parse_mode="HTML")
    
    result = await proses_chat_pt_core(user_id=user_id, teks=teks)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔚 Keluar Chat", callback_data="pt_exit")
    builder.button(text="🏠 Menu", callback_data="menu_utama")
    builder.adjust(2)
    
    if result["status"] == "ai_failed":
        await pesan_tunggu.edit_text("❌ PT AI-nya lagi error nih bro. Coba lagi bentar ya.", reply_markup=builder.as_markup())
        return
        
    if result["status"] == "error":
        await pesan_tunggu.edit_text("❌ Terjadi kesalahan sistem. Coba lagi ya.", reply_markup=builder.as_markup())
        return
        
    balasan = result["data"]
    try:
        await pesan_tunggu.edit_text(balasan, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception:
        try:
            await pesan_tunggu.edit_text(strip_markdown(balasan), reply_markup=builder.as_markup())
        except Exception:
            await message.answer(strip_markdown(balasan)[:4000], reply_markup=builder.as_markup())