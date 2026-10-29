import logging
import base64
import json
import os
from bot_instance import groq_client
from config import PRIORITAS_MODEL
from database.queries import cache_get, cache_set, buat_cache_key, ambil_chat_history, get_user_profile
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

def perbaiki_teks_dengan_ai(teks):
    key = buat_cache_key("rapih", teks)
    cached = cache_get(key)
    if cached: return cached
    for model_name in MODEL_GROQ_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Kamu adalah mesin pengubah bahasa gaul/singkatan Indonesia menjadi bahasa Indonesia baku. DILARANG KERAS memberikan penjelasan, peringatan, atau kata pengantar. KEMBALIKAN TEKS BAKUNYA SAJA!"},
                    {"role": "user", "content": f"Teks: {teks}\nHasil:"}
                ], model=model_name, temperature=0.0,
            )
            hasil_ai = response.choices[0].message.content.strip()
            hasil_ai = hasil_ai.replace("Hasil:", "").replace("Teks:", "").strip().split('\n')[0].strip()
            if hasil_ai:
                cache_set(key, hasil_ai); return hasil_ai
        except Exception as e:
            logger.warning(f"Model {model_name} gagal (rapih): {e}"); continue
    return ""

def terjemahkan_ke_inggris(teks):
    key = buat_cache_key("translate", teks)
    cached = cache_get(key)
    if cached: return cached
    prompt = f"Terjemahkan ke bahasa Inggris natural (hindari terjemahan kaku). TANPA PENJELASAN!\nTeks: {teks}\nHasil:"
    for model_name in MODEL_GROQ_LIST:
        try:
            response = groq_client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=model_name, temperature=0.3)
            hasil_ai = response.choices[0].message.content.strip().split('\n')[0].strip()
            if hasil_ai: cache_set(key, hasil_ai); return hasil_ai
        except Exception as e:
            logger.warning(f"Model {model_name} gagal (translate): {e}"); continue
    return "Sorry, translation failed due to server issues."

def chat_dengan_ai(user_id, pesan_baru):
    history = ambil_chat_history(user_id)
    user = get_user_profile(user_id)
    
    nama = user['nama'] if user else "Bro"
    umur = f"{user['umur']} tahun" if user and user['umur'] else ""
    bb = f"{user['berat']} kg" if user and user['berat'] else ""
    tb = f"{user['tinggi']} cm" if user and user['tinggi'] else ""
    
    profil_str = f"User bernama {nama}, umur {umur}, BB {bb}, TB {tb}."
    if not user: profil_str = "Kamu belum tau data user ini."
        
    system_prompt = (
        f"Kamu adalah asisten AI yang santai, ramah, dan pintar. {profil_str} "
        "Panggil user dengan namanya jika kamu tau. Jawab dengan jelas, JANGAN bertele-tele. "
        "Kalau nggak tau jawabannya, jujur aja bilang 'gw kurang tau'. "
        "JANGAN pernah mengarang fakta atau nama yang nggak jelas. Kalau user nanya hal sensitif/ilegal, tolak dengan sopan. "
        "ATURAN FORMAT: JANGAN pakai format markdown apapun. Dilarang pakai tanda **, *, _, #, `, atau ```. "
        "Tulis dengan teks polos aja. Boleh pakai tanda baca biasa (-, •, 1. 2. 3.) dan emoji kalau perlu."
    )
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": pesan_baru}]
    for model_name in MODEL_GROQ_LIST:
        try:
            response = groq_client.chat.completions.create(
                messages=messages, model=model_name, temperature=0.5, max_tokens=1024,
                frequency_penalty=0.5, presence_penalty=0.5
            )
            hasil = response.choices[0].message.content.strip()
            if hasil: return hasil
        except Exception as e:
            logger.warning(f"Model {model_name} gagal (chat): {e}"); continue
    return None

def analisis_gym_noob(umur, berat, tinggi):
    bmi = hitung_bmi(berat, tinggi); kategori = kategori_bmi(bmi)
    system_prompt = (
        "Kamu adalah personal trainer berpengalaman yang ramah. "
        "Klien kamu BARU MULAI gym, jelaskan sederhana & gaul. "
        "WAJIB pakai bahasa Indonesia (bukan bahasa Melayu). "
        "JANGAN pakai markdown, tulis teks polos. "
        "JANGAN mengulang kata yang sama berkali-kali. Berhenti jika sudah selesai."
    )
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
    system_prompt = (
        "Kamu adalah personal trainer elite. Klien kamu sudah pengalaman, jawab detail teknis advanced. "
        "WAJIB pakai bahasa Indonesia gaul (bukan bahasa Melayu). JANGAN pakai markdown. "
        "JANGAN mengulang kata yang sama berkali-kali. Berhenti jika sudah selesai."
    )
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

def analisis_foto_makanan(image_bytes, caption=""):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    prompt_text = (
        "Analisis foto makanan ini sebagai ahli gizi. "
        "Berikan output HANYA format JSON murni dengan key: nama_makanan, estimasi_porsi, kalori, protein, karbo, lemak, gula. "
        "Perkirakan gula (dalam gram) secara realistis, termasuk gula tersembunyi. "
        f"Caption dari user: {caption}"
    )
    user_content = [
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
    ]
    model_vision = "qwen/qwen3.8-27b"
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": user_content}],
            model=model_vision,
            temperature=0.2,
            max_completion_tokens=500,
            response_format={"type": "json_object"}
        )
        hasil = response.choices[0].message.content.strip()
        return json.loads(hasil)
    except Exception as e:
        logger.error(f"Vision API Error: {e}")
        return None

def koreksi_foto_makanan(koreksi_user):
    prompt_text = (
        f"User mengoreksi analisis makanan sebelumnya. Koreksi: '{koreksi_user}'. "
        "Tugasmu: Ganti HANYA item makanan yang salah koreksi dengan item yang baru. "
        "JANGAN menghapus item lain yang tidak disebutkan. "
        "Hitung ulang TOTAL kalori, makro, dan gula secara keseluruhan. "
        "Berikan output HANYA format JSON murni dengan key: "
        "nama_makanan (HARUS TEKS STRING), estimasi_porsi, kalori, protein, karbo, lemak, gula."
    )
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_text}],
            model="qwen/qwen3.8-27b",
            temperature=0.2,
            max_completion_tokens=500,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Koreksi API Error: {e}")
        return None

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
    Kamu adalah asisten AI serba bisa. User baru saja mengirim pesan suara dengan transkripsi berikut:
    "{teks}"

    Analisis teks tersebut dan tentukan aksi yang harus dilakukan.
    Output HANYA JSON murni dengan format:
    {{
      "food_data": {{
        "nama_makanan": "string", "estimasi_porsi": "string", "kalori": number,
        "protein": number, "karbo": number, "lemak": number, "gula": number
      }} atau null,
      "gym_data": "string (deskripsi latihan)" atau null,
      "chat_reply": "string (balasan natural)" atau null
    }}

    PENTING:
    - Jika user mencatat makanan, isi `food_data`. Kosongkan `gym_data` dan `chat_reply`.
    - Jika user mencatat latihan gym, isi `gym_data`. Kosongkan `food_data` dan `chat_reply`.
    - Jika user cuma ngobrol, isi `chat_reply`. Kosongkan `food_data` dan `gym_data`.
    """
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="qwen/qwen3.8-27b",
            temperature=0.1,
            max_completion_tokens=500,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Voice Intent Error: {e}")
        return None

def rekomendasi_makanan(sisa_kalori, sisa_protein, sisa_karbo, sisa_lemak, target_user):
    prompt = f"""
    Kamu adalah Chef & Ahli Gizi Profesional.
    User sedang diet dengan target: {target_user}.
    Sisa kalori harian user saat ini: {sisa_kalori} kcal.
    Sisa Protein: {sisa_protein}g, Karbo: {sisa_karbo}g, Lemak: {sisa_lemak}g.
    
    Berikan 1 rekomendasi resep makanan yang:
    1. Kalorinya TIDAK MELEBIHI sisa kalori.
    2. Tinggi protein (buat nutupin sisa protein).
    3. Bahan-bahannya gampang dicari di Indonesia.
    4. Cara buatnya singkat.
    
    Berikan jawaban dengan format teks polos (JANGAN pakai markdown ** atau *), tapi gunakan emoji yang menarik. Maksimal 150 kata.
    """
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