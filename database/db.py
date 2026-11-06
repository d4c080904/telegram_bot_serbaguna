import sqlite3
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def setup_db():
    conn = get_db()
    cursor = conn.cursor()

    # TABEL BARU: USER PROFILES (Data Utama)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            nama TEXT,
            umur INTEGER,
            berat REAL,
            tinggi REAL,
            jenis_kelamin TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabel lama tetap ada
    cursor.execute('''CREATE TABLE IF NOT EXISTS histori_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, teks_asli TEXT, teks_rapi TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gym_profile (user_id TEXT PRIMARY KEY, mode TEXT DEFAULT 'noob', target TEXT, level TEXT, pengalaman INTEGER, frekuensi INTEGER, alat TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gym_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, log_teks TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cache_ai (key TEXT PRIMARY KEY, hasil TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (user_id TEXT PRIMARY KEY, is_active INTEGER DEFAULT 0, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, role TEXT, content TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # --- TAMBAHAN BARU: Tabel untuk State Wizard (Onboarding & Gym) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wizard_states (
            user_id TEXT,
            state_type TEXT,
            step TEXT,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, state_type) -- <--- FIX: Composite Primary Key
        )
    ''')

    # --- MIGRASI OTOMATIS: Cek kalau tabel lama masih pakai single primary key ---
    cursor.execute("PRAGMA table_info(wizard_states)")
    cols = cursor.fetchall()
    pk_count = sum(1 for col in cols if col[5] > 0) # col[5] adalah urutan PK
    
    if pk_count == 1:
        logger.info("🔄 Migrasi tabel wizard_states ke composite primary key...")
        cursor.execute("ALTER TABLE wizard_states RENAME TO wizard_states_old")
        cursor.execute('''
            CREATE TABLE wizard_states (
                user_id TEXT,
                state_type TEXT,
                step TEXT,
                data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, state_type)
            )
        ''')
        cursor.execute("INSERT INTO wizard_states (user_id, state_type, step, data, updated_at) SELECT user_id, state_type, step, data, updated_at FROM wizard_states_old")
        cursor.execute("DROP TABLE wizard_states_old")
        logger.info("✅ Migrasi wizard_states selesai!")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message_id INTEGER,
            photo_message_id INTEGER, photo_hash TEXT, tanggal DATE, nama_makanan TEXT,
            estimasi_porsi TEXT, kalori INTEGER, protein REAL, karbo REAL, lemak REAL,
            gula REAL DEFAULT 0.0, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, tanggal DATE, ml INTEGER, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, tanggal DATE, berat REAL, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Index biasa
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON histori_chat(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id, id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_user ON food_logs(user_id, tanggal)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_water_user ON water_logs(user_id, tanggal)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_weight_user ON weight_logs(user_id, tanggal)")
    
    # --- TAMBAHAN STEP 2: Anti Duplikat Foto (Unique Index) ---
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_food_user_photohash ON food_logs(user_id, photo_hash) WHERE photo_hash IS NOT NULL")

    conn.commit()
    conn.close()
    logger.info("✅ Database siap")