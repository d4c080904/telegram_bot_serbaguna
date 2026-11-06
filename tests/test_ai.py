import json
from services.ai import koreksi_foto_makanan

def test_koreksi_foto_sukses(mock_groq, test_db):
    """Test AI ngembaliin JSON yang valid"""
    # Siapin respons palsu dari Groq
    mock_response = mock_groq.chat.completions.create.return_value
    mock_response.choices = [
        type('Choice', (), {'message': type('Message', (), {'content': '{"nama_makanan": "Nasi Padang", "estimasi_porsi": "1 porsi", "kalori": 700, "protein": 30, "karbo": 80, "lemak": 25, "gula": 2}'})()})()
    ]
    
    hasil = koreksi_foto_makanan("Itu bukan nasi padang, tapi nasi uduk")
    
    assert hasil is not None
    assert hasil["nama_makanan"] == "Nasi Padang"
    assert hasil["kalori"] == 700
    
    # Pastiin AI dipanggil pake model yang bener
    mock_groq.chat.completions.create.assert_called_once()

def test_koreksi_foto_malformed_json(mock_groq, test_db):
    """Test kalau AI ngasih jawaban ngaco (bukan JSON)"""
    # Mock Groq ngembaliin teks biasa
    mock_response = mock_groq.chat.completions.create.return_value
    mock_response.choices = [
        type('Choice', (), {'message': type('Message', (), {'content': 'Maaf, saya tidak bisa menganalisis foto ini.'})()})()
    ]
    
    # Harusnya nangkep exception json.loads dan return None
    hasil = koreksi_foto_makanan("Ganti jadi ayam")
    assert hasil is None

def test_koreksi_foto_api_error(mock_groq, test_db):
    """Test kalau Groq API error/timeout"""
    # Mock Groq ngasih Exception
    mock_groq.chat.completions.create.side_effect = Exception("Groq Timeout")
    
    # Harusnya nangkep exception dan lanjut ke fallback model, ujung-ujungnya None
    hasil = koreksi_foto_makanan("Ganti jadi ayam")
    assert hasil is None