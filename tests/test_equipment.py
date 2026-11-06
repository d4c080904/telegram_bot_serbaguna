import pytest
from services.equipment import proses_foto_alat_core

def test_proses_alat_sukses(mocker):
    """Test jalur sukses: AI ngasih teks penjelasan alat"""
    # Mock fungsi AI
    mocker.patch("services.equipment.analisis_alat_gym", return_value="🏋️ Nama Alat: Treadmill\n💪 Otot: Kaki")
    
    result = proses_foto_alat_core(image_bytes=b"fake_image_bytes")
    
    assert result["status"] == "success"
    assert "Treadmill" in result["data"]

def test_proses_alat_ai_gagal(mocker):
    """Test jalur AI gagal: Groq error / return None"""
    mocker.patch("services.equipment.analisis_alat_gym", return_value=None)
    
    result = proses_foto_alat_core(image_bytes=b"fake_image_bytes")
    
    assert result["status"] == "ai_failed"