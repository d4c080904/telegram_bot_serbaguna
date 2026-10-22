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

def migrasi_gym_table():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("PRAGMA table_info(gym_profile)")
        kolom_lama = [row[1] for row in c.fetchall()]

        # PERBAIKAN: 'updated_at' diubah jadi "TEXT" biar SQLite mau nambahin kolomnya
        kolom_baru = {
            'mode': "TEXT DEFAULT 'noob'",
            'umur': "INTEGER",
            'jenis_kelamin': "TEXT",
            'level': "TEXT",
            'pengalaman': "INTEGER",
            'frekuensi': "INTEGER",
            'alat': "TEXT",
            'updated_at': "TEXT" 
        }

        for nama_kolom, tipe in kolom_baru.items():
            if nama_kolom not in kolom_lama:
                try:
                    c.execute(f"ALTER TABLE gym_profile ADD COLUMN {nama_kolom} {tipe}")
                    logger.info(f"✅ Migrasi: tambah kolom gym_profile.{nama_kolom}")
                except Exception as e:
                    logger.warning(f"Migrasi {nama_kolom} gagal: {e}")

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"migrasi_gym_table error: {e}")

def setup_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS histori_chat (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, teks_asli TEXT, teks_rapi TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabel gym_profile versi baru (untuk database baru)
    cursor.execute('''CREATE TABLE IF NOT EXISTS gym_profile (user_id TEXT PRIMARY KEY, mode TEXT DEFAULT 'noob', umur INTEGER, berat REAL, tinggi REAL, jenis_kelamin TEXT, target TEXT, level TEXT, pengalaman INTEGER, frekuensi INTEGER, alat TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS gym_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, log_teks TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cache_ai (key TEXT PRIMARY KEY, hasil TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (user_id TEXT PRIMARY KEY, is_active INTEGER DEFAULT 0, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, role TEXT, content TEXT, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON histori_chat(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id, id)")

    conn.commit()
    conn.close()
    logger.info("✅ Database siap")
    migrasi_gym_table()