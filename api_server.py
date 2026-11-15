import logging
import hashlib
import hmac
import json
from urllib.parse import parse_qsl
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from database.queries import (
    catat_payment_event, aktifkan_premium, get_db, cek_status_vip, 
    tambah_food_log, tambah_air, update_user_weight, 
    get_history_makanan_hari_ini, hapus_food_log_by_id, get_unified_history,
    hapus_water_log_by_id, hapus_weight_log_by_id, tambah_workout_log, get_statistik_user,
    get_user_profile, get_gym_profile, update_profile_web,
    ambil_chat_history, simpan_chat_message, hapus_chat_history
)
from services.ai import analisis_foto_makanan, analisis_teks_makanan, estimasi_kalori_olahraga, analisis_alat_gym

# ✅ FIX: Import fungsi yang BENAR dari services/pt_chat.py
# Signature: proses_chat_pt_core(user_id: str, teks: str) -> dict
# Return: {"status": "success", "data": "..."} atau {"status": "ai_failed"} atau {"status": "error", "message": "..."}
# CATATAN: Fungsi ini SUDAH nyimpen chat ke DB (chat_messages) secara internal!
from services.pt_chat import proses_chat_pt_core

from bot_instance import bot

logger = logging.getLogger(__name__)
app = FastAPI()


def verify_telegram_data(init_data: str) -> dict:
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data: return None
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


async def get_vip_user(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not init_data: raise HTTPException(status_code=401, detail="Bukan dari Telegram")
    user_data = verify_telegram_data(init_data)
    if not user_data: raise HTTPException(status_code=401, detail="Data tidak valid")
    user_id = str(user_data.get("id"))
    is_vip = await cek_status_vip(user_id)
    if not is_vip: raise HTTPException(status_code=403, detail="Akses ditolak: Anda bukan VIP")
    return user_id


@app.post("/webhook/qris")
async def webhook_qris(request: Request):
    try:
        data = await request.json()
        trx_id, user_id, amount, status = data.get("transaction_id"), data.get("user_id"), data.get("amount"), data.get("status")
        if status == "SUCCESS":
            if await catat_payment_event(trx_id, user_id, amount, status):
                await aktifkan_premium(user_id, days=30)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500)


@app.get("/api/chart_data")
async def get_chart_data(request: Request):
    user_id = await get_vip_user(request)
    try:
        async with await get_db() as conn:
            daily = await conn.fetch("SELECT tanggal, total_kalori_masuk, total_kalori_keluar, total_air FROM daily_logs WHERE user_id = $1 ORDER BY tanggal DESC LIMIT 7", user_id)
            weight = await conn.fetch("SELECT tanggal, berat FROM weight_logs WHERE user_id = $1 ORDER BY tanggal DESC LIMIT 7", user_id)
            return {
                "daily": [dict(row) for row in reversed(daily)],
                "weight": [dict(row) for row in reversed(weight)]
            }
    except Exception as e:
        logger.error(f"API Chart Error: {e}")
        return {"error": str(e)}


@app.post("/api/log_food")
async def log_food(request: Request, food_text: str = Form(None), food_image: UploadFile = File(None)):
    user_id = await get_vip_user(request)
    try:
        hasil = None
        if food_image:
            image_bytes = await food_image.read()
            hasil = await analisis_foto_makanan(image_bytes, food_text or "")
        elif food_text:
            hasil = await analisis_teks_makanan(food_text)
        
        if not hasil: raise HTTPException(status_code=400, detail="AI gagal menganalisis.")
        berhasil = await tambah_food_log(user_id, 0, 0, None, hasil.get('nama_makanan', 'Makanan'), hasil.get('estimasi_porsi', '1 porsi'), hasil.get('kalori', 0), hasil.get('protein', 0), hasil.get('karbo', 0), hasil.get('lemak', 0), hasil.get('gula', 0))
        if not berhasil: raise HTTPException(status_code=500, detail="Gagal simpan ke database")
        return {"status": "success", "data": hasil}
    except Exception as e:
        logger.error(f"Log food error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/log_water")
async def log_water(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    ml = data.get("ml")
    if not ml: raise HTTPException(status_code=400, detail="Jumlah ml kosong")
    
    berhasil = await tambah_air(user_id, int(ml))
    if berhasil: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Gagal simpan air")


@app.post("/api/log_weight")
async def log_weight(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    berat = data.get("berat")
    if not berat: raise HTTPException(status_code=400, detail="Berat kosong")
    
    berhasil = await update_user_weight(user_id, float(berat))
    if berhasil: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Gagal simpan berat")


@app.post("/api/log_workout")
async def log_workout(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    teks_olahraga = data.get("teks")
    if not teks_olahraga: raise HTTPException(status_code=400, detail="Teks olahraga kosong")
    
    try:
        profil = await get_user_profile(user_id)
        berat = profil['berat'] if profil and profil.get('berat') else 70
        
        hasil_ai = await estimasi_kalori_olahraga(teks_olahraga, berat)
        if not hasil_ai: raise HTTPException(status_code=400, detail="AI gagal memahami olahraga lu.")
        
        olahraga = hasil_ai.get('olahraga', 'Olahraga')
        durasi = hasil_ai.get('durasi', 30)
        kalori = hasil_ai.get('kalori_terbakar', 200)
        
        berhasil = await tambah_workout_log(user_id, olahraga, durasi, kalori)
        if not berhasil: raise HTTPException(status_code=500, detail="Gagal simpan ke database")
        
        return {"status": "success", "data": {"olahraga": olahraga, "durasi": durasi, "kalori": kalori}}
    except Exception as e:
        logger.error(f"Log workout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_stats")
async def get_stats(request: Request):
    user_id = await get_vip_user(request)
    stats = await get_statistik_user(user_id)
    return {"stats": stats}


@app.get("/api/profile")
async def api_get_profile(request: Request):
    user_id = await get_vip_user(request)
    profil = await get_gym_profile(user_id)
    if not profil:
        raise HTTPException(status_code=404, detail="Profil tidak ditemukan")
    bmi = profil['berat'] / ((profil['tinggi']/100) ** 2) if profil['berat'] and profil['tinggi'] else 0
    return {
        "nama": profil['nama'],
        "umur": profil['umur'],
        "berat": profil['berat'],
        "tinggi": profil['tinggi'],
        "target": profil['target'] or 'recomp',
        "bmi": round(bmi, 1)
    }


@app.post("/api/profile")
async def api_update_profile(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    berat = data.get("berat")
    tinggi = data.get("tinggi")
    target = data.get("target")
    
    if not all([berat, tinggi, target]):
        raise HTTPException(status_code=400, detail="Data tidak lengkap")
        
    berhasil = await update_profile_web(user_id, float(berat), float(tinggi), target)
    if berhasil: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Gagal update profil")


@app.post("/api/scan_equipment")
async def api_scan_equipment(request: Request, equipment_image: UploadFile = File(...)):
    user_id = await get_vip_user(request)
    try:
        image_bytes = await equipment_image.read()
        hasil = await analisis_alat_gym(image_bytes)
        if not hasil: raise HTTPException(status_code=400, detail="AI gagal mengenali alat.")
        return {"status": "success", "data": hasil}
    except Exception as e:
        logger.error(f"Scan equipment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- CHAT PT AI (FIXED) ---
@app.get("/api/chat/history")
async def api_chat_history(request: Request):
    user_id = await get_vip_user(request)
    try:
        history = await ambil_chat_history(user_id)
        return {"history": history}
    except Exception as e:
        logger.error(f"Chat history error: {e}")
        return {"history": []}


@app.post("/api/chat/send")
async def api_chat_send(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    pesan = data.get("pesan", "").strip()
    if not pesan:
        raise HTTPException(status_code=400, detail="Pesan kosong")
    
    try:
        # ✅ proses_chat_pt_core SUDAH handle simpan user msg + assistant msg ke DB
        # Jadi kita TIDAK simpan lagi di sini (biar gak duplikat)
        # Signature: proses_chat_pt_core(user_id, teks) -> dict
        result = await proses_chat_pt_core(user_id, pesan)
        
        # Handle return type dict
        if result.get("status") == "success":
            return {"status": "success", "response": result.get("data", "")}
        elif result.get("status") == "ai_failed":
            raise HTTPException(status_code=500, detail="AI gagal merespon. Coba lagi.")
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "Error tidak diketahui"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/clear")
async def api_chat_clear(request: Request):
    user_id = await get_vip_user(request)
    berhasil = await hapus_chat_history(user_id)
    if berhasil:
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Gagal hapus chat")


@app.get("/api/unified_history")
async def api_unified_history(request: Request):
    user_id = await get_vip_user(request)
    history = await get_unified_history(user_id)
    return {"history": history}


@app.delete("/api/delete_log/{log_type}/{log_id}")
async def delete_log(request: Request, log_type: str, log_id: int):
    user_id = await get_vip_user(request)
    
    if log_type == 'food':
        berhasil = await hapus_food_log_by_id(user_id, log_id)
    elif log_type == 'water':
        berhasil = await hapus_water_log_by_id(user_id, log_id)
    elif log_type == 'weight':
        berhasil = await hapus_weight_log_by_id(user_id, log_id)
    else:
        raise HTTPException(status_code=400, detail="Tipe log tidak valid")

    if berhasil: return {"status": "success"}
    raise HTTPException(status_code=404, detail="Log tidak ditemukan")


@app.get("/", response_class=HTMLResponse)
async def serve_mini_app():
    with open("webapp/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)