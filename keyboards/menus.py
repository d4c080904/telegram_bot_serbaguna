from telebot import types

def buat_menu_utama():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_rapih = types.InlineKeyboardButton("📝 Perapih Teks", callback_data="menu_rapih")
    btn_chat = types.InlineKeyboardButton("💬 AI Chat", callback_data="menu_chat")
    btn_gym = types.InlineKeyboardButton("💪 Asisten Gym", callback_data="menu_gym")
    btn_klr = types.InlineKeyboardButton("🍎 Kalori Tracker", callback_data="menu_kalori")
    btn_dl = types.InlineKeyboardButton("📥 Downloader", callback_data="menu_downloader")
    btn_stats = types.InlineKeyboardButton("📊 Statistik", callback_data="menu_stats")
    btn_help = types.InlineKeyboardButton("❓ Bantuan", callback_data="menu_help")
    
    markup.add(btn_rapih, btn_chat)
    markup.add(btn_gym, btn_klr)
    markup.add(btn_dl, btn_stats)
    markup.add(btn_help)
    return markup

def teks_menu_utama():
    return (
        "🏠 *MENU UTAMA*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Selamat datang di *Bot Serba Guna*! 🤖\n\n"
        "Pilih fitur yang lu mau pakai dengan pencet tombol di bawah:\n\n"
        "📝 *Perapih Teks* — ubah bahasa gaul jadi baku\n"
        "💬 *AI Chat* — ngobrol bebas kayak ChatGPT\n"
        "💪 *Asisten Gym* — PT AI pribadi lu\n"
        "🍎 *Kalori Tracker* — Catat makan pakai foto\n"
        "📥 *Downloader* — TikTok, IG, YouTube\n"
        "📊 *Statistik* — cek pemakaian lu\n"
        "❓ *Bantuan* — panduan lengkap\n\n"
        "_Tinggal pencet, nggak usah ngetik command!_ 👇"
    )

def tombol_kembali():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="menu_utama")
    markup.add(btn)
    return markup