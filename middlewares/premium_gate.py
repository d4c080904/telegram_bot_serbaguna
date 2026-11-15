from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.queries import cek_status_vip
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

logger = logging.getLogger(__name__)

class PremiumGateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = str(event.from_user.id)
        
        # 1. PENGECUALIAN (User tetap bisa akses ini walau belum VIP)
        if isinstance(event, Message):
            if event.text and event.text.startswith(('/start', '/premium', '/help')):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            if event.data in ['menu_premium', 'bayar_qris', 'cek_status', 'menu_utama']:
                return await handler(event, data)
        
        # 2. CEK STATUS VIP
        is_vip = await cek_status_vip(user_id)
        if not is_vip:
            # Blokir akses
            if isinstance(event, Message):
                builder = InlineKeyboardBuilder()
                builder.button(text="👑 Beli Akses Premium", callback_data="menu_premium")
                await event.answer(
                    "🔒 <b>AKSES TERBATAS</b>\n\n"
                    "Bot ini eksklusif untuk member Premium.\n"
                    "Silakan berlangganan untuk menggunakan seluruh fitur GymMate.", 
                    reply_markup=builder.as_markup()
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Akses ditolak. Silakan berlangganan VIP dulu.", show_alert=True)
            return # Hentikan proses (jangan teruskan ke handler asli)
        
        # 3. JIKA VIP, SILAKAN LEWAT
        return await handler(event, data)