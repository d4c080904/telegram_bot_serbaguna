import logging
import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from database.queries import (
    catat_payment_event, aktifkan_premium, get_db, cek_status_vip, 
    tambah_food_log, tambah_air, update_user_weight, 
    get_history_makanan_hari_ini, hapus_food_log_by_id, get_unified_history,
    hapus_water_log_by_id, hapus_weight_log_by_id, tambah_workout_log, get_statistik_user,
    get_user_profile, get_gym_profile, update_profile_web, save_gym_profile,
    ambil_chat_history, simpan_chat_message, hapus_chat_history
)
from services.ai import analisis_foto_makanan, analisis_teks_makanan, estimasi_kalori_olahraga, analisis_alat_gym, rekomendasi_makanan
from services.pt_chat import proses_chat_pt_core

# ✅ IMPORT FITUR TAMBAHAN (Pastikan path-nya sesuai project lu)
from services.barcode_scanner import decode_barcode, get_product_from_openfoodfacts
# GANTI IMPORT INI SESUAI STRUKTUR FOLDER LU (Misal di handlers/export.py atau services/pdf.py)
# Asumsi gw lu punya fungsi yang bikin PDF dan return file path-nya.
from services.pdf_generator import buat_laporan_pdf 

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

# ✅ ENDPOINT BARU: LOG BARCODE
@app.post("/api/log_barcode")
async def api_log_barcode(request: Request, barcode_image: UploadFile = File(...)):
    user_id = await get_vip_user(request)
    try:
        image_bytes = await barcode_image.read()
        barcode_num = decode_barcode(image_bytes)
        if not barcode_num: raise HTTPException(status_code=400, detail="Barcode gagal dibaca.")
        
        produk = await get_product_from_openfoodfacts(barcode_num)
        if not produk: raise HTTPException(status_code=404, detail="Produk tidak ditemukan di database.")
        
        berhasil = await tambah_food_log(
            user_id, 0, 0, barcode_num,
            f"{produk['nama']} ({produk['kategori']})", "1 porsi (100g)",
            produk['kalori'], produk['protein'], produk['karbo'], produk['lemak'], produk['gula']
        )
        if not berhasil: raise HTTPException(status_code=500, detail="Gagal menyimpan data.")
        return {"status": "success", "data": produk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ ENDPOINT BARU: MEAL PLANNER
@app.get("/api/meal_planner")
async def api_meal_planner(request: Request):
    user_id = await get_vip_user(request)
    try:
        user = await get_user_profile(user_id)
        async with await get_db() as conn:
            row = await conn.fetchrow("SELECT total_kalori_masuk, total_kalori_terbakar FROM daily_logs WHERE user_id = $1 AND tanggal = CURRENT_DATE", user_id)
            
        target = 2500 # Default
        masuk = row['total_kalori_masuk'] if row else 0
        keluar = row['total_kalori_terbakar'] if row else 0
        sisa = target - (masuk - keluar)
        
        resep = await rekomendasi_makanan(sisa, 50, 100, 30, user.get('target', 'recomp'))
        if not resep: raise HTTPException(status_code=500, detail="AI gagal membuat resep.")
        return {"status": "success", "data": resep}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ ENDPOINT BARU: EXPORT PDF
@app.post("/api/export_pdf")
async def api_export_pdf(request: Request):
    user_id = await get_vip_user(request)
    try:
        file_path = await buat_laporan_pdf(user_id) 
        with open(file_path, "rb") as f:
            await bot.send_document(chat_id=user_id, document=f, caption="📄 Berikut laporan GymMate lu bro!")
        os.remove(file_path)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Export PDF error: {e}")
        raise HTTPException(status_code=500, detail="Gagal membuat/mengirim PDF")

@app.post("/api/log_water")
async def log_water(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    ml = data.get("ml")
    if not ml: raise HTTPException(status_code=400, detail="Jumlah ml kosong")
    if await tambah_air(user_id, int(ml)): return {"status": "success"}
    raise HTTPException(status_code=500)

@app.post("/api/log_weight")
async def log_weight(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    berat = data.get("berat")
    if not berat: raise HTTPException(status_code=400, detail="Berat kosong")
    if await update_user_weight(user_id, float(berat)): return {"status": "success"}
    raise HTTPException(status_code=500)

@app.post("/api/log_workout")
async def log_workout(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    teks = data.get("teks")
    if not teks: raise HTTPException(status_code=400)
    try:
        profil = await get_user_profile(user_id)
        berat = profil['berat'] if profil else 70
        hasil = await estimasi_kalori_olahraga(teks, berat)
        if await tambah_workout_log(user_id, hasil['olahraga'], hasil['durasi'], hasil['kalori_terbakar']):
            return {"status": "success", "data": hasil}
        raise HTTPException(status_code=500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get_stats")
async def get_stats(request: Request):
    user_id = await get_vip_user(request)
    return {"stats": await get_statistik_user(user_id)}

@app.get("/api/profile")
async def api_get_profile(request: Request):
    user_id = await get_vip_user(request)
    profil = await get_gym_profile(user_id)
    if not profil: raise HTTPException(status_code=404)
    bmi = profil['berat'] / ((profil['tinggi']/100) ** 2) if profil['berat'] and profil['tinggi'] else 0
    return {"nama": profil['nama'], "umur": profil['umur'], "berat": profil['berat'], "tinggi": profil['tinggi'], "target": profil['target'] or 'recomp', "bmi": round(bmi, 1)}

@app.post("/api/profile")
async def api_update_profile(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    if await update_profile_web(user_id, float(data['berat']), float(data['tinggi']), data['target']):
        return {"status": "success"}
    raise HTTPException(status_code=500)

@app.post("/api/gym_profile")
async def api_gym_profile(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    if await save_gym_profile(user_id, data): return {"status": "success"}
    raise HTTPException(status_code=500)

@app.post("/api/scan_equipment")
async def api_scan_equipment(request: Request, equipment_image: UploadFile = File(...)):
    user_id = await get_vip_user(request)
    image_bytes = await equipment_image.read()
    hasil = await analisis_alat_gym(image_bytes)
    return {"status": "success", "data": hasil}

@app.get("/api/chat/history")
async def api_chat_history(request: Request):
    user_id = await get_vip_user(request)
    return {"history": await ambil_chat_history(user_id)}

@app.post("/api/chat/send")
async def api_chat_send(request: Request):
    user_id = await get_vip_user(request)
    data = await request.json()
    result = await proses_chat_pt_core(user_id, data.get("pesan", ""))
    if result["status"] == "success": return {"response": result["data"]}
    raise HTTPException(status_code=500)

@app.delete("/api/chat/clear")
async def api_chat_clear(request: Request):
    user_id = await get_vip_user(request)
    await hapus_chat_history(user_id)
    return {"status": "success"}

@app.get("/api/unified_history")
async def api_unified_history(request: Request):
    user_id = await get_vip_user(request)
    return {"history": await get_unified_history(user_id)}

@app.delete("/api/delete_log/{log_type}/{log_id}")
async def delete_log(request: Request, log_type: str, log_id: int):
    user_id = await get_vip_user(request)
    if log_type == 'food': await hapus_food_log_by_id(user_id, log_id)
    elif log_type == 'water': await hapus_water_log_by_id(user_id, log_id)
    elif log_type == 'weight': await hapus_weight_log_by_id(user_id, log_id)
    return {"status": "success"}

@app.get("/", response_class=HTMLResponse)
async def serve_mini_app():
    with open("webapp/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)