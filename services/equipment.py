import logging
from services.ai import analisis_alat_gym

logger = logging.getLogger(__name__)

def proses_foto_alat_core(image_bytes: bytes) -> dict:
    """
    Fungsi murni untuk memproses foto alat gym.
    Bebas dari dependensi Telegram API.
    """
    try:
        hasil_teks = analisis_alat_gym(image_bytes)
        
        if not hasil_teks:
            return {"status": "ai_failed"}
            
        return {"status": "success", "data": hasil_teks}
        
    except Exception as e:
        logger.error(f"proses_foto_alat_core error: {e}")
        return {"status": "error", "message": str(e)}