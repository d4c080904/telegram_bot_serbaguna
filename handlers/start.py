import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.menus import (
    buat_menu_utama, teks_menu_utama, 
    tombol_kembali, buat_tombol_gender
)
from utils.state import set_onboarding_wizard, get_onboarding_wizard, clear_onboarding_wizard, clear_gym_wizard
from database.queries import get_user_profile, save_user_profile, get_total_air_hari_ini, get_berat_terakhir, set_chat_mode, cek_status_vip, get_statistik_user, get_user_full_stats
from database.db import get_db
from config import ADMIN_ID

logger = logging.getLogger(__name__)
router = Router()

# Pastiin URL ini sesuai sama URL ngrok lu
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

@router.message(Command("start", "menu"))
async def kirim_sambutan(message: Message, state: FSMContext):
    try:
        await state.clear()
        user_id = str(message.from_user.id)
        await set_chat_mode(user_id, False)
        await clear_gym_wizard(user_id)
        
        # 1. CEK VIP DULU (Mencegah user baru nyangkut di onboarding)
        is_vip_db = await cek_status_vip(user_id)
        is_admin = (user_id == str(ADMIN_ID))
        is_vip = is_vip_db or is_admin 

        if not is_vip:
            builder = InlineKeyboardBuilder()
            builder.button(text="🔓 Minta Izin Akses", callback_data="req_access")
            await message.answer(
                "🔒 <b>AKSES TERBATAS</b>\n\n"
                "Bot ini masih dalam tahap uji coba terbatas.\n"
                "Silakan minta izin akses ke Admin untuk bisa menggunakan bot ini.",
                reply_markup=builder.as_markup()
            )
            return

        # 2. JIKA VIP, BARU CEK PROFIL (ONBOARDING)
        user = await get_user_profile(user_id)
        
        if not user:
            await set_onboarding_wizard(user_id, 'nama', {})
            await message.answer("Halo bro! 👋 Sebelum mulai, kenalin diri lu dulu ya.\n\nSiapa <b>nama panggilan</b> lu?", parse_mode="HTML")
            return

        ringkasan = await buat_ringkasan_dashboard(user_id)
        teks = f"Halo <b>{user['nama']}</b>! 👋\n\n" + teks_menu_utama(ringkasan)
        await message.answer(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL, is_vip))
    except Exception as e:
        logger.error(f"[start] error: {e}")

@router.message(Command("help"))
async def cmd_help(message: Message):
    try:
        user_id = str(message.from_user.id)
        is_vip_db = await cek_status_vip(user_id)
        is_admin = (user_id == str(ADMIN_ID))
        is_vip = is_vip_db or is_admin

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
            "<code>/stats</code> — Lihat statistik lu\n"
            "<code>/myprogress</code> — Progres sepanjang masa\n"
            "<code>/cancel</code> — Batalin input yang lagi jalan"
        )
        
        builder = InlineKeyboardBuilder()
        if not is_vip:
            builder.button(text="🔓 Minta Izin Akses", callback_data="req_access")
        builder.button(text="🔙 Kembali ke Menu Utama", callback_data="menu_utama")
        
        await message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"[cmd_help] error: {e}")

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
        
        is_vip_db = await cek_status_vip(user_id)
        is_admin = (user_id == str(ADMIN_ID))
        is_vip = is_vip_db or is_admin

        if not is_vip:
            builder = InlineKeyboardBuilder()
            builder.button(text="🔓 Minta Izin Akses", callback_data="req_access")
            teks = f"✅ Mantap! Data lu udah disimpen.\n\nTapi untuk masuk, lu harus minta izin Admin dulu."
            await callback.message.edit_text(teks, reply_markup=builder.as_markup())
            return

        teks = f"✅ Mantap! Data lu udah disimpen.\n\nHalo <b>{data['nama']}</b>! 👋\n\n" + teks_menu_utama(ringkasan)
        
        try:
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL, is_vip))
        except Exception:
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL, is_vip))
            
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
        
        is_vip_db = await cek_status_vip(user_id)
        is_admin = (user_id == str(ADMIN_ID))
        is_vip = is_vip_db or is_admin

        teks = f"Halo <b>{nama}</b>! 👋\n\n" + teks_menu_utama(ringkasan)
        
        try: 
            await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL, is_vip))
        except Exception: 
            await callback.message.answer(teks, parse_mode="HTML", reply_markup=buat_menu_utama(user_id, WEBAPP_URL, is_vip))
    except Exception as e:
        logger.error(f"[menu_utama] error: {e}")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    try:
        user_id = str(message.from_user.id)
        stats = await get_statistik_user(user_id)
        
        teks = (
            "📊 <b>STATISTIK GYM LU</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🍎 Log Makanan: <b>{stats['makanan']} kali</b>\n"
            f"💧 Log Air Minum: <b>{stats['air']} kali</b>\n"
            f"💪 Log Latihan: <b>{stats['gym']} kali</b>\n\n"
            "<i>Terus pakai bot ini biar badan makin gede!</i> 🚀"
        )
        await message.answer(teks, parse_mode="HTML", reply_markup=tombol_kembali())
    except Exception as e:
        logger.error(f"[cmd_stats] error: {e}")

@router.message(Command("myprogress"))
async def cmd_myprogress(message: Message):
    try:
        import datetime
        user_id = str(message.from_user.id)
        stats = await get_user_full_stats(user_id)
        
        if not stats or stats['days_active'] == 0:
            await message.answer(
                "📊 <b>Belum ada data progres</b>\n\n"
                "Mulai catat makanan, air minum, atau latihan dulu ya.\n"
                "Gunakan tombol di menu utama.",
                parse_mode="HTML",
                reply_markup=tombol_kembali()
            )
            return
        
        weight_str = "Belum ada data"
        if stats['first_weight'] and stats['last_weight']:
            diff = stats['last_weight'] - stats['first_weight']
            if diff > 0:
                weight_str = f"{stats['first_weight']} → {stats['last_weight']} kg (🔴 +{diff:.1f} kg)"
            elif diff < 0:
                weight_str = f"{stats['first_weight']} → {stats['last_weight']} kg (🟢 {diff:.1f} kg)"
            else:
                weight_str = f"{stats['first_weight']} → {stats['last_weight']} kg (⚪ Stabil)"
        elif stats['last_weight']:
            weight_str = f"{stats['last_weight']} kg"
            
        teks = (
            "📊 <b>PROGRES LU SEJAUH INI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 Aktif sejak: <b>{stats['first_date']}</b>\n"
            f"⏱️ Total hari aktif: <b>{stats['days_active']} hari</b>\n\n"
            f"🍽️ <b>MAKANAN</b>\n"
            f"   • Dicatat: <b>{stats['total_food']} kali</b>\n"
            f"   • Total kalori: <b>{stats['total_kalori']:,} kcal</b>\n\n"
            f"💧 <b>AIR MINUM</b>\n"
            f"   • Dicatat: <b>{stats['total_water']} kali</b>\n"
            f"   • Total air: <b>{stats['total_water_ml']:,} ml</b>\n\n"
            f"🏋️ <b>LATIHAN</b>\n"
            f"   • Dicatat: <b>{stats['total_workout']} kali</b>\n"
            f"   • Total kalori terbakar: <b>{stats['total_burned']:,} kcal</b>\n\n"
            f"⚖️ <b>BERAT BADAN</b>\n"
            f"   • {weight_str}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Terus konsisten ya bro! 💪"
        )
        
        await message.answer(teks, parse_mode="HTML", reply_markup=tombol_kembali())
    except Exception as e:
        logger.error(f"[cmd_myprogress] error: {e}")
        await message.answer("❌ Gagal ambil data progres. Coba lagi nanti.")

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    try:
        await state.clear()
        await message.answer(
            "✅ Aksi berhasil dibatalkan.\nKetik /start atau klik tombol di bawah untuk kembali ke menu utama.",
            reply_markup=tombol_kembali()
        )
    except Exception as e:
        logger.error(f"[cmd_cancel] error: {e}")

@router.callback_query(F.data == "menu_stats")
async def callback_menu_stats(callback: CallbackQuery):
    try:
        user_id = str(callback.from_user.id)
        stats = await get_statistik_user(user_id)

        await callback.answer()
        teks = (
            "📊 <b>STATISTIK GYM LU</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🍎 Log Makanan: <b>{stats['makanan']} kali</b>\n"
            f"💧 Log Air Minum: <b>{stats['air']} kali</b>\n"
            f"💪 Log Latihan: <b>{stats['gym']} kali</b>\n\n"
            "<i>Terus pakai bot ini biar badan makin gede!</i> 🚀"
        )
        try: await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=tombol_kembali())
        except Exception: await callback.message.answer(teks, parse_mode="HTML", reply_markup=tombol_kembali())
    except Exception as e: logger.error(f"[menu_stats] error: {e}")

@router.callback_query(F.data == "menu_help")
async def callback_menu_help(callback: CallbackQuery):
    try:
        await callback.answer()
        user_id = str(callback.from_user.id)
        is_vip_db = await cek_status_vip(user_id)
        is_admin = (user_id == str(ADMIN_ID))
        is_vip = is_vip_db or is_admin

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
            "<code>/stats</code> — Lihat statistik lu\n"
            "<code>/myprogress</code> — Progres sepanjang masa\n"
            "<code>/cancel</code> — Batalin input yang lagi jalan"
        )
        
        builder = InlineKeyboardBuilder()
        if not is_vip:
            builder.button(text="🔓 Minta Izin Akses", callback_data="req_access")
        builder.button(text="🔙 Kembali ke Menu Utama", callback_data="menu_utama")
        
        try: await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception: await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: logger.error(f"[menu_help] error: {e}")