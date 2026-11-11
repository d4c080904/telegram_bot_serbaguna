import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.barcode_scanner import decode_barcode, get_product_from_openfoodfacts
from database.queries import tambah_food_log
from handlers.calorie import tampil_dashboard_kalori

logger = logging.getLogger(__name__)
router = Router()

class BarcodeState(StatesGroup):
    waiting_barcode = State()

@router.callback_query(F.data == "menu_barcode")
async def callback_menu_barcode(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await state.set_state(BarcodeState.waiting_barcode)
        
        teks = (
            "📷 <b>SCAN BARCODE PRODUK</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Silakan kirim foto barcode (garis hitam-putih) dari kemasan makanan/minuman yang mau lu catat.\n\n"
            "<i>*Pastikan barcode kelihatan jelas dan gak blur.</i>"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Batal", callback_data="menu_kalori") # <--- Balik ke Kalori
        
        try:
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception:
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"barcode menu error: {e}")

@router.message(BarcodeState.waiting_barcode, F.photo)
async def handle_barcode_photo(message: Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    
    pesan_tunggu = await message.reply("⏳ <i>AI lagi nge-scan barcode lu...</i>", parse_mode="HTML")
    
    try:
        file_id = message.photo[-1].file_id
        file_info = await message.bot.get_file(file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        image_bytes = downloaded_file.read()
        
        barcode_num = decode_barcode(image_bytes)
        
        if not barcode_num:
            await pesan_tunggu.edit_text(
                "❌ Barcode gagal dibaca. Coba foto lebih dekat dan pastiin barcode-nya jelas (garis hitam-putih)."
            )
            return
            
        await pesan_tunggu.edit_text(f"🔍 Barcode terdeteksi: <code>{barcode_num}</code>\n⏳ <i>Mencari info gizi di database...</i>", parse_mode="HTML")
        
        produk = await get_product_from_openfoodfacts(barcode_num)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Kembali ke Menu Kalori", callback_data="menu_kalori") # <--- Balik ke Kalori
        
        if not produk:
            await pesan_tunggu.edit_text(
                "❌ Produk gak ada di database OpenFoodFacts.\nCoba foto makanannya langsung pake menu Kalori ya.", 
                reply_markup=builder.as_markup()
            )
            return
            
        # Simpan ke database (Anggap 1 porsi = 100g)
        berhasil = await tambah_food_log(
            user_id, pesan_tunggu.message_id, message.message_id, barcode_num,
            f"{produk['nama']} ({produk['kategori']})", "1 porsi (100g)",
            produk['kalori'], produk['protein'], produk['karbo'], produk['lemak'], produk['gula']
        )
        
        if berhasil:
            await pesan_tunggu.edit_text(
                f"✅ <b>Berhasil Dicatat dari Barcode!</b>\n\n"
                f"🛒 Produk: <b>{produk['nama']}</b>\n"
                f"📦 Kategori: <b>{produk['kategori']}</b>\n"
                f"⚖️ Porsi: <b>1 porsi (100g)</b>\n"
                f"🔥 Kalori: <b>{produk['kalori']} kcal</b>\n"
                f"🥩 Protein: <b>{produk['protein']}g</b>\n"
                f"🍚 Karbo: <b>{produk['karbo']}g</b>\n"
                f"🧈 Lemak: <b>{produk['lemak']}g</b>\n"
                f"🍭 Gula: <b>{produk['gula']}g</b>\n\n"
                f"<i>*Data gizi berdasarkan takaran 100g produk.</i>",
                parse_mode="HTML", reply_markup=builder.as_markup()
            )
            # Balikin ke Dashboard Kalori
            await tampil_dashboard_kalori(message.chat.id, user_id, bot=message.bot)
        else:
            await pesan_tunggu.edit_text("❌ Gagal menyimpan data produk ke database (mungkin duplikat).", reply_markup=builder.as_markup())
            
    except Exception as e:
        logger.error(f"[barcode] error: {e}")
        await pesan_tunggu.edit_text("❌ Terjadi kesalahan sistem saat memproses barcode.")