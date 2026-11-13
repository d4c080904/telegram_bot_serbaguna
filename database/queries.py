import hashlib
import logging
import datetime
import re
import json
from database.db import get_db
from config import CHAT_HISTORY_LIMIT, CHAT_MAX_MESSAGES

logger = logging.getLogger(__name__)

def parse_number(val):
    if isinstance(val, (int, float)): return val
    if isinstance(val, str):
        match = re.search(r'[\d\.]+', val)
        if match: return float(match.group())
    return 0.0

async def get_user_profile(user_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT nama, umur, berat, tinggi, jenis_kelamin FROM user_profiles WHERE user_id = $1", str(user_id))
            if not row: return None
            return {'nama': row['nama'], 'umur': row['umur'], 'berat': row['berat'], 'tinggi': row['tinggi'], 'jenis_kelamin': row['jenis_kelamin']}
    except Exception as e: logger.error(f"get_user_profile error: {e}"); return None

async def save_user_profile(user_id, nama, umur, berat, tinggi, jenis_kelamin):
    try:
        async with await get_db() as conn:
            await conn.execute('''INSERT INTO user_profiles (user_id, nama, umur, berat, tinggi, jenis_kelamin, updated_at) 
                         VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                         ON CONFLICT (user_id) DO UPDATE SET 
                         nama=EXCLUDED.nama, umur=EXCLUDED.umur, berat=EXCLUDED.berat, tinggi=EXCLUDED.tinggi, jenis_kelamin=EXCLUDED.jenis_kelamin, updated_at=CURRENT_TIMESTAMP''', 
                      str(user_id), nama, int(umur), float(berat), float(tinggi), jenis_kelamin)
            
            await conn.execute('''INSERT INTO users (user_id, nama, umur, tinggi, gender) 
                         VALUES ($1, $2, $3, $4, $5)
                         ON CONFLICT (user_id) DO UPDATE SET 
                         nama=EXCLUDED.nama, umur=EXCLUDED.umur, tinggi=EXCLUDED.tinggi, gender=EXCLUDED.gender''', 
                      str(user_id), nama, int(umur), float(tinggi), jenis_kelamin)

            tanggal_ini = datetime.date.today()
            await conn.execute("INSERT INTO weight_logs (user_id, tanggal, berat) VALUES ($1, $2, $3)", str(user_id), tanggal_ini, float(berat))
            return True
    except Exception as e: logger.error(f"save_user_profile error: {e}"); return False

async def update_user_weight(user_id, berat_baru):
    try:
        async with await get_db() as conn:
            berat_float = float(parse_number(berat_baru))
            await conn.execute("UPDATE user_profiles SET berat = $1 WHERE user_id = $2", berat_float, str(user_id))
            tanggal_ini = datetime.date.today()
            await conn.execute("INSERT INTO weight_logs (user_id, tanggal, berat) VALUES ($1, $2, $3)", str(user_id), tanggal_ini, berat_float)
            return True
    except Exception as e: logger.error(f"update_user_weight error: {e}"); return False

async def get_gym_profile(user_id):
    try:
        async with await get_db() as conn:
            row_gym = await conn.fetchrow('''SELECT target, level, pengalaman, frekuensi, alat, mode FROM gym_profile WHERE user_id = $1''', str(user_id))
            row_user = await conn.fetchrow("SELECT nama, umur, berat, tinggi, jenis_kelamin FROM user_profiles WHERE user_id = $1", str(user_id))
            if not row_user: return None
            profil = {'nama': row_user['nama'], 'umur': row_user['umur'], 'berat': row_user['berat'], 'tinggi': row_user['tinggi'], 'jenis_kelamin': row_user['jenis_kelamin']}
            if row_gym:
                profil.update({'target': row_gym['target'], 'level': row_gym['level'], 'pengalaman': row_gym['pengalaman'], 'frekuensi': row_gym['frekuensi'], 'alat': row_gym['alat'], 'mode': row_gym['mode'] or 'noob'})
            else:
                profil.update({'target': None, 'level': None, 'pengalaman': None, 'frekuensi': None, 'alat': None, 'mode': 'noob'})
            return profil
    except Exception as e: logger.error(f"get_gym_profile error: {e}"); return None

async def save_gym_profile(user_id, data):
    try:
        async with await get_db() as conn:
            await conn.execute('''INSERT INTO gym_profile (user_id, target, level, pengalaman, frekuensi, alat, mode) 
                         VALUES ($1, $2, $3, $4, $5, $6, $7)
                         ON CONFLICT (user_id) DO UPDATE SET 
                         target=EXCLUDED.target, level=EXCLUDED.level, pengalaman=EXCLUDED.pengalaman, frekuensi=EXCLUDED.frekuensi, alat=EXCLUDED.alat, mode=EXCLUDED.mode''', 
                      str(user_id), data.get('target'), data.get('level'), data.get('pengalaman'), data.get('frekuensi'), data.get('alat'), data.get('mode', 'noob'))
            return True
    except Exception as e: logger.error(f"save_gym_profile error: {e}"); return False

async def simpan_ke_db(user_id, username, teks_asli, teks_rapi):
    try:
        async with await get_db() as conn:
            await conn.execute('''INSERT INTO histori_chat (user_id, username, teks_asli, teks_rapi) VALUES ($1, $2, $3, $4)''', str(user_id), str(username), teks_asli, teks_rapi)
    except Exception as e: logger.error(f"simpan_ke_db error: {e}")

async def cache_get(key):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT hasil FROM cache_ai WHERE key = $1", key)
            return row['hasil'] if row else None
    except Exception as e: logger.error(f"cache_get error: {e}"); return None

async def cache_set(key, hasil):
    try:
        async with await get_db() as conn:
            await conn.execute("INSERT INTO cache_ai (key, hasil) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET hasil = EXCLUDED.hasil", key, hasil)
    except Exception as e: logger.error(f"cache_set error: {e}")

def buat_cache_key(prefix, teks):
    h = hashlib.md5(teks.strip().lower().encode('utf-8')).hexdigest()
    return f"{prefix}:{h}"

async def is_chat_mode(user_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT is_active FROM chat_sessions WHERE user_id = $1", str(user_id))
            return bool(row and row['is_active'] == 1)
    except Exception as e: logger.error(f"is_chat_mode error: {e}"); return False

async def set_chat_mode(user_id, active):
    try:
        async with await get_db() as conn:
            await conn.execute('''INSERT INTO chat_sessions (user_id, is_active, last_active) VALUES ($1, $2, CURRENT_TIMESTAMP) 
                         ON CONFLICT(user_id) DO UPDATE SET is_active = EXCLUDED.is_active, last_active = CURRENT_TIMESTAMP''', str(user_id), 1 if active else 0)
            return True
    except Exception as e: logger.error(f"set_chat_mode error: {e}"); return False

async def simpan_chat_message(user_id, role, content):
    try:
        async with await get_db() as conn:
            await conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES ($1, $2, $3)", str(user_id), role, content)
            await conn.execute('''DELETE FROM chat_messages WHERE id IN (
                            SELECT id FROM chat_messages WHERE user_id = $1 ORDER BY id DESC OFFSET $2
                         )''', str(user_id), CHAT_MAX_MESSAGES)
    except Exception as e: logger.error(f"simpan_chat_message error: {e}")

async def ambil_chat_history(user_id, limit=CHAT_HISTORY_LIMIT):
    try:
        async with await get_db() as conn:
            rows = await conn.fetch('''SELECT role, content FROM chat_messages WHERE user_id = $1 ORDER BY id DESC LIMIT $2''', str(user_id), limit)
            return [{"role": row['role'], "content": row['content']} for row in reversed(rows)]
    except Exception as e: logger.error(f"ambil_chat_history error: {e}"); return []

async def hapus_chat_history(user_id):
    try:
        async with await get_db() as conn:
            await conn.execute("DELETE FROM chat_messages WHERE user_id = $1", str(user_id))
            return True
    except Exception as e: logger.error(f"hapus_chat_history error: {e}"); return False

async def cek_duplikat_foto(user_id, photo_hash):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            row = await conn.fetchrow("SELECT id FROM food_logs WHERE user_id = $1 AND photo_hash = $2 AND tanggal = $3", str(user_id), photo_hash, tanggal_ini)
            return bool(row)
    except Exception as e: logger.error(f"cek_duplikat_foto error: {e}"); return False

async def tambah_food_log(user_id, message_id, photo_message_id, photo_hash, nama, porsi, kalori, protein, karbo, lemak, gula):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            kal = int(parse_number(kalori)); pro = float(parse_number(protein))
            kar = float(parse_number(karbo)); lem = float(parse_number(lemak))
            gul = float(parse_number(gula))
            if isinstance(nama, list): nama = ", ".join(map(str, nama))
            else: nama = str(nama)
            
            await conn.execute('''INSERT INTO food_logs (user_id, message_id, photo_message_id, photo_hash, tanggal, nama_makanan, estimasi_porsi, kalori, protein, karbo, lemak, gula) 
                         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)''', 
                      str(user_id), message_id, photo_message_id, photo_hash, tanggal_ini, nama, porsi, kal, pro, kar, lem, gul)
            return True
            
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e):
            logger.warning(f"⚠️ Duplikat dicegah DB: user {user_id}, hash {photo_hash}")
            return False
        logger.error(f"tambah_food_log error: {e}")
        return False

async def cek_id_makanan(user_id, reply_msg_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow('''SELECT id FROM food_logs WHERE user_id = $1 AND (message_id = $2 OR photo_message_id = $2)''', str(user_id), reply_msg_id)
            return bool(row)
    except Exception as e: logger.error(f"cek_id_makanan error: {e}"); return False

async def update_food_log(user_id, reply_msg_id, nama, porsi, kalori, protein, karbo, lemak, gula):
    try:
        async with await get_db() as conn:
            kal = int(parse_number(kalori)); pro = float(parse_number(protein))
            kar = float(parse_number(karbo)); lem = float(parse_number(lemak))
            gul = float(parse_number(gula))
            if isinstance(nama, list): nama = ", ".join(map(str, nama))
            else: nama = str(nama)
            result = await conn.execute('''UPDATE food_logs SET nama_makanan=$1, estimasi_porsi=$2, kalori=$3, protein=$4, karbo=$5, lemak=$6, gula=$7 
                         WHERE user_id=$8 AND (message_id=$9 OR photo_message_id=$9)''', 
                      nama, porsi, kal, pro, kar, lem, gul, str(user_id), reply_msg_id)
            return int(result.split(" ")[1]) > 0
    except Exception as e: logger.error(f"update_food_log error: {e}"); return False

async def get_total_makro_hari_ini(user_id):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            row = await conn.fetchrow("SELECT SUM(kalori) as kal, SUM(gula) as gul FROM food_logs WHERE user_id = $1 AND tanggal = $2", str(user_id), tanggal_ini)
            return (row['kal'] if row['kal'] else 0), (row['gul'] if row['gul'] else 0)
    except Exception as e: logger.error(f"get_total_makro error: {e}"); return 0, 0

async def get_history_makanan_hari_ini(user_id):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            return await conn.fetch("SELECT nama_makanan, estimasi_porsi, kalori, gula, waktu FROM food_logs WHERE user_id = $1 AND tanggal = $2 ORDER BY id ASC", str(user_id), tanggal_ini)
    except Exception as e: logger.error(f"get_history error: {e}"); return []

async def hapus_log_terakhir(user_id):
    try:
        async with await get_db() as conn:
            result = await conn.execute('''DELETE FROM food_logs WHERE id = (SELECT id FROM food_logs WHERE user_id = $1 ORDER BY id DESC LIMIT 1)''', str(user_id))
            return int(result.split(" ")[1]) > 0
    except Exception as e: logger.error(f"hapus_log_terakhir error: {e}"); return False

async def tambah_air(user_id, ml):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            await conn.execute("INSERT INTO water_logs (user_id, tanggal, ml) VALUES ($1, $2, $3)", str(user_id), tanggal_ini, ml)
            return True
    except Exception as e: logger.error(f"tambah_air error: {e}"); return False

async def get_total_air_hari_ini(user_id):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            row = await conn.fetchrow("SELECT SUM(ml) as ml FROM water_logs WHERE user_id = $1 AND tanggal = $2", str(user_id), tanggal_ini)
            return row['ml'] if row['ml'] else 0
    except Exception as e: logger.error(f"get_total_air error: {e}"); return 0

async def get_berat_terakhir(user_id):
    try:
        async with await get_db() as conn:
            return await conn.fetch("SELECT berat, tanggal FROM weight_logs WHERE user_id = $1 ORDER BY id DESC LIMIT 2", str(user_id))
    except Exception as e: logger.error(f"get_berat_terakhir error: {e}"); return []

async def get_all_data_for_export(user_id):
    try:
        async with await get_db() as conn:
            food_data = await conn.fetch("SELECT tanggal, nama_makanan, estimasi_porsi, kalori, protein, karbo, lemak, gula, waktu FROM food_logs WHERE user_id = $1 ORDER BY tanggal DESC", str(user_id))
            water_data = await conn.fetch("SELECT tanggal, ml, waktu FROM water_logs WHERE user_id = $1 ORDER BY tanggal DESC", str(user_id))
            weight_data = await conn.fetch("SELECT tanggal, berat, waktu FROM weight_logs WHERE user_id = $1 ORDER BY tanggal DESC", str(user_id))
            return food_data, water_data, weight_data
    except Exception as e: logger.error(f"get_all_data_for_export error: {e}"); return [], [], []

async def save_wizard_state(user_id, state_type, step, data):
    try:
        async with await get_db() as conn:
            data_json = json.dumps(data)
            await conn.execute('''INSERT INTO wizard_states (user_id, state_type, step, data, updated_at) 
                         VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                         ON CONFLICT (user_id, state_type) DO UPDATE SET 
                         step = EXCLUDED.step, data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP''', 
                      str(user_id), state_type, step, data_json)
            return True
    except Exception as e: logger.error(f"save_wizard_state error: {e}"); return False

async def get_wizard_state(user_id, state_type):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT step, data FROM wizard_states WHERE user_id = $1 AND state_type = $2", str(user_id), state_type)
            if row:
                return {'step': row['step'], 'data': json.loads(row['data'])}
            return None
    except Exception as e: logger.error(f"get_wizard_state error: {e}"); return None

async def delete_wizard_state(user_id, state_type):
    try:
        async with await get_db() as conn:
            await conn.execute("DELETE FROM wizard_states WHERE user_id = $1 AND state_type = $2", str(user_id), state_type)
            return True
    except Exception as e: logger.error(f"delete_wizard_state error: {e}"); return False

async def get_berat_14_hari_terakhir(user_id):
    try:
        async with await get_db() as conn:
            rows = await conn.fetch('''
                SELECT tanggal, berat FROM weight_logs 
                WHERE user_id = $1 AND tanggal >= CURRENT_DATE - INTERVAL '14 days'
                GROUP BY tanggal, berat
                ORDER BY tanggal ASC
            ''', str(user_id))
            return rows
    except Exception as e: 
        logger.error(f"get_berat_14_hari_terakhir error: {e}")
        return []

async def tambah_workout_log(user_id, olahraga, durasi, kalori_terbakar):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            await conn.execute('''INSERT INTO workout_logs (user_id, tanggal, olahraga, durasi, kalori_terbakar) 
                         VALUES ($1, $2, $3, $4, $5)''', 
                      str(user_id), tanggal_ini, olahraga, int(durasi), int(kalori_terbakar))
            return True
    except Exception as e: 
        logger.error(f"tambah_workout_log error: {e}")
        return False

async def get_total_kalori_terbakar_hari_ini(user_id):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            row = await conn.fetchrow("SELECT SUM(kalori_terbakar) as total FROM workout_logs WHERE user_id = $1 AND tanggal = $2", str(user_id), tanggal_ini)
            return row['total'] if row['total'] else 0
    except Exception as e: 
        logger.error(f"get_total_kalori_terbakar error: {e}")
        return 0

async def get_history_workout_hari_ini(user_id):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            return await conn.fetch("SELECT olahraga, durasi, kalori_terbakar, waktu FROM workout_logs WHERE user_id = $1 AND tanggal = $2 ORDER BY id ASC", str(user_id), tanggal_ini)
    except Exception as e: 
        logger.error(f"get_history_workout error: {e}")
        return []

# --- FUNGSI BARU ENTERPRISE SCHEMA ---
async def get_daily_logs(user_id, tanggal_str):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT * FROM daily_logs WHERE user_id = $1 AND tanggal = $2", str(user_id), tanggal_str)
            return row
    except Exception as e: 
        logger.error(f"get_daily_logs error: {e}")
        return None

async def set_user_premium(user_id, days):
    try:
        async with await get_db() as conn:
            await conn.execute('''
                UPDATE users 
                SET premium_until = CURRENT_TIMESTAMP + ($1 || ' days')::interval 
                WHERE user_id = $2
            ''', str(days), str(user_id))
            return True
    except Exception as e: 
        logger.error(f"set_user_premium error: {e}")
        return False

# --- FUNGSI PREMIUM & PAYMENT ---
async def get_user_premium_status(user_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT premium_until FROM users WHERE user_id = $1", str(user_id))
            if row and row['premium_until']:
                if row['premium_until'] > datetime.datetime.now():
                    return True, row['premium_until']
            return False, None
    except Exception as e: 
        logger.error(f"get_user_premium_status error: {e}")
        return False, None

async def catat_payment_event(transaction_id, user_id, amount, status):
    try:
        async with await get_db() as conn:
            result = await conn.execute('''
                INSERT INTO payment_events (transaction_id, user_id, amount, status) 
                VALUES ($1, $2, $3, $4) ON CONFLICT (transaction_id) DO NOTHING
            ''', transaction_id, str(user_id), int(amount), status)
            return "INSERT" in result
    except Exception as e: 
        logger.error(f"catat_payment_event error: {e}")
        return False

async def aktifkan_premium(user_id, days=30):
    try:
        async with await get_db() as conn:
            await conn.execute('''
                UPDATE users 
                SET premium_until = CURRENT_TIMESTAMP + ($1 || ' days')::interval 
                WHERE user_id = $2
            ''', str(days), str(user_id))
            return True
    except Exception as e: 
        logger.error(f"aktifkan_premium error: {e}")
        return False