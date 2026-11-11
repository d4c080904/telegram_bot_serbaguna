from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def buat_menu_utama():
    builder = InlineKeyboardBuilder()
    builder.button(text="🍎 Kalori & Gula", callback_data="menu_kalori")
    builder.button(text="💧 Progress & Air", callback_data="menu_progress")
    builder.button(text="💪 Program Gym", callback_data="menu_gym")
    builder.button(text="💬 Chat PT AI", callback_data="menu_chat_pt")
    builder.button(text="🔍 Scan Alat Gym", callback_data="menu_scan_alat")
    builder.button(text="🍳 Meal Planner", callback_data="menu_meal_planner")
    builder.button(text="📄 Laporan PDF", callback_data="menu_export")
    builder.button(text="📊 Statistik", callback_data="menu_stats")
    builder.button(text="❓ Bantuan", callback_data="menu_help")
    builder.adjust(2) # Diatur 2 kolom biar rapi
    return builder.as_markup()

def tombol_kembali():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Kembali ke Menu Utama", callback_data="menu_utama")
    return builder.as_markup()

def buat_tombol_gender():
    builder = InlineKeyboardBuilder()
    builder.button(text="👨 Laki-laki", callback_data="onboard_gender_L")
    builder.button(text="👩 Perempuan", callback_data="onboard_gender_P")
    builder.adjust(2)
    return builder.as_markup()

def teks_menu_utama(ringkasan):
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{ringkasan}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Silakan pilih fitur yang mau lu pake di bawah:"
    )