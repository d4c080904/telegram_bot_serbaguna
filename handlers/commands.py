from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.queries import save_wizard_state, set_chat_mode
import logging

logger = logging.getLogger(__name__)
router = Router()

# 1. Command /kalori
@router.message(Command("kalori"))
async def cmd_kalori(message: Message):
    try:
        from handlers.calorie import tampil_dashboard_kalori
        await tampil_dashboard_kalori(message.chat.id, str(message.from_user.id), bot=message.bot)
    except Exception as e:
        await message.answer(f"❌ Error di /kalori: {e}")

# 2. Command /air
@router.message(Command("air"))
async def cmd_air(message: Message):
    teks = (
        "💧 <b>PROGRESS & HYDRATION</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Silakan pilih aksi di bawah:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💧 Minum 250ml", callback_data="minum_250"), InlineKeyboardButton(text="💧 Minum 500ml", callback_data="minum_500")],
        [InlineKeyboardButton(text="🚰 Minum 1 Liter", callback_data="minum_1000")],
        [InlineKeyboardButton(text="⚖️ Catat Berat Badan", callback_data="menu_berat")],
        [InlineKeyboardButton(text="🔙 Kembali ke Menu Utama", callback_data="menu_utama")]
    ])
    await message.answer(teks, reply_markup=kb, parse_mode="HTML")

# 3. Command /pt
@router.message(Command("pt"))
async def cmd_pt(message: Message, state: FSMContext):
    try:
        user_id = str(message.from_user.id)
        await set_chat_mode(user_id, True) 
        
        teks = (
            "💬 <b>MODE CHAT PT AI AKTIF</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Sekarang lu bisa tanya apa aja seputar gym, latihan, nutrisi, atau minta saran program ke PT AI gw.\n\n"
            "👉 <b>Silakan ketik pertanyaan lu langsung di chat!</b>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Reset History", callback_data="reset_history"), InlineKeyboardButton(text="❌ Keluar Chat", callback_data="menu_utama")]
        ])
        await message.answer(teks, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Error di /pt: {e}")

# 4. Command /scan (MENGGUNAKAN SAVE_WIZARD_STATE)
@router.message(Command("scan"))
async def cmd_scan(message: Message):
    try:
        # ✅ PAKAI INI (BUKAN EquipmentState)
        await save_wizard_state(str(message.from_user.id), "waiting_equipment_photo", "waiting", {})
        
        teks = (
            "🔍 <b>SCAN ALAT GYM</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Silakan kirim foto alat gym yang mau lu pake. Gw bakal kasih tau nama alat, otot yang dilatih, dan cara pakenya yang bener."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Batal", callback_data="menu_utama")]
        ])
        await message.answer(teks, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Error di /scan: {e}")

# 5. Command /meal
@router.message(Command("meal"))
async def cmd_meal(message: Message):
    teks = (
        "🍳 <b>MEAL PLANNER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Klik tombol di bawah buat minta rekomendasi resep dari AI sesuai sisa kalori lu hari ini."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Generate Resep", callback_data="generate_meal")],
        [InlineKeyboardButton(text="🔙 Kembali", callback_data="menu_utama")]
    ])
    await message.answer(teks, reply_markup=kb, parse_mode="HTML")

# 6. Command /pdf
@router.message(Command("pdf"))
async def cmd_pdf(message: Message):
    teks = (
        "📄 <b>LAPORAN PDF</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Klik tombol di bawah buat download laporan lengkap lu (makanan, air, berat)."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Download Laporan", callback_data="download_pdf")],
        [InlineKeyboardButton(text="🔙 Kembali", callback_data="menu_utama")]
    ])
    await message.answer(teks, reply_markup=kb, parse_mode="HTML")