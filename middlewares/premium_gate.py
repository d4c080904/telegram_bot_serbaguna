from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.queries import cek_status_vip, update_last_active
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID
from database.db import get_db
import logging

logger = logging.getLogger(__name__)

class PremiumGateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = str(event.from_user.id).strip()
        admin_id = str(ADMIN_ID).strip()

        # 1. ADMIN BEBAS AKSES
        if user_id == admin_id:
            await update_last_active(user_id)
            return await handler(event, data)

        # 2. DEFINE EXEMPTIONS (Biar user baru/banned bisa minta akses)
        is_exempt = False
        if isinstance(event, Message):
            if event.text and event.text.startswith(('/start', '/help')):
                is_exempt = True
        elif isinstance(event, CallbackQuery):
            if event.data in ['req_access', 'menu_help']:
                is_exempt = True

        # 3. CEK BANNED (HARD BLOCK)
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT is_banned, banned_reason FROM users WHERE user_id = $1", user_id)
            if row and row['is_banned'] and not is_exempt:
                reason = row['banned_reason'] or "Pelanggaran sistem"
                if isinstance(event, Message):
                    builder = InlineKeyboardBuilder()
                    builder.button(text="🔓 Minta Izin Akses Lagi", callback_data="req_access")
                    await event.answer(
                        f"🚫 <b>AKSES LU DICABUT</b>\n\nAlasan: <i>{reason}</i>\n\nKetik /start atau klik tombol di bawah untuk mengajukan akses kembali.",
                        parse_mode="HTML", reply_markup=builder.as_markup()
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer("Akses dicabut. Silakan ketik /start untuk minta akses.", show_alert=True)
                return

        # 4. CEK STATUS VIP
        is_vip = await cek_status_vip(user_id)
        if not is_vip and not is_exempt:
            if isinstance(event, Message):
                builder = InlineKeyboardBuilder()
                builder.button(text="🔓 Minta Izin Akses", callback_data="req_access")
                await event.answer(
                    "🔒 <b>AKSES TERBATAS</b>\n\n"
                    "Bot ini eksklusif. Silakan minta izin akses ke Admin untuk bisa menggunakan bot ini.", 
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Akses terbatas! Silakan ketik /start untuk minta akses.", show_alert=True)
            return

        # 5. LEWATKAN & UPDATE LAST ACTIVE
        await update_last_active(user_id)
        return await handler(event, data)