import asyncpg
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

pool = None

async def create_pool():
    global pool
    if not pool:
        pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
        logger.info("✅ Connection Pool PostgreSQL siap")

async def close_pool():
    global pool
    if pool:
        await pool.close()
        logger.info("🔌 Connection Pool ditutup")

async def get_db():
    return pool.acquire()

async def setup_db():
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id VARCHAR(255) PRIMARY KEY, nama VARCHAR(255), umur INTEGER,
                berat REAL, tinggi REAL, jenis_kelamin VARCHAR(1), updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS histori_chat (id SERIAL PRIMARY KEY, user_id VARCHAR(255), username VARCHAR(255), teks_asli TEXT, teks_rapi TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS gym_profile (user_id VARCHAR(255) PRIMARY KEY, mode VARCHAR(50) DEFAULT 'noob', target VARCHAR(50), level VARCHAR(50), pengalaman INTEGER, frekuensi INTEGER, alat VARCHAR(50), updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS gym_logs (id SERIAL PRIMARY KEY, user_id VARCHAR(255), log_teks TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS cache_ai (key VARCHAR(255) PRIMARY KEY, hasil TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (user_id VARCHAR(255) PRIMARY KEY, is_active INTEGER DEFAULT 0, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS chat_messages (id SERIAL PRIMARY KEY, user_id VARCHAR(255), role VARCHAR(50), content TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS wizard_states (user_id VARCHAR(255), state_type VARCHAR(50), step VARCHAR(50), data TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, state_type))''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS food_logs (id SERIAL PRIMARY KEY, user_id VARCHAR(255), message_id INTEGER, photo_message_id INTEGER, photo_hash VARCHAR(255), tanggal DATE, nama_makanan TEXT, estimasi_porsi VARCHAR(255), kalori INTEGER, protein REAL, karbo REAL, lemak REAL, gula REAL DEFAULT 0.0, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS water_logs (id SERIAL PRIMARY KEY, user_id VARCHAR(255), tanggal DATE, ml INTEGER, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS weight_logs (id SERIAL PRIMARY KEY, user_id VARCHAR(255), tanggal DATE, berat REAL, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS workout_logs (
                id SERIAL PRIMARY KEY, 
                user_id VARCHAR(255), 
                tanggal DATE, 
                olahraga TEXT, 
                durasi INTEGER, 
                kalori_terbakar INTEGER, 
                waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # =====================================================================
        # --- TAMBAHAN FASE ENTERPRISE ---
        # =====================================================================

        # 1. Bikin tabel users (buat profil dasar & premium)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(255) PRIMARY KEY,
                nama VARCHAR(255),
                umur INTEGER,
                tinggi REAL,
                gender VARCHAR(1),
                target_weight REAL,
                premium_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Pindahin data lama dari user_profiles ke users (Biar data lu gak ilang)
        await conn.execute('''
            INSERT INTO users (user_id, nama, umur, tinggi, gender)
            SELECT user_id, nama, umur, tinggi, jenis_kelamin FROM user_profiles
            ON CONFLICT (user_id) DO NOTHING
        ''')

        # 3. Bikin VIEW daily_logs (Ngerangkum makanan, air, olahraga jadi 1 baris per tanggal)
        await conn.execute('''
            CREATE OR REPLACE VIEW daily_logs AS
            SELECT
                d.user_id,
                d.tanggal,
                COALESCE((SELECT SUM(ml) FROM water_logs WHERE user_id = d.user_id AND tanggal = d.tanggal), 0) AS total_air,
                COALESCE((SELECT SUM(kalori) FROM food_logs WHERE user_id = d.user_id AND tanggal = d.tanggal), 0) AS total_kalori_masuk,
                COALESCE((SELECT SUM(kalori_terbakar) FROM workout_logs WHERE user_id = d.user_id AND tanggal = d.tanggal), 0) AS total_kalori_keluar
            FROM (
                SELECT user_id, tanggal FROM food_logs
                UNION
                SELECT user_id, tanggal FROM water_logs
                UNION
                SELECT user_id, tanggal FROM workout_logs
            ) d
        ''')
        # =====================================================================

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON histori_chat(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id, id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_food_user ON food_logs(user_id, tanggal)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_water_user ON water_logs(user_id, tanggal)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_weight_user ON weight_logs(user_id, tanggal)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_workout_user ON workout_logs(user_id, tanggal)")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_food_user_photohash ON food_logs(user_id, photo_hash) WHERE photo_hash IS NOT NULL")
        
        logger.info("✅ Semua tabel PostgreSQL siap")