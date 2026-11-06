import hashlib
import logging
from database.queries import cek_duplikat_foto, tambah_food_log, update_food_log
from services.ai import analisis_foto_makanan, koreksi_foto_makanan

logger = logging.getLogger(__name__)

def proses_foto_makanan_core(user_id: str, image_bytes: bytes, caption: str, message_id: int, photo_message_id: int) -> dict:
    """Fungsi murni untuk memproses foto makanan."""
    try:
        photo_hash = hashlib.md5(image_bytes).hexdigest()
        
        if cek_duplikat_foto(user_id, photo_hash):
            return {"status": "duplicate"}
            
        hasil = analisis_foto_makanan(image_bytes, caption)
        if not hasil:
            return {"status": "ai_failed"}
            
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

def proses_koreksi_makanan_core(user_id: str, reply_msg_id: int, teks_koreksi: str) -> dict:
    """Fungsi murni untuk memproses koreksi makanan via teks."""
    try:
        # 1. Panggil AI
        hasil_baru = koreksi_foto_makanan(teks_koreksi)
        if not hasil_baru:
            return {"status": "ai_failed"}
            
        # 2. Update DB
        berhasil = update_food_log(
            user_id, reply_msg_id,
            hasil_baru.get('nama_makanan', 'Makanan'), hasil_baru.get('estimasi_porsi', '1 porsi'), 
            hasil_baru.get('kalori', 0), hasil_baru.get('protein', 0), 
            hasil_baru.get('karbo', 0), hasil_baru.get('lemak', 0), hasil_baru.get('gula', 0)
        )
        
        if not berhasil:
            return {"status": "db_failed"}
            
        return {"status": "success", "data": hasil_baru}
        
    except Exception as e:
        logger.error(f"proses_koreksi_makanan_core error: {e}")
        return {"status": "error", "message": str(e)}