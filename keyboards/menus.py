from telebot import types

def buat_menu_utama():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Baris 1: Fitur Harian
    btn_kalori = types.InlineKeyboardButton("🍎 Kalori & Gula", callback_data="menu_kalori")
    btn_progress = types.InlineKeyboardButton("💧 Air & Berat", callback_data="menu_progress")
    
    # Baris 2: Fitur AI
    btn_meal = types.InlineKeyboardButton("🍳 Meal Planner", callback_data="menu_meal_planner")
    btn_program = types.InlineKeyboardButton("💪 Program Gym", callback_data="menu_gym")
    
    # BARIS BARU: TOMBOL CHAT PT AI
    btn_chat_pt = types.InlineKeyboardButton("💬 Tanya Chat PT AI", callback_data="menu_chat_pt")
    
    # Baris 3: Fitur Tools
    btn_scan = types.InlineKeyboardButton("🔍 Scan Alat", callback_data="menu_scan_alat")
    btn_export = types.InlineKeyboardButton("📥 Export CSV", callback_data="menu_export")
    
    # Baris 4: Info
    btn_stats = types.InlineKeyboardButton("📊 Statistik", callback_data="menu_stats")
    btn_help = types.InlineKeyboardButton("❓ Bantuan", callback_data="menu_help")
    
    markup.add(btn_kalori, btn_progress)
    markup.add(btn_meal, btn_program)
    markup.add(btn_chat_pt) # <--- Tombol PT AI ditaruh di sini
    markup.add(btn_scan, btn_export)
    markup.add(btn_stats, btn_help)
    return markup

def teks_menu_utama(ringkasan=""):
    return (
        "🏠 *DASHBOARD GYMBOT* 🏋️‍♂️\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ringkasan}\n"
        "👇 *Silakan pilih menu di bawah ini:*"
    )

def buat_tombol_gender():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_l = types.InlineKeyboardButton("🙎‍♂️ Laki-laki", callback_data="onboard_gender_L")
    btn_p = types.InlineKeyboardButton("🙎‍♀️ Perempuan", callback_data="onboard_gender_P")
    markup.add(btn_l, btn_p)
    return markup

def tombol_kembali():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="menu_utama")
    markup.add(btn)
    return markup