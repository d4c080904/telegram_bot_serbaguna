import hashlib
import logging
import datetime
import re
from database.db import get_db
from config import CHAT_HISTORY_LIMIT, CHAT_MAX_MESSAGES

logger = logging.getLogger(__name__)

def parse_number(val):
    if isinstance(val, (int, float)): return val
    if isinstance(val, str):
        match = re.search(r'[\d\.]+', val)
        if match: return float(match.group())
    return 0.0

def get_user_profile(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT nama, umur, berat, tinggi, jenis_kelamin FROM user_profiles WHERE user_id = ?", (str(user_id),))
        row = c.fetchone(); conn.close()
        if not row: return None
        return {'nama': row[0], 'umur': row[1], 'berat': row[2], 'tinggi': row[3], 'jenis_kelamin': row[4]}
    except Exception as e: logger.error(f"get_user_profile error: {e}"); return None

def save_user_profile(user_id, nama, umur, berat, tinggi, jenis_kelamin):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO user_profiles (user_id, nama, umur, berat, tinggi, jenis_kelamin, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', (str(user_id), nama, int(umur), float(berat), float(tinggi), jenis_kelamin))
        tanggal_ini = datetime.date.today().isoformat()
        c.execute("INSERT INTO weight_logs (user_id, tanggal, berat) VALUES (?, ?, ?)", (str(user_id), tanggal_ini, float(berat)))
        conn.commit(); conn.close(); return True
    except Exception as e: logger.error(f"save_user_profile error: {e}"); return False

def update_user_weight(user_id, berat_baru):
    """Fungsi sakti buat update berat badan di profil & history log"""
    try:
        conn = get_db(); c = conn.cursor()
        berat_float = float(parse_number(berat_baru))
        # 1. Update profil utama
        c.execute("UPDATE user_profiles SET berat = ? WHERE user_id = ?", (berat_float, str(user_id)))
        # 2. Insert ke history berat badan
        tanggal_ini = datetime.date.today().isoformat()
        c.execute("INSERT INTO weight_logs (user_id, tanggal, berat) VALUES (?, ?, ?)", (str(user_id), tanggal_ini, berat_float))
        conn.commit(); conn.close(); return True
    except Exception as e: logger.error(f"update_user_weight error: {e}"); return False

def get_gym_profile(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''SELECT target, level, pengalaman, frekuensi, alat, mode FROM gym_profile WHERE user_id = ?''', (str(user_id),))
        row_gym = c.fetchone()
        c.execute("SELECT nama, umur, berat, tinggi, jenis_kelamin FROM user_profiles WHERE user_id = ?", (str(user_id),))
        row_user = c.fetchone(); conn.close()
        if not row_user: return None
        profil = {'nama': row_user[0], 'umur': row_user[1], 'berat': row_user[2], 'tinggi': row_user[3], 'jenis_kelamin': row_user[4]}
        if row_gym:
            profil.update({'target': row_gym[0], 'level': row_gym[1], 'pengalaman': row_gym[2], 'frekuensi': row_gym[3], 'alat': row_gym[4], 'mode': row_gym[5] or 'noob'})
        else:
            profil.update({'target': None, 'level': None, 'pengalaman': None, 'frekuensi': None, 'alat': None, 'mode': 'noob'})
        return profil
    except Exception as e: logger.error(f"get_gym_profile error: {e}"); return None

def save_gym_profile(user_id, data):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO gym_profile (user_id, target, level, pengalaman, frekuensi, alat, mode) VALUES (?, ?, ?, ?, ?, ?, ?)''', (str(user_id), data.get('target'), data.get('level'), data.get('pengalaman'), data.get('frekuensi'), data.get('alat'), data.get('mode', 'noob')))
        conn.commit(); conn.close(); return True
    except Exception as e: logger.error(f"save_gym_profile error: {e}"); return False

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

def cek_duplikat_foto(user_id, photo_hash):
    try:
        conn = get_db(); c = conn.cursor()
        tanggal_ini = datetime.date.today().isoformat()
        c.execute("SELECT id FROM food_logs WHERE user_id = ? AND photo_hash = ? AND tanggal = ?", (str(user_id), photo_hash, tanggal_ini))
        row = c.fetchone(); conn.close(); return bool(row)
    except Exception as e: logger.error(f"cek_duplikat_foto error: {e}"); return False

def tambah_food_log(user_id, message_id, photo_message_id, photo_hash, nama, porsi, kalori, protein, karbo, lemak, gula):
    try:
        conn = get_db(); c = conn.cursor()
        tanggal_ini = datetime.date.today().isoformat()
        kal = int(parse_number(kalori)); pro = float(parse_number(protein))
        kar = float(parse_number(karbo)); lem = float(parse_number(lemak))
        gul = float(parse_number(gula))
        if isinstance(nama, list): nama = ", ".join(map(str, nama))
        else: nama = str(nama)
        c.execute('''INSERT INTO food_logs (user_id, message_id, photo_message_id, photo_hash, tanggal, nama_makanan, estimasi_porsi, kalori, protein, karbo, lemak, gula) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (str(user_id), message_id, photo_message_id, photo_hash, tanggal_ini, nama, porsi, kal, pro, kar, lem, gul))
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
        kal = int(parse_number(kalori)); pro = float(parse_number(protein))
        kar = float(parse_number(karbo)); lem = float(parse_number(lemak))
        gul = float(parse_number(gula))
        if isinstance(nama, list): nama = ", ".join(map(str, nama))
        else: nama = str(nama)
        c.execute('''UPDATE food_logs SET nama_makanan=?, estimasi_porsi=?, kalori=?, protein=?, karbo=?, lemak=?, gula=? WHERE user_id=? AND (message_id=? OR photo_message_id=?)''', (nama, porsi, kal, pro, kar, lem, gul, str(user_id), reply_msg_id, reply_msg_id))
        affected = c.rowcount; conn.commit(); conn.close(); return affected > 0
    except Exception as e: logger.error(f"update_food_log error: {e}"); return False

def get_total_makro_hari_ini(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        tanggal_ini = datetime.date.today().isoformat()
        c.execute("SELECT SUM(kalori), SUM(gula) FROM food_logs WHERE user_id = ? AND tanggal = ?", (str(user_id), tanggal_ini))
        row = c.fetchone(); conn.close()
        return (row[0] if row[0] else 0), (row[1] if row[1] else 0)
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
        affected = c.rowcount; conn.commit(); conn.close(); return affected > 0
    except Exception as e: logger.error(f"hapus_log_terakhir error: {e}"); return False

def tambah_air(user_id, ml):
    try:
        conn = get_db(); c = conn.cursor()
        tanggal_ini = datetime.date.today().isoformat()
        c.execute("INSERT INTO water_logs (user_id, tanggal, ml) VALUES (?, ?, ?)", (str(user_id), tanggal_ini, ml))
        conn.commit(); conn.close(); return True
    except Exception as e: logger.error(f"tambah_air error: {e}"); return False

def get_total_air_hari_ini(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        tanggal_ini = datetime.date.today().isoformat()
        c.execute("SELECT SUM(ml) FROM water_logs WHERE user_id = ? AND tanggal = ?", (str(user_id), tanggal_ini))
        total = c.fetchone()[0]; conn.close(); return total if total else 0
    except Exception as e: logger.error(f"get_total_air error: {e}"); return 0

def get_berat_terakhir(user_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT berat, tanggal FROM weight_logs WHERE user_id = ? ORDER BY id DESC LIMIT 2", (str(user_id),))
        rows = c.fetchall(); conn.close(); return rows
    except Exception as e: logger.error(f"get_berat_terakhir error: {e}"); return []