import pytest
from services.equipment import proses_foto_alat_core

@pytest.mark.asyncio
async def test_proses_alat_sukses(mocker):
    """Test jalur sukses: AI ngasih teks penjelasan alat"""
    # Mock fungsi AI (harus AsyncMock karena analisis_alat_gym adalah async)
    mock_ai = mocker.patch("services.equipment.analisis_alat_gym", new_callable=mocker.AsyncMock)
    mock_ai.return_value = "🏋️ Nama Alat: Treadmill\n💪 Otot: Kaki"

    result = await proses_foto_alat_core(image_bytes=b"fake_image_bytes")

    assert result["status"] == "success"
    assert "Treadmill" in result["data"]

@pytest.mark.asyncio
async def test_proses_alat_ai_gagal(mocker):
    """Test jalur AI gagal: Groq error / return None"""
    mock_ai = mocker.patch("services.equipment.analisis_alat_gym", new_callable=mocker.AsyncMock)
    mock_ai.return_value = None

    result = await proses_foto_alat_core(image_bytes=b"fake_image_bytes")

    assert result["status"] == "ai_failed"