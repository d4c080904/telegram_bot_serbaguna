# ============================================
# Docker Image buat Bot Serba Guna
# ============================================

FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg buat yt-dlp & instaloader
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs

CMD ["python", "main.py"]