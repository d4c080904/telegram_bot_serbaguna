import logging
from database.queries import simpan_chat_message
from services.ai import chat_dengan_pt

logger = logging.getLogger(__name__)

async def proses_chat_pt_core(user_id: str, teks: str) -> dict:
    try:
        # FIX: Tambahin await
        await simpan_chat_message(user_id, "user", teks)
        
        balasan = await chat_dengan_pt(user_id, teks)
        if not balasan:
            return {"status": "ai_failed"}
            
        # FIX: Tambahin await
        await simpan_chat_message(user_id, "assistant", balasan)
        
        if len(balasan) > 4000:
            balasan = balasan[:4000] + "\n\n[...dipotong]"
            
        return {"status": "success", "data": balasan}
        
    except Exception as e:
        logger.error(f"proses_chat_pt_core error: {e}")
        return {"status": "error", "message": str(e)}