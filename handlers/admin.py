from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID
from database.queries import request_access_db, approve_user_access, reject_user_access
from bot_instance import bot
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "req_access")
async def handle_req_access(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name

    await request_access_db(user_id, username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Setujui (3 Hari)", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Tolak", callback_data=f"reject_{user_id}")
        ]
    ])
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>PENDAFTARAN BARU</b>\n\nUser: @{username}\nID: <code>{user_id}</code>\nIngin meminta izin akses bot.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.message.edit_text("⏳ Permintaan Anda sudah dikirim ke Admin. Mohon tunggu persetujuan.")
    except Exception as e:
        logger.error(f"Gagal kirim pesan ke admin: {e}")
        await callback.message.edit_text("❌ Gagal mengirim pesan ke Admin.")

@router.callback_query(F.data.startswith("approve_"))
async def handle_approve(callback: CallbackQuery):
    # ✅ KUNCI KETAT: Bandingin ID pakai string
    if str(callback.from_user.id).strip() != str(ADMIN_ID).strip():
        return await callback.answer("Anda bukan Admin!", show_alert=True)

    user_id = callback.data.split("_")[1]
    await approve_user_access(user_id, days=3) 
    
    try:
        await bot.send_message(user_id, "✅ <b>AKSES DISETUJUI!</b>\n\nAdmin telah menyetujui akses Anda.\nSilakan ketik /start untuk mulai menggunakan bot. Anda mendapatkan masa trial gratis selama 3 hari.", parse_mode="HTML")
    except:
        pass
        
    await callback.message.edit_text(f"✅ User <code>{user_id}</code> berhasil disetujui (Trial 3 Hari).", parse_mode="HTML")

@router.callback_query(F.data.startswith("reject_"))
async def handle_reject(callback: CallbackQuery):
    # ✅ KUNCI KETAT: Bandingin ID pakai string
    if str(callback.from_user.id).strip() != str(ADMIN_ID).strip():
        return await callback.answer("Anda bukan Admin!", show_alert=True)

    user_id = callback.data.split("_")[1]
    await reject_user_access(user_id)
    
    try:
        await bot.send_message(user_id, "❌ <b>AKSES DITOLAK</b>\n\nMohon maaf, Admin menolak permintaan Anda.")
    except:
        pass
        
    await callback.message.edit_text(f"❌ User <code>{user_id}</code> telah ditolak.", parse_mode="HTML")