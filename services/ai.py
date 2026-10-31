import logging
import json
import os
from google.genai import types
from bot_instance import gemini_client
from database.queries import cache_get, cache_set, buat_cache_key, ambil_chat_history, get_user_profile
from utils.helpers import hitung_bmi, kategori_bmi

logger = logging.getLogger(__name__)

def perbaiki_teks_dengan_ai(teks):
    key = buat_cache_key("rapih", teks)
    cached = cache_get(key)
    if cached: return cached
    
    prompt = f"Kamu adalah mesin pengubah bahasa gaul/singkatan Indonesia menjadi bahasa Indonesia baku. DILARANG KERAS memberikan penjelasan. KEMBALIKAN TEKS BAKUNYA SAJA!\nTeks: {teks}\nHasil:"
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        hasil_ai = response.text.strip().split('\n')[0].strip()
        if hasil_ai:
            cache_set(key, hasil_ai); return hasil_ai
    except Exception as e:
        logger.warning(f"Gemini gagal (rapih): {e}")
    return ""

def terjemahkan_ke_inggris(teks):
    key = buat_cache_key("translate", teks)
    cached = cache_get(key)
    if cached: return cached
    
    prompt = f"Terjemahkan ke bahasa Inggris natural. TANPA PENJELASAN!\nTeks: {teks}\nHasil:"
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        hasil_ai = response.text.strip().split('\n')[0].strip()
        if hasil_ai: cache_set(key, hasil_ai); return hasil_ai
    except Exception as e:
        logger.warning(f"Gemini gagal (translate): {e}")
    return "Sorry, translation failed."

def chat_dengan_ai(user_id, pesan_baru):
    history = ambil_chat_history(user_id)
    user = get_user_profile(user_id)
    
    nama = user['nama'] if user else "Bro"
    profil_str = f"User bernama {nama}, BB {user['berat']}kg, TB {user['tinggi']}cm." if user else ""
    
    system_prompt = (
        f"Kamu adalah asisten AI santai, ramah, dan pintar. {profil_str} "
        "Jawab dengan jelas, JANGAN bertele-tele. "
        "ATURAN FORMAT: JANGAN pakai markdown (** atau *). Tulis teks polos aja."
    )
    
    contents = [system_prompt]
    for msg in history:
        contents.append(f"{msg['role']}: {msg['content']}")
    contents.append(f"user: {pesan_baru}")
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents
        )
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini gagal (chat): {e}")
    return None

def analisis_gym_noob(umur, berat, tinggi):
    bmi = hitung_bmi(berat, tinggi); kategori = kategori_bmi(bmi)
    prompt = (
        f"Kamu adalah personal trainer ramah. Klien: {umur}th, {berat}kg, {tinggi}cm, BMI: {bmi} ({kategori}). "
        "Kasih panduan: 1. Kondisi. 2. Program minggu 1. 3. Tips makan. 4. 3 kesalahan pemula. 5. Motivasi. Max 500 kata. "
        "JANGAN pakai markdown."
    )
    try:
        response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e: logger.warning(f"Gemini gagal (gym noob): {e}"); return None

def analisis_gym_pro(data):
    bmi = hitung_bmi(data.get('berat'), data.get('tinggi')); kategori = kategori_bmi(bmi)
    prompt = (
        f"Kamu personal trainer elite. Klien: {data.get('umur')}th, {data.get('berat')}kg, {data.get('tinggi')}cm, Target: {data.get('target')}, Level: {data.get('level')}. "
        "Kasih analisis advanced: 1. Komposisi. 2. Split program. 3. Kalori & makro. 4. Periodization. 5. Weak point. Max 700 kata. "
        "JANGAN pakai markdown."
    )
    try:
        response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e: logger.warning(f"Gemini gagal (gym pro): {e}"); return None

def analisis_foto_makanan(image_bytes, caption=""):
    prompt_text = (
        "Analisis foto makanan ini. "
        "Berikan output HANYA format JSON murni dengan key: nama_makanan, estimasi_porsi, kalori, protein, karbo, lemak, gula. "
        f"Caption: {caption}"
    )
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                prompt_text,
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini Vision Error: {e}")
        return None

def koreksi_foto_makanan(koreksi_user):
    prompt_text = (
        f"User mengoreksi makanan sebelumnya: '{koreksi_user}'. "
        "Ganti HANYA item yang salah. Hitung ulang TOTAL kalori & makro. "
        "Output JSON murni: nama_makanan (string), estimasi_porsi, kalori, protein, karbo, lemak, gula."
    )
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_text,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini Koreksi Error: {e}")
        return None

def transkripsi_audio(audio_file_path):
    """Transkripsi audio pakai Gemini Vision/Audio"""
    try:
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
            
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                "Tolong transkrip audio ini ke dalam teks bahasa Indonesia. Jangan tambahkan kata pengantar.",
                types.Part.from_bytes(data=audio_bytes, mime_type='audio/ogg')
            ]
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Audio Error: {e}")
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
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini Voice Intent Error: {e}")
        return None

def rekomendasi_makanan(sisa_kalori, sisa_protein, sisa_karbo, sisa_lemak, target_user):
    prompt = (
        f"Kamu Chef & Ahli Gizi. Target user: {target_user}. Sisa kalori: {sisa_kalori} kcal. Sisa Protein: {sisa_protein}g. "
        "Kasih 1 resep yang kalorinya < sisa kalori, tinggi protein, bahan lokal, cara singkat. Teks polos + emoji. Max 150 kata."
    )
    try:
        response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e: logger.warning(f"Gemini gagal (meal planner): {e}"); return None