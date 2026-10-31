from telebot import types

def buat_menu_utama():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_rapih = types.InlineKeyboardButton("📝 Perapih Teks", callback_data="menu_rapih")
    btn_chat = types.InlineKeyboardButton("💬 AI Chat", callback_data="menu_chat")
    btn_gym_mode = types.InlineKeyboardButton("🏋️‍♂️ GYM MODE", callback_data="menu_gym_mode")
    btn_dl = types.InlineKeyboardButton("📥 Downloader", callback_data="menu_downloader")
    btn_stats = types.InlineKeyboardButton("📊 Statistik", callback_data="menu_stats")
    btn_help = types.InlineKeyboardButton("❓ Bantuan", callback_data="menu_help")
    
    markup.add(btn_rapih, btn_chat)
    markup.add(btn_gym_mode, btn_dl)
    markup.add(btn_stats, btn_help)
    return markup

def teks_menu_utama(ringkasan=""):
    return (
        "🏠 *MENU UTAMA*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ringkasan}\n\n"
        "Pilih fitur yang lu mau pakai dengan pencet tombol di bawah:\n\n"
        "📝 *Perapih Teks* — ubah bahasa gaul jadi baku\n"
        "💬 *AI Chat* — ngobrol bebas kayak ChatGPT\n"
        "🏋️‍♂️ *GYM MODE* — Semua fitur Gym, Kalori, Air, Meal Planner\n"
        "📥 *Downloader* — TikTok, IG, YouTube\n"
        "📊 *Statistik* — cek pemakaian lu\n"
        "❓ *Bantuan* — panduan lengkap\n\n"
        "_Tinggal pencet, nggak usah ngetik command!_ 👇"
    )

def buat_menu_gym_mode():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_makan = types.InlineKeyboardButton("🍎 Kalori & Gula", callback_data="menu_kalori")
    btn_progress = types.InlineKeyboardButton("💧 Progress & Air", callback_data="menu_progress")
    btn_meal = types.InlineKeyboardButton("🍳 Meal Planner", callback_data="menu_meal_planner")
    btn_program = types.InlineKeyboardButton("💪 Profil & Program", callback_data="menu_gym")
    btn_export = types.InlineKeyboardButton("📥 Export Laporan CSV", callback_data="menu_export") # TOMBOL BARU
    btn_chat_pt = types.InlineKeyboardButton("💬 Chat PT AI", callback_data="menu_chat")
    btn_back = types.InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="menu_utama")
    
    markup.add(btn_makan, btn_progress)
    markup.add(btn_meal, btn_program)
    markup.add(btn_export) # PASANG DI SINI
    markup.add(btn_chat_pt)
    markup.add(btn_back)
    return markup

def teks_menu_gym_mode():
    return (
        "🏋️‍♂️ *WELCOME TO GYM MODE* 🏋️‍♂️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Semua fitur buat ngebantu progres gym lu ada di sini.\n"
        "_(Ketik atau kirim Voice Note kapan aja buat nyatet makanan/latihan)_\n\n"
        "👇 *Pilih menu di bawah:*"
    )

def buat_tombol_gender():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_l = types.InlineKeyboardButton("🙎‍♂️ Laki-laki", callback_data="onboard_gender_L")
    btn_p = types.InlineKeyboardButton("🙎‍♀️ Perempuan", callback_data="onboard_gender_P")
    markup.add(btn_l, btn_p)
    return markup

def tombol_kembali():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")
    markup.add(btn)
    return markup