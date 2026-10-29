from bot_instance import bot
from telebot import types
from database.queries import get_gym_profile, save_gym_profile
from database.db import get_db
from services.ai import analisis_gym_noob, analisis_gym_pro
from utils.decorators import rate_limited
from utils.helpers import hitung_bmi, kategori_bmi, strip_markdown
from utils.state import set_gym_wizard, get_gym_wizard, clear_gym_wizard
import logging

logger = logging.getLogger(__name__)

def tampil_menu_gym(chat_id, user_id, message_id=None):
    profil = get_gym_profile(user_id)
    nama = profil['nama'] if profil else "Bro"
    
    teks = (
        f"💪 *ASISTEN GYM PRIBADI*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Halo *{nama}*!\n"
        f"Data saat ini: {profil['umur']}th, {profil['berat']}kg, {profil['tinggi']}cm\n\n"
        "Pilih mode program latihan lu:"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🆕 Mode Baru Gym", callback_data="gym_noob_start"),
        types.InlineKeyboardButton("💪 Mode Pro Gym", callback_data="gym_pro_start")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Profil Saya", callback_data="gym_view_profile"),
        types.InlineKeyboardButton("📝 Log Latihan", callback_data="gym_log_info")
    )
    markup.add(types.InlineKeyboardButton("🔙 Kembali ke GYM MODE", callback_data="menu_gym_mode"))
    
    try:
        if message_id:
            bot.edit_message_text(teks, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(chat_id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        logger.error(f"tampil_menu_gym error: {e}")

def tampil_profil_gym(chat_id, user_id, message_id=None):
    profil = get_gym_profile(user_id)
    
    if not profil:
        teks = "⚠️ *Lu belum punya profil Gym.*\n\nIsi profil dulu di menu awal ya."
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Kembali", callback_data="menu_gym"))
        try:
            if message_id: bot.edit_message_text(teks, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
            else: bot.send_message(chat_id, teks, parse_mode='Markdown', reply_markup=markup)
        except Exception: pass
        return
        
    bmi = hitung_bmi(profil['berat'], profil['tinggi'])
    kategori = kategori_bmi(bmi)
    mode_label = "🆕 Baru Gym" if profil['mode'] == 'noob' else "💪 Pro Gym"
    
    teks = (
        f"📊 *PROFIL GYM LU*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Mode: *{mode_label}*\n\n"
        f"👤 Umur: *{profil['umur'] or 'N/A'}* tahun\n"
        f"⚖️ Berat: *{profil['berat'] or 'N/A'}* kg\n"
        f"📏 Tinggi: *{profil['tinggi'] or 'N/A'}* cm\n"
        f"📈 BMI: *{bmi or 'N/A'}* ({kategori})\n"
    )
    
    if profil['mode'] == 'pro':
        teks += (
            f"\n🎯 Target: *{profil['target'] or 'N/A'}*\n"
            f"🎓 Level: *{profil['level'] or 'N/A'}*\n"
            f"⏳ Pengalaman: *{profil['pengalaman'] or 'N/A'}* tahun\n"
            f"📅 Frekuensi: *{profil['frekuensi'] or 'N/A'}*x/minggu\n"
            f"🏋️ Alat: *{profil['alat'] or 'N/A'}*\n"
        )
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Daftar Ulang", callback_data=f"gym_{profil['mode']}_start"),
        types.InlineKeyboardButton("📝 Log Latihan", callback_data="gym_log_info")
    )
    markup.add(types.InlineKeyboardButton("🔙 Menu Gym", callback_data="menu_gym"))
    
    try:
        if message_id: bot.edit_message_text(teks, chat_id, message_id, parse_mode='Markdown', reply_markup=markup)
        else: bot.send_message(chat_id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e: logger.error(f"tampil_profil_gym error: {e}")

# --- HANDLER GYM ---
@bot.message_handler(commands=['gym'])
@rate_limited
def handler_gym(pesan):
    try:
        user_id = str(pesan.from_user.id)
        teks_perintah = pesan.text.replace("/gym", "").strip()
        
        if not teks_perintah:
            tampil_menu_gym(pesan.chat.id, user_id)
            return
            
        profil = get_gym_profile(user_id)
        if not profil:
            bot.reply_to(pesan, "⚠️ Lu belum punya profil Gym nih.\n\nBikin dulu dengan ketik `/gym` (tanpa teks).", parse_mode='Markdown')
            return
            
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO gym_logs (user_id, log_teks) VALUES (?, ?)", (user_id, teks_perintah))
        conn.commit()
        conn.close()
        
        bot.send_chat_action(pesan.chat.id, 'typing')
        pesan_tunggu = bot.reply_to(pesan, "⏳ _PT AI lu lagi evaluasi..._", parse_mode="Markdown")
        
        mode = profil['mode']
        if mode == 'noob':
            system_prompt = (
                f"Kamu adalah asisten gym ramah untuk pemula. "
                f"Klien: umur {profil['umur']}th, BB {profil['berat']}kg, TB {profil['tinggi']}cm. "
                f"Evaluasi laporan latihan/makan dia dengan bahasa sederhana & motivasi. "
                f"JANGAN pakai markdown (** atau * atau `). Tulis teks polos aja."
            )
        else:
            system_prompt = (
                f"Kamu adalah personal trainer elite untuk klien berpengalaman. "
                f"Klien: umur {profil['umur']}th, BB {profil['berat']}kg, TB {profil['tinggi']}cm, "
                f"target {profil['target']}, level {profil['level']}, "
                f"frekuensi {profil['frekuensi']}x/minggu, alat {profil['alat']}. "
                f"Evaluasi laporan dia dengan detail teknis. "
                f"JANGAN pakai markdown (** atau * atau `). Tulis teks polos aja."
            )
            
        from services.ai import MODEL_GROQ_LIST
        from bot_instance import groq_client
        hasil = None
        
        for model_name in MODEL_GROQ_LIST:
            try:
                response = groq_client.chat.completions.create(
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
            try:
                bot.edit_message_text(hasil, pesan.chat.id, pesan_tunggu.message_id, parse_mode='Markdown')
            except Exception:
                bot.edit_message_text(strip_markdown(hasil), pesan.chat.id, pesan_tunggu.message_id)
        else:
            bot.edit_message_text("❌ AI lagi error nih bro. Coba lagi bentar ya.", pesan.chat.id, pesan_tunggu.message_id)
            
    except Exception as e:
        logger.error(f"[gym] error: {e}")
        try: bot.reply_to(pesan, "❌ Ada error di fitur gym. Coba lagi nanti.")
        except Exception: pass

def proses_gym_wizard(pesan, wizard):
    user_id = pesan.from_user.id
    teks = pesan.text.strip()
    mode = wizard['mode']
    
    if mode == 'pro':
        parts = [p.strip().lower() for p in teks.split('|')]
        if len(parts) != 5:
            bot.reply_to(pesan, "❌ Format salah bro.\n\nKirim pakai format:\n`target | level | pengalaman | frekuensi | alat`\n\nContoh:\n`cutting | intermediate | 3 | 5 | gym_full`", parse_mode='Markdown')
            return
        try:
            target = parts[0]
            level = parts[1]
            pengalaman = int(parts[2])
            frekuensi = int(parts[3])
            alat = parts[4]
        except ValueError:
            bot.reply_to(pesan, "❌ Ada format yang salah. Coba lagi.")
            return
            
        if target not in ('bulking', 'cutting', 'recomp', 'strength') or level not in ('beginner', 'intermediate', 'advanced') or alat not in ('gym_full', 'home_dumbbell', 'home_barbell', 'bodyweight'):
            bot.reply_to(pesan, "❌ Pilihan teks salah. Cek lagi formatnya.")
            return
            
        data_pro = {'mode': 'pro', 'target': target, 'level': level, 'pengalaman': pengalaman, 'frekuensi': frekuensi, 'alat': alat}
        save_gym_profile(user_id, data_pro)
        clear_gym_wizard(user_id)
        
        profil = get_gym_profile(user_id)
        if not profil:
            bot.reply_to(pesan, "❌ Gagal ambil data profil.")
            return
            
        bot.reply_to(pesan, f"✅ Data program Pro disimpan!\n\n⏳ _AI lagi nyiapin analisis advanced..._", parse_mode='Markdown')
        bot.send_chat_action(pesan.chat.id, 'typing')
        
        data_pro.update({'umur': profil['umur'], 'berat': profil['berat'], 'tinggi': profil['tinggi'], 'jenis_kelamin': profil['jenis_kelamin']})
        hasil = analisis_gym_pro(data_pro)
        
        if hasil:
            try: bot.send_message(pesan.chat.id, hasil, parse_mode='Markdown')
            except Exception: bot.send_message(pesan.chat.id, strip_markdown(hasil))
        else:
            bot.send_message(pesan.chat.id, "❌ AI-nya lagi error. Coba lagi nanti ya.")
            
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("📝 Log Latihan", callback_data="gym_log_info"), types.InlineKeyboardButton("📊 Profil Saya", callback_data="gym_view_profile"))
        markup.add(types.InlineKeyboardButton("🔙 Menu Gym", callback_data="menu_gym"))
        bot.send_message(pesan.chat.id, "👇 Selanjutnya lu bisa:", reply_markup=markup)
        return

@bot.callback_query_handler(func=lambda call: call.data == "menu_gym")
def callback_menu_gym(call):
    try:
        bot.answer_callback_query(call.id)
        clear_gym_wizard(call.from_user.id)
        tampil_menu_gym(call.message.chat.id, call.from_user.id, call.message.message_id)
    except Exception as e: logger.error(f"[menu_gym] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "gym_noob_start")
def callback_gym_noob_start(call):
    try:
        user_id = str(call.from_user.id)
        bot.answer_callback_query(call.id, "⏳ Nyiapin panduan...")
        
        profil = get_gym_profile(user_id)
        if not profil:
            bot.send_message(call.message.chat.id, "⚠️ Lu belum isi profil di awal. Ketik /start dulu ya.")
            return
            
        save_gym_profile(user_id, {'mode': 'noob', 'target': 'recomp'})
        
        bot.edit_message_text("⏳ _AI lagi nyiapin panduan buat lu..._", call.message.chat.id, call.message.message_id)
        bot.send_chat_action(call.message.chat.id, 'typing')
        
        hasil = analisis_gym_noob(profil['umur'], profil['berat'], profil['tinggi'])
        
        if hasil:
            try: bot.send_message(call.message.chat.id, hasil, parse_mode='Markdown')
            except Exception: bot.send_message(call.message.chat.id, strip_markdown(hasil))
        else:
            bot.send_message(call.message.chat.id, "❌ AI error. Coba lagi.")
            
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("📝 Log Latihan", callback_data="gym_log_info"), types.InlineKeyboardButton("📊 Profil Saya", callback_data="gym_view_profile"))
        markup.add(types.InlineKeyboardButton("🔙 Menu Gym", callback_data="menu_gym"))
        bot.send_message(call.message.chat.id, "👇 Selanjutnya lu bisa:", reply_markup=markup)
        
    except Exception as e: logger.error(f"[gym_noob] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "gym_pro_start")
def callback_gym_pro_start(call):
    try:
        set_gym_wizard(call.from_user.id, 'pro', 'input_data')
        bot.answer_callback_query(call.id, "💪 Mode Pro Gym!")
        teks = (
            "💪 *MODE PRO GYM*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Kirim data program lu dalam 1 baris:\n\n"
            "📌 *Format:*\n"
            "`target | level | pengalaman | frekuensi | alat`\n\n"
            "📌 *Contoh:*\n"
            "`cutting | intermediate | 3 | 5 | gym_full`\n\n"
            "Gass kirim datanya! 👇\n\n"
            "_Ketik /cancel kalau mau batal_"
        )
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown')
    except Exception as e: logger.error(f"[gym_pro] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "gym_view_profile")
def callback_gym_view_profile(call):
    try:
        bot.answer_callback_query(call.id)
        tampil_profil_gym(call.message.chat.id, call.from_user.id, call.message.message_id)
    except Exception as e: logger.error(f"[gym_view_profile] error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "gym_log_info")
def callback_gym_log_info(call):
    try:
        bot.answer_callback_query(call.id)
        teks = (
            "📝 *LOG LATIHAN & MAKAN*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Kirim laporan lu dengan ketik:\n\n"
            "`/gym [laporan]`\n\n"
            "*Contoh:*\n"
            "`/gym hari ini latihan dada, bench 60kg 4x10`\n\n"
            "AI bakal evaluasi & kasih saran sesuai profil lu. 🔥"
        )
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Menu Gym", callback_data="menu_gym"))
        try: bot.edit_message_text(teks, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        except Exception: bot.send_message(call.message.chat.id, teks, parse_mode='Markdown', reply_markup=markup)
    except Exception as e: logger.error(f"[gym_log_info] error: {e}")