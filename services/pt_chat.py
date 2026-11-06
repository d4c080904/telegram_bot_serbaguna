import logging
from database.queries import simpan_chat_message
from services.ai import chat_dengan_pt

logger = logging.getLogger(__name__)

def proses_chat_pt_core(user_id: str, teks: str) -> dict:
    """
    Fungsi murni orkestrasi chat PT:
    simpan pesan user -> panggil AI -> simpan balasan AI.
    Bebas dari dependensi Telegram API.
    """
    try:
        # 1. Simpan pesan user ke history
        simpan_chat_message(user_id, "user", teks)
        
        # 2. Panggil AI
        balasan = chat_dengan_pt(user_id, teks)
        
        if not balasan:
            return {"status": "ai_failed"}
            
        # 3. Simpan balasan AI ke history
        simpan_chat_message(user_id, "assistant", balasan)
        
        # 4. Potong kalau kelamaan (limit Telegram 4096 karakter)
        if len(balasan) > 4000:
            balasan = balasan[:4000] + "\n\n[...dipotong]"
            
        return {"status": "success", "data": balasan}
        
    except Exception as e:
        logger.error(f"proses_chat_pt_core error: {e}")
        return {"status": "error", "message": str(e)}