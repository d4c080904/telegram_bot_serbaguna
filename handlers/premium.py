import logging
import uuid
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.queries import get_user_premium_status

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "menu_premium")
async def callback_menu_premium(callback: CallbackQuery):
    try:
        await callback.answer()
        user_id = str(callback.from_user.id)
        
        is_premium, expired_at = await get_user_premium_status(user_id)
        
        if is_premium:
            teks = (
                "👑 <b>STATUS PREMIUM LU</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ Akun lu <b>AKTIF</b> sebagai Premium.\n"
                f"📅 Masa aktif sampai: <b>{expired_at.strftime('%d %B %Y')}</b>\n\n"
                "Terima kasih udah support GymMate! 🔥"
            )
            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 Kembali ke Menu Utama", callback_data="menu_utama")
        else:
            teks = (
                "👑 <b>UPGRADE KE PREMIUM</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Dapetin akses tanpa batas ke semua fitur GymMate!\n\n"
                "💰 Harga: <b>Rp 50.000 / bulan</b>\n"
                "✅ Unlimited Foto Makanan\n"
                "✅ Unlimited Chat PT AI\n"
                "✅ Laporan PDF Eksklusif\n\n"
                "Silakan klik tombol di bawah buat bayar pake QRIS:"
            )
            builder = InlineKeyboardBuilder()
            trx_id = str(uuid.uuid4())[:8].upper()
            builder.button(text="💳 Bayar Sekarang (Simulasi)", callback_data=f"simulate_pay_{trx_id}")
            builder.button(text="🔙 Kembali", callback_data="menu_utama")
            
        builder.adjust(1)
        try:
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception:
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
            
    except Exception as e:
        logger.error(f"menu_premium error: {e}")

@router.callback_query(F.data.startswith("simulate_pay_"))
async def callback_simulate_pay(callback: CallbackQuery):
    try:
        trx_id = callback.data.replace("simulate_pay_", "")
        user_id = str(callback.from_user.id)
        
        await callback.answer("⏳ Memproses pembayaran simulasi...")
        
        from database.queries import catat_payment_event, aktifkan_premium
        await catat_payment_event(trx_id, user_id, 50000, "SUCCESS")
        await aktifkan_premium(user_id, days=30)
        
        await callback.message.edit_text(
            "✅ <b>PEMBAYARAN BERHASIL (SIMULASI)!</b>\n\nAkun lu sekarang udah Premium selama 30 hari bro. 🔥",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"simulate_pay error: {e}")
        await callback.answer("❌ Gagal simulasi pembayaran.", show_alert=True)