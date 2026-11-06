import logging
from bot_instance import bot
from database.queries import simpan_ke_db, update_food_log, cek_id_makanan, is_chat_mode, get_wizard_state
from services.ai import koreksi_foto_makanan
from utils.helpers import strip_markdown
from utils.decorators import rate_limited
from utils.state import get_gym_wizard, get_onboarding_wizard
from handlers.gym import proses_gym_wizard
from handlers.start import proses_onboarding
from handlers.calorie import proses_foto_makanan, tampil_dashboard_kalori
from handlers.equipment import proses_foto_alat
from handlers.pt_chat import proses_chat_pt

logger = logging.getLogger(__name__)

@bot.message_handler(content_types=["text"])
@rate_limited
def respon_pesan(pesan):
    try:
        teks_asli = pesan.text.strip()
        user_id = str(pesan.from_user.id)

        # 1. CEK ONBOARDING (Isi Nama, Umur, dll)
        onboarding = get_onboarding_wizard(user_id)
        if onboarding:
            proses_onboarding(pesan)
            return

        # 2. CEK GYM WIZARD (Input Data Pro)
        wizard = get_gym_wizard(user_id)
        if wizard:
            proses_gym_wizard(pesan, wizard)
            return

        # --- CEK MODE CHAT PT AI ---
        if is_chat_mode(user_id) and not teks_asli.startswith('/'):
            proses_chat_pt(pesan)
            return
        # ------------------------------------------

        # 3. FITUR KOREKSI KALORI (Reply pesan makanan buat dibenerin)
        if pesan.reply_to_message:
            if cek_id_makanan(user_id, pesan.reply_to_message.message_id):
                bot.send_chat_action(pesan.chat.id, 'typing')
                pesan_tunggu = bot.reply_to(pesan, "⏳ _Oke bro, AI lagi ngitung ulang kalorinya..._")
                hasil_baru = koreksi_foto_makanan(teks_asli)
                if hasil_baru:
                    berhasil = update_food_log(
                        user_id, pesan.reply_to_message.message_id,
                        hasil_baru.get('nama_makanan', 'Makanan'), hasil_baru.get('estimasi_porsi', '1 porsi'), 
                        hasil_baru.get('kalori', 0), hasil_baru.get('protein', 0), 
                        hasil_baru.get('karbo', 0), hasil_baru.get('lemak', 0), hasil_baru.get('gula', 0)
                    )
                    if berhasil:
                        bot.edit_message_text(f"✅ *Koreksi Berhasil!*\n\n🍽️ Nama Baru: *{hasil_baru.get('nama_makanan')}*\n🔥 Kalori Baru: *{hasil_baru.get('kalori')} kcal*\n🍭 Gula: *{hasil_baru.get('gula')}g*\n", pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
                        tampil_dashboard_kalori(pesan.chat.id, user_id)
                        return
                    else:
                        bot.edit_message_text("❌ Gagal update database.", pesan.chat.id, pesan_tunggu.message_id)
                        return
                else:
                    bot.edit_message_text("❌ AI gagal memproses koreksi.", pesan.chat.id, pesan_tunggu.message_id)
                    return
            
            # Kalau nge-reply dashboard
            elif pesan.reply_to_message.from_user.id == bot.get_me().id:
                if "FOOD & SUGAR TRACKER" in (pesan.reply_to_message.text or "") or "KALORI TRACKER" in (pesan.reply_to_message.text or ""):
                    bot.reply_to(pesan, "⚠️ *Pesan yang lu reply itu Dashboard, bukan detail makanannya.*\n\nBiar bisa dikoreksi, tolong reply pesan *Foto Makanan* atau *✅ Berhasil Dicatat!* ya.", parse_mode='Markdown')
                    return

        # 4. JIKA USER KIRIM TEKS SEMBARANG
        if teks_asli.startswith('/'):
            return
            
        bot.reply_to(
            pesan, 
            "🤖 *Gw sekarang fokus jadi GymBot bro!*\n\n"
            "Kalau lu mau nyatet makanan, pake tombol *🍎 Kalori & Gula* di menu.\n"
            "Kalau mau nyatet latihan, ketik `/gym [laporan latihan lu]`.\n\n"
            "Ketik /start buat buka menu ya! 💪", 
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"[respon_pesan] fatal error: {e}")
        try: bot.reply_to(pesan, "❌ Ada error. Coba lagi ya bro.")
        except Exception: pass

@bot.message_handler(content_types=['photo'])
def handle_photo(pesan):
    user_id = str(pesan.from_user.id)
    
    if get_wizard_state(user_id, "waiting_food_photo"):
        proses_foto_makanan(pesan)
    elif get_wizard_state(user_id, "waiting_equipment_photo"):
        proses_foto_alat(pesan)
    else:
        bot.reply_to(pesan, "📸 Foto diterima. Kalau mau scan kalori, masuk ke menu 🍎 *Kalori & Gula*. Kalau mau scan alat gym, masuk ke *🔍 Scan Alat Gym*.", parse_mode='Markdown')