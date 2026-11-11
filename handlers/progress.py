import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.queries import get_total_air_hari_ini, get_berat_terakhir, tambah_air, update_user_weight

logger = logging.getLogger(__name__)
router = Router()
BATAS_AIR_HARIAN = 2000

class ProgressState(StatesGroup):
    waiting_weight = State()

async def tampil_dashboard_progress(chat_id, user_id, message_id=None, bot=None):
    total_air = await get_total_air_hari_ini(user_id)
    sisa_air = BATAS_AIR_HARIAN - total_air
    
    persen = (total_air / BATAS_AIR_HARIAN) * 100
    if persen > 100: persen = 100
    bar_length = 10
    filled = int(bar_length * persen / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    berat_data = await get_berat_terakhir(user_id)
    if not berat_data:
        teks_berat = "⚖️ <b>Berat Badan:</b> Belum ada data."
    elif len(berat_data) == 1:
        teks_berat = f"⚖️ <b>Berat Badan Terakhir:</b> {berat_data[0]['berat']} kg"
    else:
        curr_berat = berat_data[0]['berat']
        prev_berat = berat_data[1]['berat']
        selisih = curr_berat - prev_berat
        
        if selisih > 0: status = f"🔴 Naik {selisih:.1f} kg"
        elif selisih < 0: status = f"🟢 Turun {abs(selisih):.1f} kg"
        else: status = "⚪ Stabil"
            
        teks_berat = f"⚖️ <b>Berat Badan Terakhir:</b> {curr_berat} kg ({status})"

    teks = (
        "📈 <b>PROGRESS & HYDRATION</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💧 <b>WATER TRACKER</b>\n"
        f"🎯 Target: {BATAS_AIR_HARIAN} ml\n"
        f"💦 Sudah Minum: <b>{total_air} ml</b>\n"
        f"📊 Progress: [{bar}] {int(persen)}%\n"
    )
    
    if sisa_air > 0:
        teks += f"⚠️ Kurang <b>{sisa_air} ml</b> lagi bro!\n\n"
    else:
        teks += "✅ <b>Hidrasi Hari Ini Tercukupi!</b> Mantap! 🔥\n\n"
        
    teks += f"{teks_berat}\n\n"
    teks += "Pilih aksi di bawah:"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💧 Minum 250ml", callback_data="water_250")
    builder.button(text="💧 Minum 500ml", callback_data="water_500")
    builder.button(text="🚰 Minum 1 Liter", callback_data="water_1000")
    builder.button(text="⚖️ Catat Berat Badan", callback_data="input_berat")
    builder.button(text="🔙 Kembali ke Menu Utama", callback_data="menu_utama") # <--- BALIK KE BERANDA
    builder.adjust(2, 1, 1, 1)
    
    try:
        if message_id: 
            await bot.edit_message_text(teks, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=builder.as_markup())
        else: 
            await bot.send_message(chat_id, teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"tampil_dashboard_progress error: {e}")

@router.callback_query(F.data == "menu_progress")
async def callback_menu_progress(callback: CallbackQuery):
    try:
        await callback.answer()
        await tampil_dashboard_progress(callback.message.chat.id, str(callback.from_user.id), callback.message.message_id, callback.bot)
    except Exception as e: logger.error(f"menu_progress error: {e}")

@router.callback_query(F.data.startswith("water_"))
async def callback_tambah_air(callback: CallbackQuery):
    try:
        ml = int(callback.data.split("_")[1])
        if await tambah_air(str(callback.from_user.id), ml):
            await callback.answer(f"✅ +{ml}ml air berhasil dicatat!", show_alert=False)
            await tampil_dashboard_progress(callback.message.chat.id, str(callback.from_user.id), callback.message.message_id, callback.bot)
        else:
            await callback.answer("❌ Gagal mencatat air.", show_alert=True)
    except Exception as e: logger.error(f"tambah_air error: {e}")

@router.callback_query(F.data == "input_berat")
async def callback_input_berat(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await state.set_state(ProgressState.waiting_weight)
        
        teks = "⚖️ <b>Catat Berat Badan</b>\n\nSilakan ketik berat badan lu saat ini (dalam kg).\n<i>Contoh: 65.5</i>\n\n<i>Ketik /cancel kalau mau batal</i>"
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Batal", callback_data="menu_progress")
        
        await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception as e: logger.error(f"input_berat error: {e}")

@router.message(ProgressState.waiting_weight)
async def proses_input_berat(message: Message, state: FSMContext):
    if message.text == '/cancel':
        await state.clear()
        await tampil_dashboard_progress(message.chat.id, str(message.from_user.id), bot=message.bot)
        return
        
    try:
        berat_baru = float(message.text.replace(',', '.'))
        user_id = str(message.from_user.id)
        
        if await update_user_weight(user_id, berat_baru):
            await message.reply(f"✅ Berat badan <b>{berat_baru} kg</b> berhasil dicatat & profil AI udah di-update!", parse_mode="HTML")
        else:
            await message.reply("❌ Gagal menyimpan data berat badan.")
            
    except ValueError:
        await message.reply("❌ Format salah bro. Tolong ketik angka aja ya (Contoh: 65.5). Coba lagi klik tombolnya.")
        
    await state.clear()
    await tampil_dashboard_progress(message.chat.id, str(message.from_user.id), bot=message.bot)