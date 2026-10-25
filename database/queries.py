import hashlib
import logging
import datetime
import re
from database.db import get_db
from config import CHAT_HISTORY_LIMIT, CHAT_MAX_MESSAGES

logger = logging.getLogger(__name__)

def parse_number(val):
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        match = re.search(r'[\d\.]+', val)
        if match:
            return float(match.group())
    return 0.0

def simpan_ke_db(user_id, username, teks_asli, teks_rapi):
    try:
        conn = get_db(); cursor = conn.cursor()
        cursor.execute('''INSERT INTO histori_chat (user_id, username, teks_asli, teks_rapi) VALUES (?, ?, ?, ?)''', (str(user_id), str(username), teks_asli, teks_rapi))
        conn.commit(); conn.close()
    except Exception as e: logger.error(f"simpan_ke_db error: {e}")

def cache_get(key):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT hasil FROM cache_ai WHERE key = ?", (key,))
        row = c.fetchone(); conn.close()
        return row[0] if row else None
    except Exception as e: logger.error(f"cache_get error: {e}"); return None

def cache_set(key, hasil):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO cache_ai (key, hasil) VALUES (?, ?)", (key, hasil))
        conn.commit(); conn.close()
    except Exception as e: logger.error(f"cache_set error: {e}")

def buat_cache_key(prefix, teks):
    h = hashlib.md5(teks.strip().lower().encode('utf-8')).hexdigest()
    return f"{prefix}:{h}"

def is_chat_mode(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT is_active FROM chat_sessions WHERE user_id = ?", (str(user_id),))
        row = c.fetchone(); conn.close()
        return bool(row and row[0] == 1)
    except Exception as e: logger.error(f"is_chat_mode error: {e}"); return False

def set_chat_mode(user_id, active):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''INSERT INTO chat_sessions (user_id, is_active, last_active) VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET is_active = excluded.is_active, last_active = CURRENT_TIMESTAMP''', (str(user_id), 1 if active else 0))
        conn.commit(); conn.close(); return True
    except Exception as e: logger.error(f"set_chat_mode error: {e}"); return False

def simpan_chat_message(user_id, role, content):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)", (str(user_id), role, content))
        c.execute('''DELETE FROM chat_messages WHERE user_id = ? AND id NOT IN (SELECT id FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?)''', (str(user_id), str(user_id), CHAT_MAX_MESSAGES))
        conn.commit(); conn.close()
    except Exception as e: logger.error(f"simpan_chat_message error: {e}")

def ambil_chat_history(user_id, limit=CHAT_HISTORY_LIMIT):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?''', (str(user_id), limit))
        rows = c.fetchall(); conn.close()
        return [{"role": role, "content": content} for role, content in reversed(rows)]
    except Exception as e: logger.error(f"ambil_chat_history error: {e}"); return []

def hapus_chat_history(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM chat_messages WHERE user_id = ?", (str(user_id),))
        conn.commit(); conn.close(); return True
    except Exception as e: logger.error(f"hapus_chat_history error: {e}"); return False

def get_gym_profile(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''SELECT mode, umur, berat, tinggi, jenis_kelamin, target, level, pengalaman, frekuensi, alat FROM gym_profile WHERE user_id = ?''', (str(user_id),))
        row = c.fetchone(); conn.close()
        if not row: return None
        return {'mode': row[0] or 'noob', 'umur': row[1], 'berat': row[2], 'tinggi': row[3], 'jenis_kelamin': row[4], 'target': row[5], 'level': row[6], 'pengalaman': row[7], 'frekuensi': row[8], 'alat': row[9]}
    except Exception as e: logger.error(f"get_gym_profile error: {e}"); return None

def save_gym_profile(user_id, data):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO gym_profile (user_id, mode, umur, berat, tinggi, jenis_kelamin, target, level, pengalaman, frekuensi, alat, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', (str(user_id), data.get('mode', 'noob'), data.get('umur'), data.get('berat'), data.get('tinggi'), data.get('jenis_kelamin'), data.get('target'), data.get('level'), data.get('pengalaman'), data.get('frekuensi'), data.get('alat')))
        conn.commit(); conn.close(); return True
    except Exception as e: logger.error(f"save_gym_profile error: {e}"); return False

# --- FUNGSI KALORI & GULA TRACKER ---

def tambah_food_log(user_id, message_id, photo_message_id, nama, porsi, kalori, protein, karbo, lemak, gula):
    try:
        conn = get_db(); c = conn.cursor()
        tanggal_ini = datetime.date.today().isoformat()
        
        kal = int(parse_number(kalori))
        pro = float(parse_number(protein))
        kar = float(parse_number(karbo))
        lem = float(parse_number(lemak))
        gul = float(parse_number(gula))
        
        if isinstance(nama, list): nama = ", ".join(map(str, nama))
        else: nama = str(nama)
            
        c.execute('''INSERT INTO food_logs (user_id, message_id, photo_message_id, tanggal, nama_makanan, estimasi_porsi, kalori, protein, karbo, lemak, gula) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (str(user_id), message_id, photo_message_id, tanggal_ini, nama, porsi, kal, pro, kar, lem, gul))
        conn.commit(); conn.close(); return True
    except Exception as e: logger.error(f"tambah_food_log error: {e}"); return False

def cek_id_makanan(user_id, reply_msg_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''SELECT id FROM food_logs WHERE user_id = ? AND (message_id = ? OR photo_message_id = ?)''', (str(user_id), reply_msg_id, reply_msg_id))
        row = c.fetchone(); conn.close(); return bool(row)
    except Exception as e: logger.error(f"cek_id_makanan error: {e}"); return False

def update_food_log(user_id, reply_msg_id, nama, porsi, kalori, protein, karbo, lemak, gula):
    try:
        conn = get_db(); c = conn.cursor()
        
        kal = int(parse_number(kalori))
        pro = float(parse_number(protein))
        kar = float(parse_number(karbo))
        lem = float(parse_number(lemak))
        gul = float(parse_number(gula))
        
        if isinstance(nama, list): nama = ", ".join(map(str, nama))
        else: nama = str(nama)
            
        c.execute('''UPDATE food_logs SET nama_makanan=?, estimasi_porsi=?, kalori=?, protein=?, karbo=?, lemak=?, gula=? WHERE user_id=? AND (message_id=? OR photo_message_id=?)''', (nama, porsi, kal, pro, kar, lem, gul, str(user_id), reply_msg_id, reply_msg_id))
        affected = c.rowcount
        conn.commit(); conn.close(); return affected > 0
    except Exception as e: logger.error(f"update_food_log error: {e}"); return False

def get_total_makro_hari_ini(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        tanggal_ini = datetime.date.today().isoformat()
        c.execute("SELECT SUM(kalori), SUM(gula) FROM food_logs WHERE user_id = ? AND tanggal = ?", (str(user_id), tanggal_ini))
        row = c.fetchone()
        conn.close()
        kalori = row[0] if row[0] else 0
        gula = row[1] if row[1] else 0
        return kalori, gula
    except Exception as e: logger.error(f"get_total_makro error: {e}"); return 0, 0

def get_history_makanan_hari_ini(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        tanggal_ini = datetime.date.today().isoformat()
        c.execute("SELECT nama_makanan, estimasi_porsi, kalori, gula, waktu FROM food_logs WHERE user_id = ? AND tanggal = ? ORDER BY id ASC", (str(user_id), tanggal_ini))
        rows = c.fetchall(); conn.close(); return rows
    except Exception as e: logger.error(f"get_history error: {e}"); return []

def hapus_log_terakhir(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''DELETE FROM food_logs WHERE id = (SELECT id FROM food_logs WHERE user_id = ? ORDER BY id DESC LIMIT 1)''', (str(user_id),))
        affected = c.rowcount
        conn.commit(); conn.close(); return affected > 0
    except Exception as e: logger.error(f"hapus_log_terakhir error: {e}"); return False