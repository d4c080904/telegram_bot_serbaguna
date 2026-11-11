import logging
from database.queries import get_berat_14_hari_terakhir

logger = logging.getLogger(__name__)

async def hitung_adaptive_tdee(user_id, base_bmr_tdee, target_mode, berat_sekarang):
    """
    Menghitung target kalori dinamis berdasarkan tren berat badan 14 hari terakhir.
    """
    try:
        # 1. Ambil data berat badan 14 hari terakhir
        weight_logs = await get_berat_14_hari_terakhir(user_id)
        
        # Kalau data kurang dari 5 (misal baru daftar), balikin target default (statis)
        if len(weight_logs) < 5:
            return base_bmr_tdee, "statis"
            
        # 2. Hitung tren (berat terbaru - berat terlama)
        berat_terlama = weight_logs[0]['berat']
        berat_terbaru = weight_logs[-1]['berat']
        selisih = berat_terbaru - berat_terlama
        
        # Hitung rata-rata selisih per minggu
        # (Ada 14 hari, jadi kita bagi 2 buat dapet rata-rata mingguan)
        tren_mingguan = selisih / 2.0 
        
        target_baru = base_bmr_tdee
        alasan = ""
        
        # 3. Logika Auto-Adjust
        if target_mode == 'cutting':
            # Kalau seminggu gak turun 0.2 kg (stagnan)
            if tren_mingguan > -0.2:
                target_baru -= 200 # Potong kalori 200
                alasan = "Stagnan, potong 200 kcal"
            # Kalau turun terlalu drastis (lebih dari 1 kg/minggu)
            elif tren_mingguan < -1.0:
                target_baru += 200 # Naikin kalori biar otot gak hilang
                alasan = "Turun terlalu cepat, naikkan 200 kcal"
            else:
                alasan = "Tren ideal, target dipertahankan"
                
        elif target_mode == 'bulking':
            # Kalau seminggu gak naik 0.1 kg
            if tren_mingguan < 0.1:
                target_baru += 200
                alasan = "Stagnan, tambah 200 kcal"
            # Kalau naik terlalu drastis (lebih dari 0.8 kg/minggu)
            elif tren_mingguan > 0.8:
                target_baru -= 200
                alasan = "Naik terlalu cepat (lemak), kurangi 200 kcal"
            else:
                alasan = "Tren ideal, target dipertahankan"
                
        else: # Recomp / maintain
            alasan = "Target maintain"

        # 4. Pengaman (Safety Net)
        # Jangan biarin target kalori di bawah BMR (biar gak bahaya)
        batas_bawah = base_bmr_tdee * 0.7 
        if target_baru < batas_bawah:
            target_baru = int(batas_bawah)
            alasan += " (Limit BMR)"
            
        return int(target_baru), alasan
        
    except Exception as e:
        logger.error(f"hitung_adaptive_tdee error: {e}")
        return base_bmr_tdee, "error"