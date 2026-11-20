from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID
from database.queries import (
    request_access_db, approve_user_access, reject_user_access,
    admin_get_stats, admin_list_users, admin_kick_user, admin_unban_user
)
from bot_instance import bot
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()

def cek_admin(user_id):
    return str(user_id).strip() == str(ADMIN_ID).strip()

# --- FITUR LAMA: REQUEST ACCESS ---
@router.callback_query(F.data == "req_access")
async def handle_req_access(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name

    await request_access_db(user_id, username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Setujui (3 Hari)", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Tolak", callback_data=f"reject_{user_id}")
        ]
    ])
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>PENDAFTARAN BARU</b>\n\nUser: @{username}\nID: <code>{user_id}</code>\nIngin meminta izin akses bot.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.message.edit_text("⏳ Permintaan Anda sudah dikirim ke Admin. Mohon tunggu persetujuan.")
    except Exception as e:
        logger.error(f"Gagal kirim pesan ke admin: {e}")
        await callback.message.edit_text("❌ Gagal mengirim pesan ke Admin.")

@router.callback_query(F.data.startswith("approve_"))
async def handle_approve(callback: CallbackQuery):
    if not cek_admin(callback.from_user.id):
        return await callback.answer("Anda bukan Admin!", show_alert=True)

    user_id = callback.data.split("_")[1]
    await approve_user_access(user_id, days=3) 
    
    try:
        await bot.send_message(user_id, "✅ <b>AKSES DISETUJUI!</b>\n\nAdmin telah menyetujui akses Anda.\nSilakan ketik /start untuk mulai menggunakan bot. Anda mendapatkan masa trial gratis selama 3 hari.", parse_mode="HTML")
    except: pass
        
    await callback.message.edit_text(f"✅ User <code>{user_id}</code> berhasil disetujui (Trial 3 Hari).", parse_mode="HTML")

@router.callback_query(F.data.startswith("reject_"))
async def handle_reject(callback: CallbackQuery):
    if not cek_admin(callback.from_user.id):
        return await callback.answer("Anda bukan Admin!", show_alert=True)

    user_id = callback.data.split("_")[1]
    await reject_user_access(user_id)
    
    try:
        await bot.send_message(user_id, "❌ <b>AKSES DITOLAK</b>\n\nMohon maaf, Admin menolak permintaan Anda.", parse_mode="HTML")
    except: pass
        
    await callback.message.edit_text(f"❌ User <code>{user_id}</code> telah ditolak.", parse_mode="HTML")

# ==========================================
# --- FITUR BARU: ADMIN DASHBOARD (FASE B) ---
# ==========================================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not cek_admin(message.from_user.id):
        return await message.answer("⛔ Anda bukan Admin.")
    
    await tampilkan_dashboard_admin(message.chat.id, message.message_id, bot, edit=False)

@router.callback_query(F.data == "admin_dash")
async def callback_admin_dash(callback: CallbackQuery):
    if not cek_admin(callback.from_user.id):
        return await callback.answer("Anda bukan Admin!", show_alert=True)
    await callback.answer()
    await tampilkan_dashboard_admin(callback.message.chat.id, callback.message.message_id, callback.bot, edit=True)

async def tampilkan_dashboard_admin(chat_id, message_id, bot, edit=False):
    stats = await admin_get_stats()
    
    teks = (
        "🔐 <b>ADMIN DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total User: <b>{stats['total']}</b>\n"
        f"✅ Aktif VIP: <b>{stats['active']}</b>\n"
        f"⚠️ Expired: <b>{stats['expired']}</b>\n"
        f"🚫 Banned: <b>{stats['banned']}</b>\n"
        f"🚨 Bandel (Expired tp msh akses): <b>{stats['bandel']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih filter user di bawah:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Aktif", callback_data="admin_list_active_0")
    builder.button(text="⚠️ Expired", callback_data="admin_list_expired_0")
    builder.button(text="🚨 Bandel", callback_data="admin_list_bandel_0")
    builder.button(text="🚫 Banned", callback_data="admin_list_banned_0")
    builder.adjust(2, 2)
    
    if edit:
        try: await bot.edit_message_text(teks, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=builder.as_markup())
        except: pass
    else:
        await bot.send_message(chat_id, teks, parse_mode="HTML", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("admin_list_"))
async def callback_admin_list(callback: CallbackQuery):
    if not cek_admin(callback.from_user.id):
        return await callback.answer("Anda bukan Admin!", show_alert=True)
    await callback.answer()
    
    parts = callback.data.split("_")
    filter_type = parts[2]
    offset = int(parts[3])
    
    users, total = await admin_list_users(filter_type, offset, limit=5)
    
    if not users:
        return await callback.message.edit_text(f"Tidak ada user di kategori <b>{filter_type}</b>.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Kembali", callback_data="admin_dash")]]))
    
    teks = f"📋 <b>DAFTAR USER ({filter_type.upper()})</b>\nTotal: {total}\n━━━━━━━━━━━━━━━━━━━━\n\n"
    builder = InlineKeyboardBuilder()
    
    for u in users:
        uid = u['user_id']
        nama = u['nama'] or "Tanpa Nama"
        
        status = ""
        if u['is_banned']:
            status = "🚫 BANNED"
        elif u['premium_until'] and u['premium_until'] > datetime.now():
            status = "✅ Aktif"
        else:
            status = "⚠️ Expired"
            
        last_act = "Belum pernah"
        if u['last_active_at']:
            diff = datetime.now() - u['last_active_at']
            if diff.days > 0: last_act = f"{diff.days} hari lalu"
            elif diff.seconds // 3600 > 0: last_act = f"{diff.seconds // 3600} jam lalu"
            else: last_act = f"{diff.seconds // 60} menit lalu"
            
        teks += f"👤 <b>{nama}</b> (<code>{uid}</code>)\n"
        teks += f"📊 Status: {status} | ⏱️ Akses: {last_act}\n"
        
        if u['is_banned']:
            builder.button(text=f"✅ Unban {nama}", callback_data=f"admin_unban_{uid}")
        else:
            builder.button(text=f"🚫 Kick {nama}", callback_data=f"admin_kick_{uid}")
            
    nav_row = []
    if offset > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"admin_list_{filter_type}_{offset-5}"))
    if offset + 5 < total:
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"admin_list_{filter_type}_{offset+5}"))
    
    builder.adjust(1) 
    if nav_row:
        builder.row(*nav_row)
    builder.row(InlineKeyboardButton(text="🔙 Kembali ke Dash", callback_data="admin_dash"))
    
    try:
        await callback.message.edit_text(teks, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception:
        pass

@router.callback_query(F.data.startswith("admin_kick_"))
async def callback_admin_kick(callback: CallbackQuery):
    if not cek_admin(callback.from_user.id):
        return await callback.answer("Anda bukan Admin!", show_alert=True)
    
    user_id = callback.data.split("_")[2]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ya, Tendang!", callback_data=f"admin_do_kick_{user_id}")],
        [InlineKeyboardButton(text="❌ Batal", callback_data="admin_dash")]
    ])
    await callback.message.edit_text(f"⚠️ Yakin mau menendang (kick) user <code>{user_id}</code>?\n\nAkses user akan dicabut dan harus bayar lagi untuk masuk.", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_do_kick_"))
async def callback_admin_do_kick(callback: CallbackQuery):
    if not cek_admin(callback.from_user.id):
        return await callback.answer("Anda bukan Admin!", show_alert=True)
    
    user_id = callback.data.split("_")[3]
    
    if await admin_kick_user(user_id, "Akses dicabut oleh Admin (Telat bayar / Bandel)"):
        try:
            await bot.send_message(user_id, "🚫 <b>AKSES LU DICABUT</b>\n\nAdmin telah mencabut akses Anda karena masa aktif habis atau pelanggaran.\nSilakan hubungi admin / bayar langganan untuk mengaktifkan kembali.", parse_mode="HTML")
        except: pass
        
        await callback.answer("✅ User berhasil ditendang!", show_alert=True)
        await tampilkan_dashboard_admin(callback.message.chat.id, callback.message.message_id, callback.bot, edit=True)
    else:
        await callback.answer("❌ Gagal menendang user.", show_alert=True)

@router.callback_query(F.data.startswith("admin_unban_"))
async def callback_admin_unban(callback: CallbackQuery):
    if not cek_admin(callback.from_user.id):
        return await callback.answer("Anda bukan Admin!", show_alert=True)
    
    user_id = callback.data.split("_")[2]
    
    if await admin_unban_user(user_id, days=30):
        try:
            await bot.send_message(user_id, "✅ <b>AKSES DIPULIHKAN!</b>\n\nAdmin telah mengaktifkan kembali akun Anda selama 30 hari. Ketik /start untuk mulai.", parse_mode="HTML")
        except: pass
        
        await callback.answer("✅ User berhasil di-unban (30 Hari)!", show_alert=True)
        await tampilkan_dashboard_admin(callback.message.chat.id, callback.message.message_id, callback.bot, edit=True)
    else:
        await callback.answer("❌ Gagal unban user.", show_alert=True)