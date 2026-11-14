import logging
import hashlib
import hmac
import json
from urllib.parse import parse_qsl
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from database.queries import catat_payment_event, aktifkan_premium, get_db, cek_status_vip, tambah_food_log
from services.ai import analisis_foto_makanan, analisis_teks_makanan
from bot_instance import bot

logger = logging.getLogger(__name__)
app = FastAPI()

def verify_telegram_data(init_data: str) -> dict:
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data:
            return None
        hash_received = parsed_data.pop("hash")
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(parsed_data.items())])
        secret_key = hmac.new(b"WebAppData", bot.token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash == hash_received:
            return json.loads(parsed_data.get("user", "{}"))
        return None
    except Exception as e:
        logger.error(f"Verify error: {e}")
        return None

@app.post("/webhook/qris")
async def webhook_qris(request: Request):
    try:
        data = await request.json()
        trx_id = data.get("transaction_id")
        user_id = data.get("user_id")
        amount = data.get("amount")
        status = data.get("status")
        
        if status != "SUCCESS": return {"status": "ignored"}
            
        is_new = await catat_payment_event(trx_id, user_id, amount, status)
        if not is_new: return {"status": "success", "message": "Duplikat"}
            
        await aktifkan_premium(user_id, days=30)
        await bot.send_message(chat_id=user_id, text="👑 <b>PEMBAYARAN BERHASIL!</b>", parse_mode="HTML")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- ENDPOINT CHART DATA (YANG BENER) ---
@app.get("/api/chart_data")
async def get_chart_data(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not init_data: 
        raise HTTPException(status_code=401, detail="Bukan dari Telegram")

    user_data = verify_telegram_data(init_data)
    if not user_data: 
        raise HTTPException(status_code=401, detail="Data tidak valid")

    user_id = str(user_data.get("id"))
    is_vip = await cek_status_vip(user_id)
    
    if not is_vip:
        raise HTTPException(status_code=403, detail="Akses ditolak: Anda bukan VIP")

    try:
        async with await get_db() as conn:
            daily = await conn.fetch("""
                SELECT tanggal, total_kalori_masuk, total_kalori_keluar, total_air 
                FROM daily_logs WHERE user_id = $1 ORDER BY tanggal DESC LIMIT 7
            """, user_id)
            weight = await conn.fetch("""
                SELECT tanggal, berat FROM weight_logs WHERE user_id = $1 ORDER BY tanggal DESC LIMIT 7
            """, user_id)
            
            # INI DIA YANG BIKIN NULL SEBELUMNYA, SEKARANG UDAH BENER
            return {
                "daily": [dict(row) for row in reversed(daily)],
                "weight": [dict(row) for row in reversed(weight)]
            }
    except Exception as e:
        logger.error(f"API Chart Error: {e}")
        return {"error": str(e)}

# --- ENDPOINT LOG MAKANAN (DARI FASE 1) ---
@app.post("/api/log_food")
async def log_food(
    request: Request,
    food_text: str = Form(None),
    food_image: UploadFile = File(None)
):
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not init_data: raise HTTPException(status_code=401, detail="Bukan dari Telegram")
    
    user_data = verify_telegram_data(init_data)
    if not user_data: raise HTTPException(status_code=401, detail="Data tidak valid")
    
    user_id = str(user_data.get("id"))
    is_vip = await cek_status_vip(user_id)
    if not is_vip: raise HTTPException(status_code=403, detail="Akses ditolak: Anda bukan VIP")

    try:
        hasil = None
        if food_image:
            image_bytes = await food_image.read()
            caption = food_text or ""
            hasil = await analisis_foto_makanan(image_bytes, caption)
        elif food_text:
            hasil = await analisis_teks_makanan(food_text)
        
        if not hasil:
            raise HTTPException(status_code=400, detail="AI gagal menganalisis makanan.")

        berhasil = await tambah_food_log(
            user_id, 0, 0, None, 
            hasil.get('nama_makanan', 'Makanan'), hasil.get('estimasi_porsi', '1 porsi'),
            hasil.get('kalori', 0), hasil.get('protein', 0), hasil.get('karbo', 0),
            hasil.get('lemak', 0), hasil.get('gula', 0)
        )
        
        if not berhasil:
            raise HTTPException(status_code=500, detail="Gagal simpan ke database")

        return {"status": "success", "data": hasil}
    except Exception as e:
        logger.error(f"Log food error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def serve_mini_app():
    with open("webapp/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)