import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.menus import (
    buat_menu_utama, teks_menu_utama, 
    tombol_kembali, buat_tombol_gender
)
from utils.state import set_onboarding_wizard, get_onboarding_wizard, clear_onboarding_wizard, clear_gym_wizard
from database.queries import get_user_profile, save_user_profile, get_total_air_hari_ini, get_berat_terakhir, set_chat_mode
from database.db import get_db

logger = logging.getLogger(__name__)
router = Router()

# LINK NGROK LU GW HARDCODE DI SINI
WEBAPP_URL = "https://fifth-twiddle-richly.ngrok-free.dev"

async def buat_ringkasan_dashboard(user_id):
    air = await get_total_air_hari_ini(user_id)
    target_air = 2000
    persen = min((air / target_air) * 100, 100)
    
    bar_length = 10
    filled = int(bar_length * persen / 100)
    bar = "🟦" * filled + "⬜" * (bar_length - filled)
    
    berat_data = await get_berat_terakhir(user_id)
    berat_str = f"{berat_data[0]['berat']} kg" if berat_data else "Belum diisi"
    
    return (
        "📊 <b>RINGKASAN HARI INI:</b>\n"
        f"💧 Air: {bar} {int(persen)}% ({air}/{target_air} ml)\n"
        f"⚖️ Berat: {berat_str}\n"
    )

@router.message(Command("start", "help", "menu"))
async def kirim_sambutan(message: Message, state: FSMContext):
    try:
        await state.clear()
        user_id = str(message.from_user.id)
        await set_chat_mode(user_id, False)
        await clear_gym_wizard(user_id)
        
        user = await get_user_profile(user_id)
        
        if not user:
            await set_onboarding_wizard(user_id, 'nama', {})
            await message.answer("Halo bro! 👋 Sebelum mulai, kenalin diri lu dulu ya.\n\nSiapa <b>nama panggilan</b> lu?", parse_mode="HTML")
            return
            
        ringkasan = await buat_ringkasan_dashboard(user_id)
        teks = f"Halo <b>{user['nama']}</b>! 👋\n\n" + teks_menu_utama(ringkasan)
        await message.answer(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL))
    except Exception as e:
        logger.error(f"[start] error: {e}")

async def proses_onboarding(message: Message, wizard: dict):
    user_id = str(message.from_user.id)
    step = wizard['step']
    data = wizard['data']
    teks = message.text.strip()
    
    if step == 'nama':
        data['nama'] = teks
        await set_onboarding_wizard(user_id, 'umur', data)
        await message.answer(f"Oke <b>{teks}</b>! Umur lu berapa tahun? (Ketik angka aja)", parse_mode="HTML")
    elif step == 'umur':
        try:
            umur = int(teks)
            if umur < 10 or umur > 100:
                await message.answer("Umur harus antara 10-100 ya.")
                return
            data['umur'] = umur
            await set_onboarding_wizard(user_id, 'berat', data)
            await message.answer("Berat badan lu berapa kg? (Contoh: 65.5)")
        except ValueError:
            await message.answer("Tolong ketik angka aja ya.")
    elif step == 'berat':
        try:
            berat = float(teks.replace(',', '.'))
            data['berat'] = berat
            await set_onboarding_wizard(user_id, 'tinggi', data)
            await message.answer("Tinggi badan lu berapa cm? (Contoh: 170)")
        except ValueError:
            await message.answer("Tolong ketik angka aja ya.")
    elif step == 'tinggi':
        try:
            tinggi = float(teks.replace(',', '.'))
            data['tinggi'] = tinggi
            await set_onboarding_wizard(user_id, 'gender', data)
            await message.answer("Terakhir nih, jenis kelamin lu apa? Pencet tombol di bawah ya 👇", reply_markup=buat_tombol_gender())
        except ValueError:
            await message.answer("Tolong ketik angka aja ya.")

@router.callback_query(F.data.startswith("onboard_gender_"))
async def callback_gender(callback: CallbackQuery):
    try:
        await callback.answer()
        user_id = str(callback.from_user.id)
        wizard = await get_onboarding_wizard(user_id)
        
        if not wizard or wizard['step'] != 'gender':
            await callback.message.answer("Sesi onboarding lu udah berakhir. Ketik /start lagi ya.")
            return
            
        data = wizard['data']
        gender = "L" if callback.data == "onboard_gender_L" else "P"
        
        await save_user_profile(user_id, data['nama'], data['umur'], data['berat'], data['tinggi'], gender)
        await clear_onboarding_wizard(user_id)
        
        ringkasan = await buat_ringkasan_dashboard(user_id)
        teks = f"✅ Mantap! Data lu udah disimpen.\n\nHalo <b>{data['nama']}</b>! 👋\n\n" + teks_menu_utama(ringkasan)
        
        try:
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL))
        except Exception:
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL))
            
    except Exception as e:
        logger.error(f"[callback_gender] error: {e}")

@router.callback_query(F.data == "menu_utama")
async def callback_menu_utama(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.answer()
        user_id = str(callback.from_user.id)
        await set_chat_mode(user_id, False)
        await clear_gym_wizard(user_id)
        
        user = await get_user_profile(user_id)
        nama = user['nama'] if user else "Bro"
        
        ringkasan = await buat_ringkasan_dashboard(user_id)
        teks = f"Halo <b>{nama}</b>! 👋\n\n" + teks_menu_utama(ringkasan)
        
        try: 
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL))
        except Exception: 
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL))
    except Exception as e:
        logger.error(f"[menu_utama] error: {e}")

@router.callback_query(F.data == "menu_stats")
async def callback_menu_stats(callback: CallbackQuery):
    try:
        user_id = str(callback.from_user.id)
        async with await get_db() as conn:
            jumlah_makan = await conn.fetchval("SELECT COUNT(*) FROM food_logs WHERE user_id = $1", user_id)
            jumlah_air = await conn.fetchval("SELECT COUNT(*) FROM water_logs WHERE user_id = $1", user_id)
            jumlah_gym = await conn.fetchval("SELECT COUNT(*) FROM gym_logs WHERE user_id = $1", user_id)

        await callback.answer()
        teks = (
            "📊 <b>STATISTIK GYM LU</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🍎 Log Makanan: <b>{jumlah_makan} kali</b>\n"
            f"💧 Log Air Minum: <b>{jumlah_air} kali</b>\n"
            f"💪 Log Latihan: <b>{jumlah_gym} kali</b>\n\n"
            "<i>Terus pakai bot ini biar badan makin gede!</i> 🚀"
        )
        try: await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=tombol_kembali())
        except Exception: await callback.message.answer(teks, parse_mode="HTML", reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_stats] error: {e}")

@router.callback_query(F.data == "menu_help")
async def callback_menu_help(callback: CallbackQuery):
    try:
        await callback.answer()
        teks = (
            "❓ <b>BANTUAN & PANDUAN GYMBOT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🍎 Kalori & Gula</b>\n→ Foto makanan buat hitung kalori otomatis.\n→ Bisa reply pesan hasil foto buat koreksi porsi.\n\n"
            "<b>💧 Progress & Air</b>\n→ Catat minum air & berat badan harian.\n\n"
            "<b>💪 Program Gym</b>\n→ Bikin program latihan (Noob/Pro).\n→ Catat log latihan harian.\n\n"
            "<b>💬 Chat PT AI</b>\n→ Tanya jawab seputar gym & nutrisi layaknya punya PT pribadi.\n\n"
            "<b>🔍 Scan Alat</b>\n→ Foto alat gym buat tau cara pakenya.\n\n"
            "<b>🍳 Meal Planner</b>\n→ Rekomendasi resep sesuai sisa kalori lu.\n\n"
            "<b>⚙️ Command Lain:</b>\n"
            "<code>/start</code> — Buka menu utama\n"
            "<code>/gym</code> — Langsung ke menu program gym\n"
            "<code>/cancel</code> — Batalin input yang lagi jalan"
        )
        try: await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=tombol_kembali())
        except Exception: await callback.message.answer(teks, parse_mode="HTML", reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_help] error: {e}")