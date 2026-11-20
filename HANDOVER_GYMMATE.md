=====================================================
BLUEPRINT & HANDOVER PROJECT: GYMMATE TELEGRAM BOT & MINI APP
VERSI: 3.0 (ENTERPRISE - POST ADMIN & BACKUP SYSTEM)
=====================================================

[ATURAN KETAT UNTUK AI BARU / PEMBANTU SELANJUTNYA]:
1. BACA BLUEPRINT INI SAMPAI HABIS SEBELUM NGODING.
2. JANGAN BERHALUSINASI (HALU), JANGAN NGARANG NAMA MODEL/FUNGSI.
3. JANGAN MENGHILANGKAN FITUR YANG SUDAH JALAN (REGRESI DILARANG KERAS).
4. SEMUA LOGIKA PYTHON WAJIB ASYNC/AWAIT (aiogram, asyncpg, FastAPI).
5. JIKA DIMINTA KODE, KASIH FULL CODE (JANGAN CUMA POTONGAN) BIAR GA ERROR.
6. JIKA ADA FILE YANG BERUBAH, SELALU MINTA FILE ASLINYA DULU SEBELUM MENIMPA.

[TEKNOLOGI YANG DIPAKAI]:
- Python 3.13
- Framework Bot: aiogram (v3.x)
- Database: PostgreSQL (via Docker, port 5432, user: gymmate, pass: rahasia_gymmate, db: gymmate_db)
- DB Driver: asyncpg (murni async)
- AI Engine: Groq API (AsyncGroq) - Model: gpt-oss, qwen, llama-scout, whisper
- PDF Generator: fpdf2
- Web Server: FastAPI + Uvicorn
- Frontend Mini App: HTML, Vanilla JS, CSS (Dipisah), Chart.js, marked.js
- Barcode Scanner: opencv-contrib-python + httpx (OpenFoodFacts)

[STRUKTUR FOLDER PENTING SAAT INI]:
- bot_instance.py (Inisialisasi Bot & Groq)
- main.py (Entry point, daftar Router, setup DB, jalankan Uvicorn)
- config.py (Load .env: TELEGRAM_TOKEN, GROQ_API_KEY, DATABASE_URL, ADMIN_ID, WEBHOOK_SECRET)
- api_server.py (FastAPI untuk Mini App & Webhook, sudah include `app.mount("/static")` untuk CSS/JS)
- /database/db.py (Connection pool asyncpg, setup tabel & migrasi schema)
- /database/queries.py (Semua query async, termasuk Admin & Stats)
- /handlers/ (start.py, calorie.py, progress.py, pt_chat.py, gym.py, equipment.py, meal_planner.py, export.py, admin.py, commands.py)
- /middlewares/premium_gate.py (Satpam VIP, Banned check, dan Last Active tracker)
- /services/ (ai.py, pdf_generator.py, barcode_scanner.py, pt_chat.py, dll)
- /webapp/index.html (UI Mini App bersih)
- /webapp/style.css (Styling Mini App + fitur scroll drag)
- /webapp/script.js (Logika JS Mini App + fitur scroll drag)
- /scripts/backup_db.ps1 (Script backup database otomatis)

=====================================================
STATUS PROJECT: FASE 1-4 SELESAI, FASE 5 (INFRA) PENDING
=====================================================

[FITUR BOT TELEGRAM (100% SELESAI)]:
1. Onboarding: User baru langsung disuguhi minta akses (VIP check duluan, bukan onboarding).
2. Kalori Tracker: Foto makanan, Teks bebas, Voice Note, Scan Barcode.
3. Adaptive TDEE: Auto-adjust kalori.
4. Progress & Air: Catat minum & berat badan.
5. Chat PT AI: History & Profil, format Markdown rapi.
6. Program Gym: Mode Noob & Pro.
7. Scan Alat Gym & Meal Planner.
8. Export PDF (Kirim ke chat).
9. Command Menu (Lengkap termasuk /myprogress untuk lihat total progres seumur hidup).
10. SECURITY (Diperbarui):
    - Invite-Only System: User klik "Minta Izin", Admin approve.
    - Webhook QRIS dikunci pakai Header `x-webhook-secret`.
    - Middleware PremiumGate diupdate: Jika user di-BAN, dia tetap bisa akses /start atau /help untuk minta tolong/akses ulang (gak permanent block).
    - Fitur Auto-Unban: Jika Admin approve user yang di-ban, status banned otomatis hilang.

[FITUR MINI APP / WEB (100% SELESAI)]:
1. Refactoring: File dipisah jadi `index.html`, `style.css`, `script.js` (Clean Code).
2. 5 Tab Utama: Dashboard, Nutrisi, Gym, Hist, PT AI.
3. Dashboard: Ringkasan Kalori, Widget Air, Grafik Chart.js.
4. Nutrisi: Log Makan, Log Barcode, Air & Berat, Meal Planner.
5. Gym: Statistik, Program, Log Latihan, Scan Alat.
6. Timeline Histori: Gabungan Makanan/Air/Berat/Workout. Ada tombol Delete (Hapus DB & Chart auto-refresh).
7. UX Desktop: Sub-tab (seperti Nutrisi/Gym) sekarang bisa di-klik-tahan-geser (Drag) dan di-scroll pakai roda mouse untuk pengguna laptop.

[FITUR ADMIN DASHBOARD (100% SELESAI - BARU)]:
1. Command `/admin` khusus ADMIN_ID.
2. Statistik User: Total, Aktif VIP, Expired, Banned, dan BANDEL (Expired tapi masih aktif dalam 24 jam).
3. List User dengan Filter & Pagination (Next/Prev).
4. Fitur KICK (Hard Ban): Mencabut akses, mengubah `is_banned = TRUE`, memberi alasan banned, dan mengirim notif ke user.
5. Fitur UNBAN: Mengembalikan akses (default 30 hari) dan menghapus status banned.
6. Tracking: Kolom `last_active_at` di DB update setiap kali user berinteraksi dengan bot.

[FITUR DATA PERSISTENCE & BACKUP (100% SELESAI - BARU)]:
1. Schema DB Diperluas: `is_banned`, `last_active_at`, `banned_at`, `banned_reason` di tabel `users`.
2. Script `scripts/backup_db.ps1`: Backup database PostgreSQL ke file `.sql` lokal.
3. Windows Task Scheduler: Backup berjalan otomatis setiap jam 2 pagi.
4. Git Ignore: Folder `backups/` dan `*.sql` sudah di-ignore, aman dari kebocoran repo.

[BUG YANG SUDAH DIPERBAIKI (HISTORIS)]:
1. Double Weight Log (Diperbaiki dengan Guard Insert / Update jika hari ini sudah ada).
2. Workout tidak muncul di History (Sudah ditambahkan query `workout_logs`).
3. Unit (kcal/ml/kg) & Jam hilang di History (Sudah ditambahkan).
4. Delete tanpa konfirmasi (Sudah pakai `confirm()` JS).
5. Float Noise Berat Badan (misal 70.8000001) -> Diperbaiki pakai `round(float(), 1)`.

=====================================================
TUGAS SELANJUTNYA (FASE 5: INFRASTRUKTUR & PAYMENT)
=====================================================
1. [ ] Deploy ke VPS (Vultr/DigitalOcean/AWS) agar bot jalan 24/7 tanpa laptop nyala.
2. [ ] Pindah Database ke Cloud (Supabase/Neon) agar sinkron dan aman.
3. [ ] Integrasi Payment Gateway Asli (Midtrans/Xendit QRIS) untuk otomatisasi VIP.
4. [ ] Scheduler Auto-Cut: Hapus masa aktif VIP jika sudah lewat tanggal (Bisa pakai APScheduler atau Cron).
5. [ ] Ganti URL statis Mini App di BotFather ke Domain VPS yang permanen (bukan Ngrok lagi).

=====================================================
CARA MENJALANKAN DI LOKAL (SOP UNTUK AI & USER)
=====================================================
1. Buka Docker Desktop.
2. Terminal 1: `docker start gymmate_db` (Pastikan container DB nyala).
3. Terminal 2: `python main.py`
4. Terminal 3: `ngrok http 8000` (Update URL di `handlers/start.py` dan BotFather jika berubah).
5. Untuk test backup DB: `powershell -ExecutionPolicy Bypass -File "D:\bot_gym\scripts\backup_db.ps1"`

=====================================================
CATATAN PENTING:
- Jangan hapus file ini.
- Git Branch aktif: `main`. Repo GitHub: `d4c080904/telegram_bot_serbaguna`.
- Semua kode Mini App terbaru sudah di-push ke GitHub.
=====================================================