import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from database.queries import catat_payment_event, aktifkan_premium, get_db
from bot_instance import bot

logger = logging.getLogger(__name__)
app = FastAPI()

# --- WEBHOOK PAYMENT (YANG UDAH ADA) ---
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

# --- ENDPOINT BUAT MINI APP (BARU) ---
@app.get("/api/chart_data/{user_id}")
async def get_chart_data(user_id: str):
    try:
        async with await get_db() as conn:
            # 1. Ambil data harian dari VIEW daily_logs (7 hari terakhir)
            daily = await conn.fetch("""
                SELECT tanggal, total_kalori_masuk, total_kalori_keluar, total_air 
                FROM daily_logs 
                WHERE user_id = $1 
                ORDER BY tanggal DESC LIMIT 7
            """, str(user_id))
            
            # 2. Ambil data berat badan (7 hari terakhir)
            weight = await conn.fetch("""
                SELECT tanggal, berat 
                FROM weight_logs 
                WHERE user_id = $1 
                ORDER BY tanggal DESC LIMIT 7
            """, str(user_id))
            
            # Balikin dalam format JSON
            return {
                "daily": [dict(row) for row in reversed(daily)],
                "weight": [dict(row) for row in reversed(weight)]
            }
    except Exception as e:
        logger.error(f"API Chart Error: {e}")
        return {"error": str(e)}

# --- SERVE FILE HTML (Mini App) ---
@app.get("/", response_class=HTMLResponse)
async def serve_mini_app():
    # Nanti kita taruh file HTML-nya di folder 'webapp'
    try:
        with open("webapp/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Web App belum dibuat.</h1>", status_code=404)