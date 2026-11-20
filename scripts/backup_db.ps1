# scripts/backup_db.ps1
# Backup PostgreSQL GymMate — simpan 7 hari terakhir

$date = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupDir = "D:\bot_gym\backups"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }

$backupFile = "$backupDir\gymmate_$date.sql"

# Cek container hidup
$containerRunning = docker ps --filter "name=gymmate_db" --filter "status=running" --format "{{.Names}}"
if (-not $containerRunning) {
    Write-Host "❌ Container gymmate_db gak jalan. Backup dibatalkan." -ForegroundColor Red
    exit 1
}

# Backup
docker exec gymmate_db pg_dump -U gymmate gymmate_db > $backupFile

if ((Test-Path $backupFile) -and (Get-Item $backupFile).Length -gt 0) {
    $sizeKB = [math]::Round((Get-Item $backupFile).Length / 1KB, 1)
    Write-Host "✅ Backup OK: $backupFile ($sizeKB KB)" -ForegroundColor Green
} else {
    Write-Host "❌ Backup gagal." -ForegroundColor Red
    Remove-Item $backupFile -Force -ErrorAction SilentlyContinue
}

# Hapus backup > 7 hari
Get-ChildItem $backupDir -Filter "gymmate_*.sql" -ErrorAction SilentlyContinue | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | 
    Remove-Item -Force
Write-Host "🧹 Cleanup: backup > 7 hari dihapus."