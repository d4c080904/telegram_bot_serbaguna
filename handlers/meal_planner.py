import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.queries import get_gym_profile, get_total_makro_hari_ini
from utils.helpers import hitung_bmr_tdee
from services.ai import rekomendasi_makanan

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "menu_meal_planner")
async def callback_meal_planner(callback: CallbackQuery):
    try:
        await callback.answer("⏳ Nyari resep buat lu...")
        user_id = str(callback.from_user.id)
        
        profil = await get_gym_profile(user_id)
        if not profil or not profil['berat']:
            await callback.message.answer("⚠️ Isi profil Gym lu dulu ya biar AI tau target lu!")
            return
            
        target = profil['target'] or 'recomp'
        batas_kalori = hitung_bmr_tdee(profil['umur'], profil['berat'], profil['tinggi'], profil['jenis_kelamin'] or 'L', target, profil['frekuensi'] or 3)
        
        target_protein = profil['berat'] * 2
        target_karbo = (batas_kalori * 0.4) / 4
        target_lemak = (batas_kalori * 0.25) / 9
        
        masuk_kalori, _ = await get_total_makro_hari_ini(user_id)
        sisa_kalori = batas_kalori - masuk_kalori
        
        sisa_protein = max(0, target_protein - (masuk_kalori * 0.3 / 4))
        sisa_karbo = max(0, target_karbo - (masuk_kalori * 0.4 / 4))
        sisa_lemak = max(0, target_lemak - (masuk_kalori * 0.25 / 9))
        
        if sisa_kalori <= 0:
            await callback.message.edit_text("⚠️ Kalori lu udah jebol bro! Mending minum air putih aja dulu, besok kita diet lagi.", parse_mode="HTML")
            return
            
        await callback.message.edit_text("⏳ <i>Chef AI lagi nyari resep yang pas sama sisa kalori lu...</i>", parse_mode="HTML")
        
        resep = await rekomendasi_makanan(sisa_kalori, int(sisa_protein), int(sisa_karbo), int(sisa_lemak), target)
        
        if resep:
            teks = f"🍳 <b>REKOMENDASI MAKANAN</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSisa kalori lu: <b>{sisa_kalori} kcal</b>\n\n{resep}"
            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 Kembali ke GYM MODE", callback_data="menu_gym_mode")
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await callback.message.edit_text("❌ AI-nya lagi bingung nyari resep. Coba lagi nanti ya.", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"meal_planner error: {e}")