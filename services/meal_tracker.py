import hashlib
import logging
from database.queries import cek_duplikat_foto, tambah_food_log
from services.ai import analisis_foto_makanan

logger = logging.getLogger(__name__)

def proses_foto_makanan_core(user_id: str, image_bytes: bytes, caption: str, message_id: int, photo_message_id: int) -> dict:
    """
    Fungsi murni untuk memproses foto makanan.
    Bebas dari dependensi Telegram API (bot/telebot).
    """
    try:
        photo_hash = hashlib.md5(image_bytes).hexdigest()
        
        # 1. Cek Duplikat
        if cek_duplikat_foto(user_id, photo_hash):
            return {"status": "duplicate"}
            
        # 2. Panggil AI
        hasil = analisis_foto_makanan(image_bytes, caption)
        if not hasil:
            return {"status": "ai_failed"}
            
        # 3. Simpan ke DB
        berhasil = tambah_food_log(
            user_id, message_id, photo_message_id, photo_hash, 
            hasil.get('nama_makanan', 'Makanan'), hasil.get('estimasi_porsi', '1 porsi'), 
            hasil.get('kalori', 0), hasil.get('protein', 0), hasil.get('karbo', 0), 
            hasil.get('lemak', 0), hasil.get('gula', 0)
        )
        
        if not berhasil:
            return {"status": "db_failed"}
            
        return {"status": "success", "data": hasil}
        
    except Exception as e:
        logger.error(f"proses_foto_makanan_core error: {e}")
        return {"status": "error", "message": str(e)}