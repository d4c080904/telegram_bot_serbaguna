# 🤖 Telegram Bot Serbaguna

Bot Telegram multifungsi yang dibangun menggunakan Python. Proyek ini didesain secara modular untuk memudahkan pengembangan, dilengkapi dengan integrasi AI (Gemini & Groq) serta berbagai fitur utilitas seperti pelacak kalori.

## ✨ Fitur Utama

- **Integrasi AI**: Dukungan cerdas menggunakan Gemini AI dan Groq API untuk merespons pengguna.
- **Pelacak Kalori**: Fitur untuk mencatat dan memantau asupan kalori harian.
- **Ekspor Data**: Dukungan ekspor data (CSV) untuk riwayat pengguna.
- **Arsitektur Modular**: Kode terstruktur rapi berdasarkan *handlers*, *services*, dan *database*.
- **Docker Ready**: Siap dijalankan menggunakan container Docker untuk deployment yang mudah.

## 📋 Prasyarat

Sebelum menjalankan bot ini, pastikan Anda sudah memiliki:
- **Python 3.9+** (Jika menjalankan secara lokal)
- **Docker & Docker Compose** (Jika menjalankan via container)
- **Telegram Bot Token** (Dapatkan dari [@BotFather](https://t.me/botfather))
- **API Key** untuk layanan AI yang digunakan (Groq / Google Gemini)

## 🚀 Cara Instalasi (Lokal)

1. **Clone repositori ini:**
   ```bash
   git clone https://github.com/d4c080904/telegram_bot_serbaguna.git
   cd telegram_bot_serbaguna