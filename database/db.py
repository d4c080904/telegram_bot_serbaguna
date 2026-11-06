import psycopg2
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def setup_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id VARCHAR(255) PRIMARY KEY,
            nama VARCHAR(255),
            umur INTEGER,
            berat REAL,
            tinggi REAL,
            jenis_kelamin VARCHAR(1),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS histori_chat (id SERIAL PRIMARY KEY, user_id VARCHAR(255), username VARCHAR(255), teks_asli TEXT, teks_rapi TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gym_profile (user_id VARCHAR(255) PRIMARY KEY, mode VARCHAR(50) DEFAULT 'noob', target VARCHAR(50), level VARCHAR(50), pengalaman INTEGER, frekuensi INTEGER, alat VARCHAR(50), updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gym_logs (id SERIAL PRIMARY KEY, user_id VARCHAR(255), log_teks TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cache_ai (key VARCHAR(255) PRIMARY KEY, hasil TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (user_id VARCHAR(255) PRIMARY KEY, is_active INTEGER DEFAULT 0, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_messages (id SERIAL PRIMARY KEY, user_id VARCHAR(255), role VARCHAR(50), content TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wizard_states (
            user_id VARCHAR(255),
            state_type VARCHAR(50),
            step VARCHAR(50),
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, state_type)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id SERIAL PRIMARY KEY, user_id VARCHAR(255), message_id INTEGER,
            photo_message_id INTEGER, photo_hash VARCHAR(255), tanggal DATE, nama_makanan TEXT,
            estimasi_porsi VARCHAR(255), kalori INTEGER, protein REAL, karbo REAL, lemak REAL,
            gula REAL DEFAULT 0.0, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS water_logs (
            id SERIAL PRIMARY KEY, user_id VARCHAR(255), tanggal DATE, ml INTEGER, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id SERIAL PRIMARY KEY, user_id VARCHAR(255), tanggal DATE, berat REAL, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON histori_chat(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id, id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_user ON food_logs(user_id, tanggal)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_water_user ON water_logs(user_id, tanggal)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_weight_user ON weight_logs(user_id, tanggal)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_food_user_photohash ON food_logs(user_id, photo_hash) WHERE photo_hash IS NOT NULL")

    conn.commit()
    conn.close()
    logger.info("✅ Database PostgreSQL siap")