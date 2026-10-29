from bot_instance import bot
from telebot import types
from database.queries import get_gym_profile, get_total_makro_hari_ini
from utils.helpers import hitung_bmr_tdee
from services.ai import rekomendasi_makanan
import logging

logger = logging.getLogger(__name__)

@bot.callback_query_handler(func=lambda call: call.data == "menu_meal_planner")
def callback_meal_planner(call):
    try:
        bot.answer_callback_query(call.id, "⏳ Nyari resep buat lu...")
        user_id = call.from_user.id
        
        profil = get_gym_profile(user_id)
        if not profil or not profil['berat']:
            bot.send_message(call.message.chat.id, "⚠️ Isi profil Gym lu dulu ya biar AI tau target lu!")
            return
            
        target = profil['target'] or 'recomp'
        batas_kalori = hitung_bmr_tdee(profil['umur'], profil['berat'], profil['tinggi'], profil['jenis_kelamin'] or 'L', target, profil['frekuensi'] or 3)
        
        target_protein = profil['berat'] * 2
        target_karbo = (batas_kalori * 0.4) / 4
        target_lemak = (batas_kalori * 0.25) / 9
        
        masuk_kalori, _ = get_total_makro_hari_ini(user_id)
        sisa_kalori = batas_kalori - masuk_kalori
        
        sisa_protein = max(0, target_protein - (masuk_kalori * 0.3 / 4))
        sisa_karbo = max(0, target_karbo - (masuk_kalori * 0.4 / 4))
        sisa_lemak = max(0, target_lemak - (masuk_kalori * 0.25 / 9))
        
        if sisa_kalori <= 0:
            bot.edit_message_text("⚠️ Kalori lu udah jebol bro! Mending minum air putih aja dulu, besok kita diet lagi.", call.message.chat.id, call.message.message_id)
            return
            
        bot.edit_message_text("⏳ _Chef AI lagi nyari resep yang pas sama sisa kalori lu..._", call.message.chat.id, call.message.message_id)
        
        resep = rekomendasi_makanan(sisa_kalori, int(sisa_protein), int(sisa_karbo), int(sisa_lemak), target)
        
        if resep:
            teks = f"🍳 *REKOMENDASI MAKANAN*\n━━━━━━━━━━━━━━━━━━━━\n\nSisa kalori lu: *{sisa_kalori} kcal*\n\n{resep}"
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Kembali ke GYM MODE", callback_data="menu_gym_mode")) # <--- DIUBAH
            bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.edit_message_text("❌ AI-nya lagi bingung nyari resep. Coba lagi nanti ya.", call.message.chat.id, call.message.message_id)
            
    except Exception as e:
        logger.error(f"meal_planner error: {e}")