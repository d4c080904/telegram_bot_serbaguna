from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.queries import cek_status_vip
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID
import logging

logger = logging.getLogger(__name__)

class PremiumGateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = str(event.from_user.id).strip()
        admin_id = str(ADMIN_ID).strip()

        # 1. ADMIN BEBAS AKSES
        if user_id == admin_id:
            return await handler(event, data)
            
        # 2. PENGECUALIAN (Bisa minta akses / bantuan)
        if isinstance(event, Message):
            if event.text and event.text.startswith(('/start', '/help')):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            if event.data in ['req_access', 'menu_help']:
                return await handler(event, data)
        
        # 3. CEK STATUS VIP
        is_vip = await cek_status_vip(user_id)
        if not is_vip:
            if isinstance(event, Message):
                builder = InlineKeyboardBuilder()
                builder.button(text="🔓 Minta Izin Akses", callback_data="req_access")
                await event.answer(
                    "🔒 <b>AKSES TERBATAS</b>\n\n"
                    "Bot ini eksklusif. Silakan minta izin akses ke Admin untuk bisa menggunakan bot ini.", 
                    reply_markup=builder.as_markup()
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Akses ditolak. Silakan minta izin ke Admin.", show_alert=True)
            return
            
        # 4. JIKA VIP, SILAKAN LEWAT
        return await handler(event, data)