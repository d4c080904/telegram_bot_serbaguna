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
    # Ngembaliin koneksi dari pool (harus dipake pake `async with`)
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
        
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON histori_chat(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id, id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_food_user ON food_logs(user_id, tanggal)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_water_user ON water_logs(user_id, tanggal)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_weight_user ON weight_logs(user_id, tanggal)")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_food_user_photohash ON food_logs(user_id, photo_hash) WHERE photo_hash IS NOT NULL")
        
        logger.info("✅ Semua tabel PostgreSQL siap")