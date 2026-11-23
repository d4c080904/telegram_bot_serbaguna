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
            berat_float = round(float(berat), 1)
            await conn.execute('''INSERT INTO user_profiles (user_id, nama, umur, berat, tinggi, jenis_kelamin, updated_at) 
                         VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                         ON CONFLICT (user_id) DO UPDATE SET 
                         nama=EXCLUDED.nama, umur=EXCLUDED.umur, berat=EXCLUDED.berat, tinggi=EXCLUDED.tinggi, jenis_kelamin=EXCLUDED.jenis_kelamin, updated_at=CURRENT_TIMESTAMP''', 
                      str(user_id), nama, int(umur), berat_float, float(tinggi), jenis_kelamin)
            
            await conn.execute('''INSERT INTO users (user_id, nama, umur, tinggi, gender) 
                         VALUES ($1, $2, $3, $4, $5)
                         ON CONFLICT (user_id) DO UPDATE SET 
                         nama=EXCLUDED.nama, umur=EXCLUDED.umur, tinggi=EXCLUDED.tinggi, gender=EXCLUDED.gender''', 
                      str(user_id), nama, int(umur), float(tinggi), jenis_kelamin)

            tanggal_ini = datetime.date.today()
            existing = await conn.fetchrow(
                "SELECT id FROM weight_logs WHERE user_id = $1 AND tanggal = $2 ORDER BY id DESC LIMIT 1",
                str(user_id), tanggal_ini
            )
            if existing:
                await conn.execute("UPDATE weight_logs SET berat = $1 WHERE id = $2", berat_float, existing['id'])
            else:
                await conn.execute("INSERT INTO weight_logs (user_id, tanggal, berat) VALUES ($1, $2, $3)", str(user_id), tanggal_ini, berat_float)
            return True
    except Exception as e: logger.error(f"save_user_profile error: {e}"); return False

async def update_user_weight(user_id, berat_baru):
    try:
        async with await get_db() as conn:
            berat_float = round(float(parse_number(berat_baru)), 1)
            await conn.execute("UPDATE user_profiles SET berat = $1 WHERE user_id = $2", berat_float, str(user_id))
            tanggal_ini = datetime.date.today()
            existing = await conn.fetchrow(
                "SELECT id FROM weight_logs WHERE user_id = $1 AND tanggal = $2 ORDER BY id DESC LIMIT 1",
                str(user_id), tanggal_ini
            )
            if existing:
                await conn.execute("UPDATE weight_logs SET berat = $1 WHERE id = $2", berat_float, existing['id'])
            else:
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
        if "duplicate key value violates unique constraint" in str(e): return False
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
            return await conn.fetch("SELECT id, nama_makanan, estimasi_porsi, kalori, gula, waktu FROM food_logs WHERE user_id = $1 AND tanggal = $2 ORDER BY id DESC", str(user_id), tanggal_ini)
    except Exception as e: logger.error(f"get_history error: {e}"); return []

async def hapus_food_log_by_id(user_id, log_id):
    try:
        async with await get_db() as conn:
            result = await conn.execute('''DELETE FROM food_logs WHERE id = $1 AND user_id = $2''', int(log_id), str(user_id))
            return int(result.split(" ")[1]) > 0
    except Exception as e: logger.error(f"hapus_food_log_by_id error: {e}"); return False

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
    except Exception as e: logger.error(f"get_berat_14_hari_terakhir error: {e}"); return []

async def tambah_workout_log(user_id, olahraga, durasi, kalori_terbakar):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            await conn.execute('''INSERT INTO workout_logs (user_id, tanggal, olahraga, durasi, kalori_terbakar) 
                         VALUES ($1, $2, $3, $4, $5)''', 
                      str(user_id), tanggal_ini, olahraga, int(durasi), int(kalori_terbakar))
            return True
    except Exception as e: logger.error(f"tambah_workout_log error: {e}"); return False

async def get_total_kalori_terbakar_hari_ini(user_id):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            row = await conn.fetchrow("SELECT SUM(kalori_terbakar) as total FROM workout_logs WHERE user_id = $1 AND tanggal = $2", str(user_id), tanggal_ini)
            return row['total'] if row['total'] else 0
    except Exception as e: logger.error(f"get_total_kalori_terbakar error: {e}"); return 0

async def get_history_workout_hari_ini(user_id):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            return await conn.fetch("SELECT olahraga, durasi, kalori_terbakar, waktu FROM workout_logs WHERE user_id = $1 AND tanggal = $2 ORDER BY id ASC", str(user_id), tanggal_ini)
    except Exception as e: logger.error(f"get_history_workout error: {e}"); return []

async def get_daily_logs(user_id, tanggal_str):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT * FROM daily_logs WHERE user_id = $1 AND tanggal = $2", str(user_id), tanggal_str)
            return row
    except Exception as e: logger.error(f"get_daily_logs error: {e}"); return None

async def set_user_premium(user_id, days):
    try:
        async with await get_db() as conn:
            await conn.execute('''UPDATE users SET premium_until = CURRENT_TIMESTAMP + ($1 || ' days')::interval WHERE user_id = $2''', str(days), str(user_id))
            return True
    except Exception as e: logger.error(f"set_user_premium error: {e}"); return False

async def get_user_premium_status(user_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT premium_until FROM users WHERE user_id = $1", str(user_id))
            if row and row['premium_until']:
                if row['premium_until'] > datetime.datetime.now():
                    return True, row['premium_until']
            return False, None
    except Exception as e: logger.error(f"get_user_premium_status error: {e}"); return False, None

async def catat_payment_event(transaction_id, user_id, amount, status):
    try:
        async with await get_db() as conn:
            result = await conn.execute('''INSERT INTO payment_events (transaction_id, user_id, amount, status) VALUES ($1, $2, $3, $4) ON CONFLICT (transaction_id) DO NOTHING''', transaction_id, str(user_id), int(amount), status)
            return "INSERT" in result
    except Exception as e: logger.error(f"catat_payment_event error: {e}"); return False

async def aktifkan_premium(user_id, days=30):
    try:
        async with await get_db() as conn:
            await conn.execute('''UPDATE users SET premium_until = CURRENT_TIMESTAMP + ($1 || ' days')::interval WHERE user_id = $2''', str(days), str(user_id))
            return True
    except Exception as e: logger.error(f"aktifkan_premium error: {e}"); return False

async def cek_status_vip(user_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT premium_until FROM users WHERE user_id = $1", str(user_id))
            if row and row['premium_until']:
                if row['premium_until'] > datetime.datetime.now():
                    return True
            return False
    except Exception as e: logger.error(f"cek_status_vip error: {e}"); return False

async def get_unified_history(user_id):
    try:
        async with await get_db() as conn:
            tanggal_ini = datetime.date.today()
            food = await conn.fetch('''SELECT id, 'food' as type, nama_makanan as title, kalori as value, NULL::INTEGER as durasi, waktu FROM food_logs WHERE user_id = $1 AND tanggal = $2''', str(user_id), tanggal_ini)
            water = await conn.fetch('''SELECT id, 'water' as type, 'Air Minum' as title, ml as value, NULL::INTEGER as durasi, waktu FROM water_logs WHERE user_id = $1 AND tanggal = $2''', str(user_id), tanggal_ini)
            weight = await conn.fetch('''SELECT id, 'weight' as type, 'Timbang Berat' as title, berat as value, NULL::INTEGER as durasi, waktu FROM weight_logs WHERE user_id = $1 AND tanggal = $2''', str(user_id), tanggal_ini)
            workout = await conn.fetch('''SELECT id, 'workout' as type, olahraga as title, kalori_terbakar as value, durasi, waktu FROM workout_logs WHERE user_id = $1 AND tanggal = $2''', str(user_id), tanggal_ini)
            
            all_logs = list(food) + list(water) + list(weight) + list(workout)
            all_logs.sort(key=lambda x: x['waktu'] or datetime.datetime.min, reverse=True)
            
            result = []
            for row in all_logs:
                r = dict(row)
                if r['waktu']: r['waktu'] = r['waktu'].strftime("%H:%M")
                if r['type'] == 'weight' and r['value'] is not None: r['value'] = round(float(r['value']), 1)
                result.append(r)
            return result
    except Exception as e: logger.error(f"get_unified_history error: {e}"); return []

async def hapus_water_log_by_id(user_id, log_id):
    try:
        async with await get_db() as conn:
            result = await conn.execute('''DELETE FROM water_logs WHERE id = $1 AND user_id = $2''', int(log_id), str(user_id))
            return int(result.split(" ")[1]) > 0
    except Exception as e: logger.error(f"hapus_water_log_by_id error: {e}"); return False

async def hapus_weight_log_by_id(user_id, log_id):
    try:
        async with await get_db() as conn:
            result = await conn.execute('''DELETE FROM weight_logs WHERE id = $1 AND user_id = $2''', int(log_id), str(user_id))
            return int(result.split(" ")[1]) > 0
    except Exception as e: logger.error(f"hapus_weight_log_by_id error: {e}"); return False

async def hapus_workout_log_by_id(user_id, log_id):
    try:
        async with await get_db() as conn:
            result = await conn.execute('''DELETE FROM workout_logs WHERE id = $1 AND user_id = $2''', int(log_id), str(user_id))
            return int(result.split(" ")[1]) > 0
    except Exception as e: logger.error(f"hapus_workout_log_by_id error: {e}"); return False

async def get_statistik_user(user_id):
    try:
        async with await get_db() as conn:
            jumlah_makan = await conn.fetchval("SELECT COUNT(*) FROM food_logs WHERE user_id = $1", str(user_id))
            jumlah_air = await conn.fetchval("SELECT COUNT(*) FROM water_logs WHERE user_id = $1", str(user_id))
            jumlah_gym = await conn.fetchval("SELECT COUNT(*) FROM workout_logs WHERE user_id = $1", str(user_id))
            return {"makanan": jumlah_makan, "air": jumlah_air, "gym": jumlah_gym}
    except Exception as e: logger.error(f"get_statistik_user error: {e}"); return {"makanan": 0, "air": 0, "gym": 0}

async def get_user_full_stats(user_id):
    try:
        async with await get_db() as conn:
            total_food = await conn.fetchval("SELECT COUNT(*) FROM food_logs WHERE user_id = $1", str(user_id))
            total_water = await conn.fetchval("SELECT COUNT(*) FROM water_logs WHERE user_id = $1", str(user_id))
            total_workout = await conn.fetchval("SELECT COUNT(*) FROM workout_logs WHERE user_id = $1", str(user_id))
            days_active = await conn.fetchval("SELECT COUNT(DISTINCT tanggal) FROM (SELECT tanggal FROM food_logs WHERE user_id = $1 UNION SELECT tanggal FROM water_logs WHERE user_id = $1 UNION SELECT tanggal FROM workout_logs WHERE user_id = $1 UNION SELECT tanggal FROM weight_logs WHERE user_id = $1) t", str(user_id))
            total_water_ml = await conn.fetchval("SELECT COALESCE(SUM(ml), 0) FROM water_logs WHERE user_id = $1", str(user_id))
            total_kalori = await conn.fetchval("SELECT COALESCE(SUM(kalori), 0) FROM food_logs WHERE user_id = $1", str(user_id))
            total_burned = await conn.fetchval("SELECT COALESCE(SUM(kalori_terbakar), 0) FROM workout_logs WHERE user_id = $1", str(user_id))
            first_weight = await conn.fetchval("SELECT berat FROM weight_logs WHERE user_id = $1 ORDER BY tanggal ASC, id ASC LIMIT 1", str(user_id))
            last_weight = await conn.fetchval("SELECT berat FROM weight_logs WHERE user_id = $1 ORDER BY tanggal DESC, id DESC LIMIT 1", str(user_id))
            first_date = await conn.fetchval("SELECT MIN(tanggal) FROM (SELECT tanggal FROM food_logs WHERE user_id = $1 UNION SELECT tanggal FROM water_logs WHERE user_id = $1 UNION SELECT tanggal FROM workout_logs WHERE user_id = $1) t", str(user_id))
            
            return {
                "total_food": total_food or 0, "total_water": total_water or 0, "total_workout": total_workout or 0,
                "days_active": days_active or 0, "total_water_ml": total_water_ml or 0, "total_kalori": total_kalori or 0, "total_burned": total_burned or 0,
                "first_weight": round(float(first_weight), 1) if first_weight else None, "last_weight": round(float(last_weight), 1) if last_weight else None, "first_date": first_date
            }
    except Exception as e: logger.error(f"get_user_full_stats error: {e}"); return None

async def update_profile_web(user_id, berat, tinggi, target):
    try:
        async with await get_db() as conn:
            berat_float = round(float(berat), 1)
            tinggi_float = float(tinggi)
            await conn.execute('''UPDATE user_profiles SET berat = $1, tinggi = $2, updated_at = CURRENT_TIMESTAMP WHERE user_id = $3''', berat_float, tinggi_float, str(user_id))
            tanggal_ini = datetime.date.today()
            existing = await conn.fetchrow("SELECT id FROM weight_logs WHERE user_id = $1 AND tanggal = $2 ORDER BY id DESC LIMIT 1", str(user_id), tanggal_ini)
            if existing: await conn.execute("UPDATE weight_logs SET berat = $1 WHERE id = $2", berat_float, existing['id'])
            else: await conn.execute("INSERT INTO weight_logs (user_id, tanggal, berat) VALUES ($1, $2, $3)", str(user_id), tanggal_ini, berat_float)
            await conn.execute('''UPDATE gym_profile SET target = $1 WHERE user_id = $2''', target, str(user_id))
            return True
    except Exception as e: logger.error(f"update_profile_web error: {e}"); return False

async def request_access_db(user_id, username):
    try:
        async with await get_db() as conn:
            await conn.execute('''INSERT INTO users (user_id, nama) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING''', str(user_id), username)
            return True
    except Exception as e: logger.error(f"request_access_db error: {e}"); return False

async def approve_user_access(user_id, days=3):
    try:
        async with await get_db() as conn:
            await conn.execute('''UPDATE users SET premium_until = CURRENT_TIMESTAMP + ($1 || ' days')::interval, is_banned = FALSE, banned_at = NULL, banned_reason = NULL WHERE user_id = $2''', str(days), str(user_id))
            return True
    except Exception as e: logger.error(f"approve_user_access error: {e}"); return False

async def reject_user_access(user_id):
    try:
        async with await get_db() as conn:
            await conn.execute('DELETE FROM users WHERE user_id = $1', str(user_id))
            return True
    except Exception as e: logger.error(f"reject_user_access error: {e}"); return False

# ==========================================
# --- FUNGSI ADMIN MONITORING & KICK ---
# ==========================================
async def update_last_active(user_id):
    try:
        async with await get_db() as conn:
            await conn.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE user_id = $1", str(user_id))
    except Exception: pass

async def admin_get_stats():
    try:
        async with await get_db() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM users")
            active = await conn.fetchval("SELECT COUNT(*) FROM users WHERE premium_until > CURRENT_TIMESTAMP AND is_banned = FALSE")
            expired = await conn.fetchval("SELECT COUNT(*) FROM users WHERE premium_until <= CURRENT_TIMESTAMP AND is_banned = FALSE")
            banned = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_banned = TRUE")
            bandel = await conn.fetchval("SELECT COUNT(*) FROM users WHERE premium_until <= CURRENT_TIMESTAMP AND is_banned = FALSE AND last_active_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'")
            return {"total": total, "active": active, "expired": expired, "banned": banned, "bandel": bandel}
    except Exception as e: logger.error(f"admin_get_stats error: {e}"); return {"total": 0, "active": 0, "expired": 0, "banned": 0, "bandel": 0}

async def admin_list_users(filter_type, offset=0, limit=5):
    try:
        async with await get_db() as conn:
            if filter_type == 'active': cond = "premium_until > CURRENT_TIMESTAMP AND is_banned = FALSE"
            elif filter_type == 'expired': cond = "premium_until <= CURRENT_TIMESTAMP AND is_banned = FALSE"
            elif filter_type == 'banned': cond = "is_banned = TRUE"
            elif filter_type == 'bandel': cond = "premium_until <= CURRENT_TIMESTAMP AND is_banned = FALSE AND last_active_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'"
            else: cond = "1=1"
            query = f"SELECT user_id, nama, premium_until, created_at, last_active_at, is_banned FROM users WHERE {cond} ORDER BY created_at DESC OFFSET $1 LIMIT $2"
            users = await conn.fetch(query, offset, limit)
            count = await conn.fetchval(f"SELECT COUNT(*) FROM users WHERE {cond}")
            return users, count
    except Exception as e: logger.error(f"admin_list_users error: {e}"); return [], 0

async def admin_kick_user(user_id, reason="Melanggar aturan / Tidak bayar"):
    try:
        async with await get_db() as conn:
            await conn.execute('''UPDATE users SET is_banned = TRUE, premium_until = CURRENT_TIMESTAMP, banned_at = CURRENT_TIMESTAMP, banned_reason = $1 WHERE user_id = $2''', reason, str(user_id))
            return True
    except Exception as e: logger.error(f"admin_kick_user error: {e}"); return False

async def admin_unban_user(user_id, days=30):
    try:
        async with await get_db() as conn:
            await conn.execute('''UPDATE users SET is_banned = FALSE, banned_at = NULL, banned_reason = NULL, premium_until = CURRENT_TIMESTAMP + ($1 || ' days')::interval WHERE user_id = $2''', str(days), str(user_id))
            return True
    except Exception as e: logger.error(f"admin_unban_user error: {e}"); return False

# ==========================================
# --- FUNGSI STREAK (API) & REMINDER ---
# ==========================================
async def update_streak(user_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT current_streak, last_streak_date FROM users WHERE user_id = $1", str(user_id))
            if not row: return
            
            today = datetime.date.today()
            last_date = row['last_streak_date']
            
            if last_date == today: return 
                
            new_streak = 1
            if last_date == today - datetime.timedelta(days=1):
                new_streak = (row['current_streak'] or 0) + 1
                
            await conn.execute("UPDATE users SET current_streak = $1, last_streak_date = $2 WHERE user_id = $3", new_streak, today, str(user_id))
            logger.info(f"🔥 Streak user {user_id} naik jadi {new_streak}")
    except Exception as e: logger.error(f"update_streak error: {e}")

async def get_user_streak(user_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT current_streak, last_streak_date FROM users WHERE user_id = $1", str(user_id))
            if not row: return 0
            today = datetime.date.today()
            if row['last_streak_date'] == today - datetime.timedelta(days=1) or row['last_streak_date'] == today:
                return row['current_streak'] or 0
            return 0 
    except Exception as e: return 0

async def get_users_for_reminder():
    try:
        async with await get_db() as conn:
            # Ambil user yang reminder nyala, VIP, gak banned, 
            # dan belum log makanan dalam 4 jam terakhir (biar gak spam)
            rows = await conn.fetch('''
                SELECT u.user_id FROM users u
                WHERE u.reminder_enabled = TRUE AND u.is_banned = FALSE AND u.premium_until > CURRENT_TIMESTAMP
                AND (
                    NOT EXISTS (SELECT 1 FROM food_logs f WHERE f.user_id = u.user_id AND f.tanggal = CURRENT_DATE)
                    OR 
                    (SELECT MAX(waktu) FROM food_logs f WHERE f.user_id = u.user_id AND f.tanggal = CURRENT_DATE) < CURRENT_TIMESTAMP - INTERVAL '4 hours'
                )
            ''')
            return [row['user_id'] for row in rows]
    except Exception as e: 
        logger.error(f"get_users_for_reminder error: {e}")
        return []

async def toggle_reminder(user_id):
    try:
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT reminder_enabled FROM users WHERE user_id = $1", str(user_id))
            if not row: return False
            new_status = not row['reminder_enabled']
            await conn.execute("UPDATE users SET reminder_enabled = $1 WHERE user_id = $2", new_status, str(user_id))
            return new_status
    except Exception as e: logger.error(f"toggle_reminder error: {e}"); return False