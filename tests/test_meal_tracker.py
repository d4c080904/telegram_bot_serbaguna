import pytest
from services.meal_tracker import proses_foto_makanan_core, proses_koreksi_makanan_core

# --- TEST FOTO MAKANAN ---
def test_proses_foto_sukses(mocker):
    mocker.patch("services.meal_tracker.cek_duplikat_foto", return_value=False)
    mocker.patch("services.meal_tracker.analisis_foto_makanan", return_value={"nama_makanan": "Nasi Padang", "kalori": 700})
    mocker.patch("services.meal_tracker.tambah_food_log", return_value=True)
    
    result = proses_foto_makanan_core(
        user_id="user_123", image_bytes=b"fake_image", caption="Nasi padang",
        message_id=111, photo_message_id=222
    )
    
    assert result["status"] == "success"
    assert result["data"]["nama_makanan"] == "Nasi Padang"

def test_proses_foto_duplikat(mocker):
    mocker.patch("services.meal_tracker.cek_duplikat_foto", return_value=True)
    result = proses_foto_makanan_core(
        user_id="user_123", image_bytes=b"fake_image", caption="",
        message_id=111, photo_message_id=222
    )
    assert result["status"] == "duplicate"

def test_proses_foto_ai_gagal(mocker):
    mocker.patch("services.meal_tracker.cek_duplikat_foto", return_value=False)
    mocker.patch("services.meal_tracker.analisis_foto_makanan", return_value=None)
    result = proses_foto_makanan_core(
        user_id="user_123", image_bytes=b"fake_image", caption="",
        message_id=111, photo_message_id=222
    )
    assert result["status"] == "ai_failed"

# --- TEST KOREKSI MAKANAN ---
def test_proses_koreksi_sukses(mocker):
    """Test koreksi teks: AI sukses, DB sukses update"""
    mocker.patch("services.meal_tracker.koreksi_foto_makanan", return_value={"nama_makanan": "Nasi Uduk", "kalori": 600})
    mocker.patch("services.meal_tracker.update_food_log", return_value=True)
    
    result = proses_koreksi_makanan_core(
        user_id="user_123", reply_msg_id=111, teks_koreksi="Bukan nasi padang, tapi nasi uduk"
    )
    
    assert result["status"] == "success"
    assert result["data"]["nama_makanan"] == "Nasi Uduk"

def test_proses_koreksi_ai_gagal(mocker):
    """Test koreksi teks: AI error / return None"""
    mocker.patch("services.meal_tracker.koreksi_foto_makanan", return_value=None)
    
    result = proses_koreksi_makanan_core(
        user_id="user_123", reply_msg_id=111, teks_koreksi="Salah nih"
    )
    
    assert result["status"] == "ai_failed"