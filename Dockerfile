# ============================================
# Docker Image buat GymMate Bot
# ============================================

FROM python:3.11-slim

# Set working directory di dalam container
WORKDIR /app

# Install system dependencies yang dibutuhin bot ini
# libgl1 & libglib2.0-0 wajib buat OpenCV (Scan Barcode)
# gcc & postgresql-client buat jaga-jaga kalau asyncpg butuh compile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    gcc \
    postgresql-client \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements dulu biar caching-nya cepet
COPY requirements.txt .

# Install library Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy semua sisa file project
COPY . .

# Bikin folder kalau lu butuh nyimpen file temp (opsional)
RUN mkdir -p /app/temp

# Jalanin bot
CMD ["python", "main.py"]