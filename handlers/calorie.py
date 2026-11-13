import logging
import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import (
    get_gym_profile, get_total_makro_hari_ini, get_history_makanan_hari_ini, 
    hapus_log_terakhir, save_wizard_state, delete_wizard_state,
    tambah_workout_log, get_total_kalori_terbakar_hari_ini, get_history_workout_hari_ini
)
from utils.helpers import hitung_bmr_tdee
from services.meal_tracker import proses_foto_makanan_core
from services.adaptive_tdee import hitung_adaptive_tdee
from services.ai import estimasi_kalori_olahraga

logger = logging.getLogger(__name__)
router = Router()

HARI_INDONESIA = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
BULAN_INDONESIA = {'January': 'Januari', 'February': 'Februari', 'March': 'Maret', 'April': 'April', 'May': 'Mei', 'June': 'Juni', 'July': 'Juli', 'August': 'Agustus', 'September': 'September', 'October': 'Oktober', 'November': 'November', 'December': 'Desember'}
WIB_TZ = datetime.timezone(datetime.timedelta(hours=7))

class WorkoutState(StatesGroup):
    waiting_workout_text = State()

async def tampil_dashboard_kalori(chat_id, user_id, message_id=None, bot=None):
    profil = await get_gym_profile(user_id)
    
    if not profil or not profil['berat'] or not profil['tinggi']:
        teks = "⚠️ <b>Lu belum lengkap ngisi profil Gym!</b>\n\nBiar AI bisa ngitung kalori harian lu, isi dulu profil Gym lu ya."
        builder = InlineKeyboardBuilder()
        builder.button(text="💪 Ke Menu Gym", callback_data="menu_gym")
        if message_id: 
            await bot.edit_message_text(teks, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=builder.as_markup())
        else: 
            await bot.send_message(chat_id, teks, parse_mode="HTML", reply_markup=builder.as_markup())
        return

    target = profil['target'] or 'recomp'
    batas_kalori_statis = hitung_bmr_tdee(profil['umur'], profil['berat'], profil['tinggi'], profil['jenis_kelamin'] or 'L', target, profil['frekuensi'] or 3)
    batas_kalori, alasan_tdee = await hitung_adaptive_tdee(user_id, batas_kalori_statis, target, profil['berat'])
    batas_gula = 25 if target == 'cutting' else 50
    
    masuk_kalori, masuk_gula = await get_total_makro_hari_ini(user_id)
    terbakar_kalori = await get_total_kalori_terbakar_hari_ini(user_id)
    
    masuk_kalori = int(masuk_kalori)
    masuk_gula = round(float(masuk_gula), 1)
    
    net_kalori = masuk_kalori - terbakar_kalori
    sisa_kalori = batas_kalori - net_kalori
    sisa_gula = round(batas_gula - masuk_gula, 1)
    
    now = datetime.datetime.now(WIB_TZ)
    hari_id = HARI_INDONESIA.get(now.strftime("%A"), now.strftime("%A"))
    bulan_id = BULAN_INDONESIA.get(now.strftime("%B"), now.strftime("%B"))
    waktu_str = f"{hari_id}, {now.day} {bulan_id} {now.year} | {now.strftime('%H:%M')} WIB"
    
    icon_gula = "✅" if sisa_gula >= 0 else "🚨"
    
    info_tdee = ""
    if "Stagnan" in alasan_tdee or "naikkan" in alasan_tdee or "kurangi" in alasan_tdee:
        info_tdee = f"📉 <i>Auto-Adjust: {alasan_tdee}</i>\n"

    teks = (
        "🍎 <b>FOOD & SUGAR TRACKER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>{waktu_str}</b>\n"
        f"{info_tdee}\n"
        f"<b>KALORI</b>\n"
        f"🎯 Batas: {batas_kalori} kcal\n"
        f"🍽️ Masuk: {masuk_kalori} kcal\n"
        f"🏃‍♂️ Terbakar: {terbakar_kalori} kcal\n"
        f"🔥 Sisa Akhir: {sisa_kalori} kcal\n\n"
        f"<b>GULA (Target: {target.capitalize()})</b>\n"
        f"🎯 Batas: {batas_gula} g\n"
        f"🍭 Masuk: {masuk_gula} g\n"
        f"{icon_gula} Sisa: {sisa_gula} g\n\n"
        "Silakan pilih aksi di bawah:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📸 Foto Makanan", callback_data="kalori_foto")
    builder.button(text="📷 Scan Barcode", callback_data="menu_barcode")
    builder.button(text="🏃‍♂️ Catat Olahraga", callback_data="kalori_olahraga")
    builder.button(text="📝 Hapus Log Makanan", callback_data="kalori_hapus")
    builder.button(text="📊 Lihat History", callback_data="kalori_history")
    builder.button(text="🔙 Kembali ke Menu Utama", callback_data="menu_utama")
    
    builder.adjust(2, 1, 2, 1)
    
    try:
        if message_id: 
            await bot.edit_message_text(teks, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=builder.as_markup())
        else: 
            await bot.send_message(chat_id, teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"tampil_dashboard_kalori error: {e}")

@router.callback_query(F.data == "menu_kalori")
async def callback_menu_kalori(callback: CallbackQuery):
    try:
        await callback.answer()
        await tampil_dashboard_kalori(callback.message.chat.id, str(callback.from_user.id), callback.message.message_id, callback.bot)
    except Exception as e: logger.error(f"menu_kalori error: {e}")

@router.callback_query(F.data == "kalori_olahraga")
async def callback_kalori_olahraga(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await state.set_state(WorkoutState.waiting_workout_text)
        
        teks = "🏃‍♂️ <b>CATAT OLAHRAGA</b>\n\nSilakan ketik jenis olahraga dan durasinya.\n<i>Contoh: lari 30 menit, angkat beban 1 jam, sepeda 45 menit</i>"
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Batal", callback_data="menu_kalori")
        
        try: 
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception: 
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: logger.error(f"kalori_olahraga error: {e}")

@router.message(WorkoutState.waiting_workout_text)
async def proses_input_olahraga(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    teks_input = message.text.strip()
    
    if teks_input == '/cancel':
        await state.clear()
        await tampil_dashboard_kalori(message.chat.id, user_id, bot=message.bot)
        return
        
    await state.clear()
    pesan_tunggu = await message.reply("⏳ <i>AI lagi ngitung kalori yang lu bakar...</i>", parse_mode="HTML")
    
    try:
        profil = await get_gym_profile(user_id)
        berat = profil['berat'] if profil else 70
        
        hasil_ai = await estimasi_kalori_olahraga(teks_input, berat)
        
        if not hasil_ai:
            await pesan_tunggu.edit_text("❌ AI gagal memahami input olahraga lu. Coba format lain.")
            return
            
        olahraga = hasil_ai.get('olahraga', 'Olahraga')
        durasi = hasil_ai.get('durasi', 30)
        kalori = hasil_ai.get('kalori_terbakar', 200)
        
        berhasil = await tambah_workout_log(user_id, olahraga, durasi, kalori)
        
        if berhasil:
            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 Kembali ke Dashboard", callback_data="menu_kalori")
            
            await pesan_tunggu.edit_text(
                f"✅ <b>Olahraga Tercatat!</b>\n\n"
                f"🏃‍♂️ Jenis: <b>{olahraga}</b>\n"
                f"⏳ Durasi: <b>{durasi} menit</b>\n"
                f"🔥 Kalori Terbakar: <b>{kalori} kcal</b>\n\n"
                f"<i>Kalori ini udah otomatis ngurangin sisa kalori harian lu!</i>",
                parse_mode="HTML", reply_markup=builder.as_markup()
            )
            await tampil_dashboard_kalori(message.chat.id, user_id, bot=message.bot)
        else:
            await pesan_tunggu.edit_text("❌ Gagal menyimpan log olahraga ke database.")
            
    except Exception as e:
        logger.error(f"proses_input_olahraga error: {e}")
        await pesan_tunggu.edit_text("❌ Terjadi kesalahan sistem.")

@router.callback_query(F.data == "kalori_foto")
async def callback_kalori_foto(callback: CallbackQuery):
    try:
        await callback.answer()
        await save_wizard_state(str(callback.from_user.id), "waiting_food_photo", "waiting", {})
        
        teks = "📸 <b>Silakan kirim foto makanan lu sekarang.</b>\n\n<i>(Boleh tambahkan caption nama makanannya biar AI makin akurat)</i>"
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Batal", callback_data="menu_kalori")
        
        try: 
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception: 
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: logger.error(f"kalori_foto error: {e}")

@router.callback_query(F.data == "kalori_hapus")
async def callback_kalori_hapus(callback: CallbackQuery):
    try:
        user_id = str(callback.from_user.id)
        if await hapus_log_terakhir(user_id):
            await callback.answer("✅ Log makanan terakhir dihapus!", show_alert=True)
        else:
            await callback.answer("⚠️ Tidak ada log makanan hari ini.", show_alert=True)
        await tampil_dashboard_kalori(callback.message.chat.id, user_id, callback.message.message_id, callback.bot)
    except Exception as e: logger.error(f"kalori_hapus error: {e}")

@router.callback_query(F.data == "kalori_history")
async def callback_kalori_history(callback: CallbackQuery):
    try:
        await callback.answer()
        history_food = await get_history_makanan_hari_ini(str(callback.from_user.id))
        history_workout = await get_history_workout_hari_ini(str(callback.from_user.id))
        
        now = datetime.datetime.now(WIB_TZ)
        hari_id = HARI_INDONESIA.get(now.strftime("%A"), now.strftime("%A"))
        bulan_id = BULAN_INDONESIA.get(now.strftime("%B"), now.strftime("%B"))
        tanggal_str = f"{hari_id}, {now.day} {bulan_id} {now.year}"
        
        teks = f"📊 <b>HISTORY HARI INI</b>\n📅 <b>{tanggal_str}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        
        teks += "<b>🍽️ MAKANAN</b>\n"
        if not history_food:
            teks += "Belum ada makanan yang dicatat.\n"
        else:
            for i, row in enumerate(history_food, 1):
                gula = round(float(row['gula']), 1) if row['gula'] else 0.0
                teks += f"{i}. {row['nama_makanan']} ({row['kalori']} kcal | 🍭 {gula}g)\n"
                
        teks += "\n<b>🏃‍♂️ OLAHRAGA</b>\n"
        if not history_workout:
            teks += "Belum ada olahraga yang dicatat.\n"
        else:
            for i, row in enumerate(history_workout, 1):
                teks += f"{i}. {row['olahraga']} ({row['durasi']}mnt | 🔥 {row['kalori_terbakar']} kcal)\n"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Kembali", callback_data="menu_kalori")
        
        try: 
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception: 
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: logger.error(f"kalori_history error: {e}")

async def proses_foto_makanan(message: Message):
    user_id = str(message.from_user.id)
    await delete_wizard_state(user_id, "waiting_food_photo")
    
    await message.bot.send_chat_action(message.chat.id, 'typing')
    pesan_tunggu = await message.reply("⏳ <i>AI Ahli Gizi lagi menganalisis makanan & gulanya...</i>", parse_mode="HTML")
    
    try:
        file_id = message.photo[-1].file_id
        file_info = await message.bot.get_file(file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        image_bytes = downloaded_file.read()
        
        caption = message.caption or ""
        
        result = await proses_foto_makanan_core(
            user_id=user_id,
            image_bytes=image_bytes,
            caption=caption,
            message_id=pesan_tunggu.message_id,
            photo_message_id=message.message_id
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Kembali ke Menu Utama", callback_data="menu_utama") 
        
        if result["status"] == "duplicate":
            await pesan_tunggu.edit_text(
                "⚠️ <b>Foto Duplikat Terdeteksi!</b>\n\nFoto ini persis kayak yang udah lu kirim dan catat hari ini. Biar kalori lu nggak dobel, gw abaikan ya bro. 👍",
                parse_mode="HTML", reply_markup=builder.as_markup()
            )
            return
            
        if result["status"] == "ai_failed":
            await pesan_tunggu.edit_text("❌ AI gagal menganalisis foto. Coba kirim ulang dengan foto yang lebih jelas.", reply_markup=builder.as_markup())
            return
            
        if result["status"] == "db_failed":
            await pesan_tunggu.edit_text("❌ Gagal menyimpan data ke database.", reply_markup=builder.as_markup())
            return
            
        if result["status"] == "error":
            await pesan_tunggu.edit_text("❌ Terjadi kesalahan sistem saat memproses foto.", reply_markup=builder.as_markup())
            return
            
        hasil = result["data"]
        gula_hasil = round(float(hasil.get('gula', 0)), 1)

        teks_balasan = (
            f"✅ <b>Berhasil Dicatat!</b>\n\n"
            f"🍽️ Nama: <b>{hasil.get('nama_makanan')}</b>\n"
            f"🍛 Porsi: <b>{hasil.get('estimasi_porsi')}</b>\n"
            f"🔥 Kalori: <b>{hasil.get('kalori')} kcal</b>\n"
            f"🥩 Protein: <b>{hasil.get('protein')}g</b>\n"
            f"🍚 Karbo: <b>{hasil.get('karbo')}g</b>\n"
            f"🧈 Lemak: <b>{hasil.get('lemak')}g</b>\n"
            f"🍭 Gula: <b>{gula_hasil}g</b>\n"
        )
        await pesan_tunggu.edit_text(teks_balasan, parse_mode="HTML", reply_markup=builder.as_markup())
        await tampil_dashboard_kalori(message.chat.id, user_id, bot=message.bot)
        
    except Exception as e:
        logger.error(f"proses_foto_makanan error: {e}")
        await pesan_tunggu.edit_text("❌ Terjadi kesalahan saat memproses foto.")