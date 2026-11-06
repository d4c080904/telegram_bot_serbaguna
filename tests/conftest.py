import pytest
import sqlite3
import os
import tempfile
from unittest.mock import MagicMock

# Set environment variable palsu sebelum import modul lain
os.environ["GROQ_API_KEY"] = "mock_api_key"
os.environ["TELEGRAM_BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

# ==========================================
# 1. MOCK GROQ DARI AKARNYA
# ==========================================
import bot_instance
bot_instance.groq_client = MagicMock()

# Mock daftar model biar services/ai.py nggak error pas import
mock_models = MagicMock()
mock_models.data = [MagicMock(id="llama-3.3-70b-versatile")]
bot_instance.groq_client.models.list.return_value = mock_models

import services.ai
# Timpa groq_client di services/ai dengan yang udah di-mock
services.ai.groq_client = bot_instance.groq_client
# Paksa list model vision cuma 1 biar test-nya cepet
services.ai.MODEL_VISION_LIST = ["mock-vision"]
services.ai.MODEL_GROQ_LIST = ["mock-groq"]

@pytest.fixture
def mock_groq():
    return bot_instance.groq_client


# ==========================================
# 2. FIX DATABASE FIXTURE (PAKAI FILE TEMP)
# ==========================================
@pytest.fixture(scope="function")
def test_db(mocker):
    """Bikin DB SQLite file temporary (nggak ganggu bot_history.db asli)"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    def mock_get_db():
        # Selalu buka koneksi baru ke file temp ini
        conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    # Patch get_db di queries.py biar ngarah ke file temp
    mocker.patch("database.queries.get_db", side_effect=mock_get_db)

    # Bikin tabel manual buat test
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Tabel Food Logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message_id INTEGER,
            photo_message_id INTEGER, photo_hash TEXT, tanggal DATE, nama_makanan TEXT,
            estimasi_porsi TEXT, kalori INTEGER, protein REAL, karbo REAL, lemak REAL,
            gula REAL DEFAULT 0.0, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_food_user_photohash ON food_logs(user_id, photo_hash) WHERE photo_hash IS NOT NULL")
    
    # 2. Tabel Wizard States (TAMBAHAN BARU)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wizard_states (
            user_id TEXT,
            state_type TEXT,
            step TEXT,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, state_type)
        )
    ''')

    conn.commit()
    conn.close()

    yield db_path

    # Hapus file temp setelah test selesai
    try:
        os.remove(db_path)
    except Exception:
        pass