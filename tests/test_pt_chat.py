import pytest
from services.pt_chat import proses_chat_pt_core

def test_chat_pt_sukses(mocker):
    """Test jalur sukses: AI ngasih balasan, history tersimpan"""
    mocker.patch("services.pt_chat.chat_dengan_pt", return_value="Bro, buat cutting, kalori defisit 500 kcal aja.")
    mock_simpan = mocker.patch("services.pt_chat.simpan_chat_message")
    
    result = proses_chat_pt_core(user_id="user_123", teks="Gimana cara cutting bro?")
    
    assert result["status"] == "success"
    assert "cutting" in result["data"].lower()
    # Pastikan disimpan 2x: pesan user dan balasan AI
    assert mock_simpan.call_count == 2
    # Cek argumen pertama: pesan user
    mock_simpan.assert_any_call("user_123", "user", "Gimana cara cutting bro?")
    # Cek argumen kedua: balasan AI
    mock_simpan.assert_any_call("user_123", "assistant", "Bro, buat cutting, kalori defisit 500 kcal aja.")

def test_chat_pt_ai_gagal(mocker):
    """Test jalur AI gagal: balasan None, tidak simpan assistant message"""
    mocker.patch("services.pt_chat.chat_dengan_pt", return_value=None)
    mock_simpan = mocker.patch("services.pt_chat.simpan_chat_message")
    
    result = proses_chat_pt_core(user_id="user_123", teks="Halo PT")
    
    assert result["status"] == "ai_failed"
    # Cuma simpan pesan user, tidak simpan balasan AI
    assert mock_simpan.call_count == 1
    mock_simpan.assert_called_once_with("user_123", "user", "Halo PT")

def test_chat_pt_balasan_kepanjangan(mocker):
    """Test pemotongan balasan kalau > 4000 karakter"""
    balasan_panjang = "A" * 5000
    mocker.patch("services.pt_chat.chat_dengan_pt", return_value=balasan_panjang)
    mocker.patch("services.pt_chat.simpan_chat_message")
    
    result = proses_chat_pt_core(user_id="user_123", teks="Test")
    
    assert result["status"] == "success"
    assert "dipotong" in result["data"]
    assert len(result["data"]) < 5000