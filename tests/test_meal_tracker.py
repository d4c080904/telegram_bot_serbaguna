import pytest
from services.meal_tracker import proses_foto_makanan_core

def test_proses_foto_sukses(mocker):
    """Test jalur sukses: AI ngasih data, DB nyimpen"""
    # 1. Mock fungsi database & AI
    mocker.patch("services.meal_tracker.cek_duplikat_foto", return_value=False)
    mocker.patch("services.meal_tracker.analisis_foto_makanan", return_value={"nama_makanan": "Nasi Padang", "kalori": 700})
    mocker.patch("services.meal_tracker.tambah_food_log", return_value=True)
    
    # 2. Jalanin core function
    result = proses_foto_makanan_core(
        user_id="user_123",
        image_bytes=b"fake_image_bytes",
        caption="Nasi padang",
        message_id=111,
        photo_message_id=222
    )
    
    # 3. Assert hasilnya
    assert result["status"] == "success"
    assert result["data"]["nama_makanan"] == "Nasi Padang"

def test_proses_foto_duplikat(mocker):
    """Test jalur duplikat: DB bilang foto udah ada"""
    mocker.patch("services.meal_tracker.cek_duplikat_foto", return_value=True)
    
    result = proses_foto_makanan_core(
        user_id="user_123",
        image_bytes=b"fake_image_bytes",
        caption="",
        message_id=111,
        photo_message_id=222
    )
    
    assert result["status"] == "duplicate"

def test_proses_foto_ai_gagal(mocker):
    """Test jalur AI gagal: Groq error / return None"""
    mocker.patch("services.meal_tracker.cek_duplikat_foto", return_value=False)
    mocker.patch("services.meal_tracker.analisis_foto_makanan", return_value=None)
    
    result = proses_foto_makanan_core(
        user_id="user_123",
        image_bytes=b"fake_image_bytes",
        caption="",
        message_id=111,
        photo_message_id=222
    )
    
    assert result["status"] == "ai_failed"