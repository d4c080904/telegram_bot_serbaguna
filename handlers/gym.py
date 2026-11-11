import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import get_gym_profile, save_gym_profile
from database.db import get_db
from services.ai import analisis_gym_noob, analisis_gym_pro, MODEL_GROQ_LIST
from utils.helpers import hitung_bmi, kategori_bmi, strip_markdown
from utils.state import set_gym_wizard, get_gym_wizard, clear_gym_wizard
from bot_instance import groq_client

logger = logging.getLogger(__name__)
router = Router()

async def tampil_menu_gym(chat_id, user_id, message_id=None, bot=None):
    profil = await get_gym_profile(user_id)
    
    if profil:
        nama = profil.get('nama') or "Bro"
        data_text = f"{profil.get('umur') or '-'}th, {profil.get('berat') or '-'}kg, {profil.get('tinggi') or '-'}cm"
    else:
        nama = "Bro"
        data_text = "Belum diisi"
        
    teks = (
        f"💪 <b>ASISTEN GYM PRIBADI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Halo <b>{nama}</b>!\n"
        f"Data saat ini: {data_text}\n\n"
        "Pilih mode program latihan lu:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 Mode Baru Gym", callback_data="gym_noob_start")
    builder.button(text="💪 Mode Pro Gym", callback_data="gym_pro_start")
    builder.button(text="📊 Profil Saya", callback_data="gym_view_profile")
    builder.button(text="📝 Log Latihan", callback_data="gym_log_info")
    builder.button(text="🔙 Kembali ke MENU UTAMA", callback_data="menu_utama") # <--- BALIK KE BERANDA
    builder.adjust(2, 2, 1)
    
    try:
        if message_id:
            await bot.edit_message_text(teks, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await bot.send_message(chat_id, teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"tampil_menu_gym error: {e}")

@router.callback_query(F.data == "menu_gym_mode")
async def callback_menu_gym_mode(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.answer()
        await tampil_menu_gym(callback.message.chat.id, str(callback.from_user.id), callback.message.message_id, callback.bot)
    except Exception as e:
        logger.error(f"[menu_gym_mode] error: {e}")

async def tampil_profil_gym(chat_id, user_id, message_id=None, bot=None):
    profil = await get_gym_profile(user_id)
    
    if not profil:
        teks = "⚠️ <b>Lu belum punya profil Gym.</b>\n\nIsi profil dulu di menu awal ya."
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Kembali", callback_data="menu_gym_mode")
        try:
            if message_id: await bot.edit_message_text(teks, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=builder.as_markup())
            else: await bot.send_message(chat_id, teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception: pass
        return
        
    bmi = hitung_bmi(profil.get('berat'), profil.get('tinggi'))
    kategori = kategori_bmi(bmi)
    mode_label = "🆕 Baru Gym" if profil.get('mode') == 'noob' else "💪 Pro Gym"
    
    teks = (
        f"📊 <b>PROFIL GYM LU</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Mode: <b>{mode_label}</b>\n\n"
        f"👤 Umur: <b>{profil.get('umur') or 'N/A'}</b> tahun\n"
        f"⚖️ Berat: <b>{profil.get('berat') or 'N/A'}</b> kg\n"
        f"📏 Tinggi: <b>{profil.get('tinggi') or 'N/A'}</b> cm\n"
        f"📈 BMI: <b>{bmi or 'N/A'}</b> ({kategori})\n"
    )
    
    if profil.get('mode') == 'pro':
        teks += (
            f"\n🎯 Target: <b>{profil.get('target') or 'N/A'}</b>\n"
            f"🎓 Level: <b>{profil.get('level') or 'N/A'}</b>\n"
            f"⏳ Pengalaman: <b>{profil.get('pengalaman') or 'N/A'}</b> tahun\n"
            f"📅 Frekuensi: <b>{profil.get('frekuensi') or 'N/A'}</b>x/minggu\n"
            f"🏋️ Alat: <b>{profil.get('alat') or 'N/A'}</b>\n"
        )
        
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Daftar Ulang", callback_data=f"gym_{profil.get('mode')}_start")
    builder.button(text="📝 Log Latihan", callback_data="gym_log_info")
    builder.button(text="🔙 Menu Gym", callback_data="menu_gym_mode")
    builder.adjust(2, 1)
    
    try:
        if message_id: await bot.edit_message_text(teks, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=builder.as_markup())
        else: await bot.send_message(chat_id, teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: logger.error(f"tampil_profil_gym error: {e}")

@router.message(Command("gym"))
async def handler_gym(message: Message):
    try:
        user_id = str(message.from_user.id)
        teks_perintah = message.text.replace("/gym", "").strip()
        
        if not teks_perintah:
            await tampil_menu_gym(message.chat.id, user_id, bot=message.bot)
            return
            
        profil = await get_gym_profile(user_id)
        if not profil:
            await message.reply("⚠️ Lu belum punya profil Gym nih.\n\nBikin dulu dengan ketik /gym (tanpa teks).", parse_mode="HTML")
            return
            
        async with await get_db() as conn:
            await conn.execute("INSERT INTO gym_logs (user_id, log_teks) VALUES ($1, $2)", user_id, teks_perintah)
        
        await message.bot.send_chat_action(message.chat.id, 'typing')
        pesan_tunggu = await message.reply("⏳ <i>PT AI lu lagi evaluasi...</i>", parse_mode="HTML")
        
        mode = profil.get('mode')
        if mode == 'noob':
            system_prompt = (
                f"Kamu adalah asisten gym ramah untuk pemula. "
                f"Klien: umur {profil.get('umur')}th, BB {profil.get('berat')}kg, TB {profil.get('tinggi')}cm. "
                f"Evaluasi laporan latihan/makan dia dengan bahasa sederhana & motivasi. "
                f"JANGAN pakai markdown (** atau * atau `). Tulis teks polos aja."
            )
        else:
            system_prompt = (
                f"Kamu adalah personal trainer elite untuk klien berpengalaman. "
                f"Klien: umur {profil.get('umur')}th, BB {profil.get('berat')}kg, TB {profil.get('tinggi')}cm, "
                f"target {profil.get('target')}, level {profil.get('level')}, "
                f"frekuensi {profil.get('frekuensi')}x/minggu, alat {profil.get('alat')}. "
                f"Evaluasi laporan dia dengan detail teknis. "
                f"JANGAN pakai markdown (** atau * atau `). Tulis teks polos aja."
            )
            
        hasil = None
        for model_name in MODEL_GROQ_LIST:
            try:
                response = await groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": teks_perintah}
                    ],
                    model=model_name,
                    temperature=0.7,
                    max_tokens=1024,
                    frequency_penalty=0.5,
                    presence_penalty=0.5
                )
                hasil = response.choices[0].message.content.strip()
                if hasil: break
            except Exception as e:
                logger.warning(f"Model {model_name} gagal (gym log): {e}")
                continue
                
        if hasil:
            try: await pesan_tunggu.edit_text(hasil)
            except Exception: await pesan_tunggu.edit_text(strip_markdown(hasil))
        else:
            await pesan_tunggu.edit_text("❌ AI lagi error nih bro. Coba lagi bentar ya.")
            
    except Exception as e:
        logger.error(f"[gym] error: {e}")
        try: await message.reply("❌ Ada error di fitur gym. Coba lagi nanti.")
        except Exception: pass

async def proses_gym_wizard(message: Message, wizard: dict):
    user_id = str(message.from_user.id)
    teks = message.text.strip()
    mode = wizard.get('mode')
    
    if mode == 'pro':
        parts = [p.strip().lower() for p in teks.split('|')]
        if len(parts) != 5:
            await message.reply("❌ Format salah bro.\n\nKirim pakai format:\n<code>target | level | pengalaman | frekuensi | alat</code>\n\nContoh:\n<code>cutting | intermediate | 3 | 5 | gym_full</code>", parse_mode="HTML")
            return
        try:
            target = parts[0]
            level = parts[1]
            pengalaman = int(parts[2])
            frekuensi = int(parts[3])
            alat = parts[4]
        except ValueError:
            await message.reply("❌ Ada format yang salah. Coba lagi.")
            return
            
        if target not in ('bulking', 'cutting', 'recomp', 'strength') or level not in ('beginner', 'intermediate', 'advanced') or alat not in ('gym_full', 'home_dumbbell', 'home_barbell', 'bodyweight'):
            await message.reply("❌ Pilihan teks salah. Cek lagi formatnya.")
            return
            
        data_pro = {'mode': 'pro', 'target': target, 'level': level, 'pengalaman': pengalaman, 'frekuensi': frekuensi, 'alat': alat}
        await save_gym_profile(user_id, data_pro)
        await clear_gym_wizard(user_id)
        
        profil = await get_gym_profile(user_id)
        if not profil:
            await message.reply("❌ Gagal ambil data profil.")
            return
            
        await message.reply("✅ Data program Pro disimpan!\n\n⏳ <i>AI lagi nyiapin analisis advanced...</i>", parse_mode="HTML")
        await message.bot.send_chat_action(message.chat.id, 'typing')
        
        data_pro.update({'umur': profil.get('umur'), 'berat': profil.get('berat'), 'tinggi': profil.get('tinggi'), 'jenis_kelamin': profil.get('jenis_kelamin')})
        hasil = await analisis_gym_pro(data_pro)
        
        if hasil:
            try: await message.answer(hasil, parse_mode="HTML")
            except Exception: await message.answer(strip_markdown(hasil))
        else:
            await message.answer("❌ AI-nya lagi error. Coba lagi nanti ya.")
            
        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Log Latihan", callback_data="gym_log_info")
        builder.button(text="📊 Profil Saya", callback_data="gym_view_profile")
        builder.button(text="🔙 Menu Gym", callback_data="menu_gym_mode")
        builder.adjust(2, 1)
        await message.answer("👇 Selanjutnya lu bisa:", reply_markup=builder.as_markup())
        return

@router.callback_query(F.data == "menu_gym")
async def callback_menu_gym(callback: CallbackQuery):
    try:
        await callback.answer()
        await clear_gym_wizard(str(callback.from_user.id))
        await tampil_menu_gym(callback.message.chat.id, str(callback.from_user.id), callback.message.message_id, callback.bot)
    except Exception as e: logger.error(f"[menu_gym] error: {e}")

@router.callback_query(F.data == "gym_noob_start")
async def callback_gym_noob_start(callback: CallbackQuery):
    try:
        user_id = str(callback.from_user.id)
        await callback.answer("⏳ Nyiapin panduan...")
        
        profil = await get_gym_profile(user_id)
        if not profil:
            await callback.message.answer("⚠️ Lu belum isi profil di awal. Ketik /start dulu ya.")
            return
            
        await save_gym_profile(user_id, {'mode': 'noob', 'target': 'recomp'})
        
        await callback.message.edit_text("⏳ <i>AI lagi nyiapin panduan buat lu...</i>", parse_mode="HTML")
        await callback.bot.send_chat_action(callback.message.chat.id, 'typing')
        
        hasil = await analisis_gym_noob(profil.get('umur'), profil.get('berat'), profil.get('tinggi'))
        
        if hasil:
            try: await callback.message.answer(hasil, parse_mode="HTML")
            except Exception: await callback.message.answer(strip_markdown(hasil))
        else:
            await callback.message.answer("❌ AI error. Coba lagi.")
            
        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Log Latihan", callback_data="gym_log_info")
        builder.button(text="📊 Profil Saya", callback_data="gym_view_profile")
        builder.button(text="🔙 Menu Gym", callback_data="menu_gym_mode")
        builder.adjust(2, 1)
        await callback.message.answer("👇 Selanjutnya lu bisa:", reply_markup=builder.as_markup())
        
    except Exception as e: logger.error(f"[gym_noob] error: {e}")

@router.callback_query(F.data == "gym_pro_start")
async def callback_gym_pro_start(callback: CallbackQuery):
    try:
        await set_gym_wizard(str(callback.from_user.id), 'pro', 'input_data')
        await callback.answer("💪 Mode Pro Gym!")
        teks = (
            "💪 <b>MODE PRO GYM</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Kirim data program lu dalam 1 baris:\n\n"
            "📌 <b>Format:</b>\n"
            "<code>target | level | pengalaman | frekuensi | alat</code>\n\n"
            "📌 <b>Contoh:</b>\n"
            "<code>cutting | intermediate | 3 | 5 | gym_full</code>\n\n"
            "Gass kirim datanya! 👇\n\n"
            "<i>Ketik /cancel kalau mau batal</i>"
        )
        try: await callback.message.edit_text(teks, parse_mode="HTML")
        except Exception: await callback.message.answer(teks, parse_mode="HTML")
    except Exception as e: logger.error(f"[gym_pro] error: {e}")

@router.callback_query(F.data == "gym_view_profile")
async def callback_gym_view_profile(callback: CallbackQuery):
    try:
        await callback.answer()
        await tampil_profil_gym(callback.message.chat.id, str(callback.from_user.id), callback.message.message_id, callback.bot)
    except Exception as e: logger.error(f"[gym_view_profile] error: {e}")

@router.callback_query(F.data == "gym_log_info")
async def callback_gym_log_info(callback: CallbackQuery):
    try:
        await callback.answer()
        teks = (
            "📝 <b>LOG LATIHAN & MAKAN</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Kirim laporan lu dengan ketik:\n\n"
            "<code>/gym [laporan]</code>\n\n"
            "<b>Contoh:</b>\n"
            "<code>/gym hari ini latihan dada, bench 60kg 4x10</code>\n\n"
            "AI bakal evaluasi & kasih saran sesuai profil lu. 🔥"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Menu Gym", callback_data="menu_gym_mode")
        try: await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
        except Exception: await callback.message.answer(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: logger.error(f"[gym_log_info] error: {e}")