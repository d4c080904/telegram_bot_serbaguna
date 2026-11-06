import logging
import json
import os
import base64
from bot_instance import groq_client
from config import PRIORITAS_MODEL
from database.queries import cache_get, cache_set, buat_cache_key, get_user_profile, ambil_chat_history
from utils.helpers import hitung_bmi, kategori_bmi

logger = logging.getLogger(__name__)

print("Mengecek daftar model Groq...")
try:
    daftar_model = groq_client.models.list()
    semua_model = [m.id for m in daftar_model.data if "whisper" not in m.id and "guard" not in m.id and "orpheus" not in m.id and "tts" not in m.id]
    MODEL_GROQ_LIST = []
    for prioritas in PRIORITAS_MODEL:
        if prioritas in semua_model:
            MODEL_GROQ_LIST.append(prioritas)
            semua_model.remove(prioritas)
    MODEL_GROQ_LIST.extend(semua_model)
    
    if not MODEL_GROQ_LIST:
        MODEL_GROQ_LIST = ["llama-3.1-8b-instant"]
        
    logger.info(f"✅ {len(MODEL_GROQ_LIST)} model Groq siap")
    logger.info(f"🥇 Model utama: {MODEL_GROQ_LIST[0]}")
except Exception as e:
    logger.warning(f"Gagal ambil model Groq: {e}")
    MODEL_GROQ_LIST = ["llama-3.1-8b-instant"]

# Model vision yang kita pake buat baca gambar (DENGAN SISTEM FALLBACK)
MODEL_VISION_LIST = [
    "qwen/qwen3.8-27b",
    "llama-3.2-11b-vision-preview"
]

# --- FUNGSI GYM & FITNESS ---

def analisis_gym_noob(umur, berat, tinggi):
    bmi = hitung_bmi(berat, tinggi); kategori = kategori_bmi(bmi)
    system_prompt = "Kamu adalah personal trainer berpengalaman yang ramah. Klien kamu BARU MULAI gym, jelaskan sederhana & gaul. WAJIB pakai bahasa Indonesia (bukan Melayu). JANGAN pakai markdown, tulis teks polos. JANGAN mengulang kata yang sama berkali-kali. Berhenti jika sudah selesai."
    user_prompt = f"Data Klien: {umur}th, {berat}kg, {tinggi}cm, BMI: {bmi} ({kategori}). Kasih panduan: 1. Ringkasan kondisi. 2. Program minggu 1. 3. Tips makan. 4. 3 kesalahan pemula. 5. Motivasi. Max 500 kata."
    for model_name in MODEL_GROQ_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], 
                model=model_name, temperature=0.5, max_tokens=1500, frequency_penalty=0.5, presence_penalty=0.5
            )
            hasil = response.choices[0].message.content.strip()
            if hasil: return hasil
        except Exception as e: logger.warning(f"Gagal (gym noob): {e}"); continue
    return None

def analisis_gym_pro(data):
    bmi = hitung_bmi(data.get('berat'), data.get('tinggi')); kategori = kategori_bmi(bmi)
    gender_label = "Laki-laki" if data.get('jenis_kelamin') == 'L' else "Perempuan"
    alat_label = {'gym_full': 'Gym lengkap', 'home_dumbbell': 'Rumahan + dumbbell', 'home_barbell': 'Rumahan + barbell', 'bodyweight': 'Bodyweight only'}.get(data.get('alat'), data.get('alat', 'N/A'))
    system_prompt = "Kamu adalah personal trainer elite. Klien kamu sudah pengalaman, jawab detail teknis advanced. WAJIB pakai bahasa Indonesia gaul (bukan Melayu). JANGAN pakai markdown. JANGAN mengulang kata yang sama berkali-kali. Berhenti jika sudah selesai."
    user_prompt = f"Data Pro: {data.get('umur')}th, {data.get('berat')}kg, {data.get('tinggi')}cm, {gender_label}, BMI: {bmi} ({kategori}), Target: {data.get('target')}, Level: {data.get('level')}, Pengalaman: {data.get('pengalaman')}th, Frekuensi: {data.get('frekuensi')}x/mgg, Alat: {alat_label}. Kasih analisis advanced: 1. Analisis komposisi. 2. Split program. 3. Kalori & makro. 4. Saran periodization. 5. Weak point. 6. Suplemen. Max 700 kata."
    for model_name in MODEL_GROQ_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], 
                model=model_name, temperature=0.5, max_tokens=2000, frequency_penalty=0.5, presence_penalty=0.5
            )
            hasil = response.choices[0].message.content.strip()
            if hasil: return hasil
        except Exception as e: logger.warning(f"Gagal (gym pro): {e}"); continue
    return None

def rekomendasi_makanan(sisa_kalori, sisa_protein, sisa_karbo, sisa_lemak, target_user):
    prompt = f"Kamu adalah Chef & Ahli Gizi. Target: {target_user}. Sisa kalori: {sisa_kalori} kcal. Protein kurang: {sisa_protein}g. Kasih 1 resep yang kalorinya < sisa kalori, tinggi protein, bahan lokal. Teks polos + emoji. Max 150 kata."
    for model_name in MODEL_GROQ_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name, temperature=0.7, max_tokens=500
            )
            hasil = response.choices[0].message.content.strip()
            if hasil: return hasil
        except Exception: continue
    return None

# --- FUNGSI VISION (BACA GAMBAR) ---

def analisis_foto_makanan(image_bytes, caption=""):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    prompt_text = "Analisis foto makanan ini sebagai ahli gizi. Berikan output HANYA format JSON murni dengan key: nama_makanan, estimasi_porsi, kalori, protein, karbo, lemak, gula. Perkirakan gula (dalam gram) secara realistis. Caption: " + caption
    user_content = [
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
    ]
    
    for model_name in MODEL_VISION_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": user_content}],
                model=model_name,
                temperature=0.2,
                max_completion_tokens=500,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            logger.warning(f"Model Vision {model_name} gagal (makanan): {e}")
            continue
    return None

def koreksi_foto_makanan(koreksi_user):
    prompt_text = f"User mengoreksi analisis makanan sebelumnya. Koreksi: '{koreksi_user}'. Ganti HANYA item makanan yang salah koreksi. Hitung ulang TOTAL kalori, makro, dan gula. Output HANYA format JSON murni: nama_makanan (HARUS TEKS STRING), estimasi_porsi, kalori, protein, karbo, lemak, gula."
    
    for model_name in MODEL_VISION_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_text}],
                model=model_name,
                temperature=0.2,
                max_completion_tokens=500,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            logger.warning(f"Model Vision {model_name} gagal (koreksi): {e}")
            continue
    return None

def analisis_alat_gym(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    prompt_text = (
        "Kamu adalah personal trainer berpengalaman. Identifikasi alat gym pada foto ini. "
        "Berikan output teks polos (tanpa markdown) dengan format:\n"
        "🏋️ Nama Alat: [Nama Alat]\n"
        "💪 Otot yang Dilatih: [Otot]\n"
        "📖 Cara Pakai: [Instruksi singkat & aman]\n\n"
        "JANGAN pakai tanda bintang ** atau *."
    )
    user_content = [
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
    ]
    
    for model_name in MODEL_VISION_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": user_content}],
                model=model_name,
                temperature=0.2,
                max_completion_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Model Vision {model_name} gagal (alat gym): {e}")
            continue
    return None

# --- FUNGSI AUDIO (VOICE NOTE) ---

def transkripsi_audio(audio_file_path):
    try:
        with open(audio_file_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_path), file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
                language="id"
            )
        return transcription.strip()
    except Exception as e:
        logger.error(f"Whisper Error: {e}")
        return None

def proses_voice_note(teks):
    prompt = f"""
    Kamu adalah asisten AI khusus GYM & NUTRISI. User baru saja mengirim pesan suara dengan transkripsi berikut:
    "{teks}"

    Output HANYA JSON murni dengan format:
    {{
      "food_data": {{"nama_makanan": "string", "estimasi_porsi": "string", "kalori": number, "protein": number, "karbo": number, "lemak": number, "gula": number}} atau null,
      "gym_data": "string (deskripsi latihan)" atau null
    }}

    PENTING:
    - Jika user mencatat makanan/minuman, isi `food_data`. Kosongkan `gym_data`.
    - Jika user mencatat latihan gym/olahraga, isi `gym_data`. Kosongkan `food_data`.
    - Jika user cuma ngobrol atau nanya hal di luar gym/makanan, kosongkan KEDUANYA (set null).
    """
    
    for model_name in MODEL_VISION_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                temperature=0.1,
                max_completion_tokens=500,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            logger.warning(f"Model Vision {model_name} gagal (voice note): {e}")
            continue
    return None

# --- FUNGSI CHAT PT AI ---

def chat_dengan_pt(user_id, pesan_baru):
    history = ambil_chat_history(user_id)
    user = get_user_profile(user_id)
    
    profil_str = ""
    if user:
        profil_str = f"User bernama {user['nama']}, BB {user['berat']}kg, TB {user['tinggi']}cm, Umur {user['umur']}th."
    
    system_prompt = (
        f"Kamu adalah Personal Trainer (PT) AI profesional, ramah, dan suportif. {profil_str} "
        "Tugasmu adalah menjawab pertanyaan user seputar gym, latihan (workout), nutrisi, diet, dan motivasi. "
        "Pakai bahasa Indonesia gaul (gw/lu) tapi tetap sopan dan berwibawa seperti PT asli. "
        "Jawab dengan jelas, SINGKAT, dan to-the-point. MAKSIMAL 3 paragraf pendek atau 5 poin saja. "
        "DILARANG KERAS mengulang kata yang sama berkali-kali. Berhenti menjawab jika sudah selesai. "
        "Kalau user nanya di luar topik fitness/kesehatan, tolak dengan halus dan arahkan kembali ke topik gym. "
        "ATURAN FORMAT: JANGAN pakai format markdown apapun (Dilarang pakai **, *, _, #, `). Tulis teks polos aja. Boleh pakai emoji."
    )
    
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": pesan_baru}]
    
    # Paksa pakai model paling pinter dulu (llama-3.3-70b-versatile)
    # Kalau gagal, baru pake list fallback
    model_prioritas = ["llama-3.3-70b-versatile"] + MODEL_GROQ_LIST
    
    for model_name in model_prioritas:
        try:
            response = groq_client.chat.completions.create(
                messages=messages, 
                model=model_name, 
                temperature=0.3,             # Dibikin rendah biar AI fokus & nggak ngaco
                max_tokens=512,              # Batasi panjang jawaban
                frequency_penalty=0.8,       # Penalti kata berulang (Ditingkatkan)
                presence_penalty=0.8         # Penalti topik berulang (Ditingkatkan)
            )
            hasil = response.choices[0].message.content.strip()
            
            # Filter deteksi kalau AI masih ngulang-ngulang kata
            if hasil and " dan " in hasil.lower():
                kata = hasil.lower().split()
                if len(kata) > 10 and len(set(kata)) < len(kata) * 0.3: 
                    logger.warning(f"Model {model_name} ngulang kata. Skip.")
                    continue # Abaikan hasil ngaco, coba model lain
            
            if hasil: return hasil
        except Exception as e:
            logger.warning(f"Model {model_name} gagal (chat PT): {e}"); continue
    return None