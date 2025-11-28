# run.ps1 - Script para ejecutar HybridLogisticsHub en PowerShell
# Uso: .\run.ps1

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   HybridLogisticsHub - Iniciando..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Docker está corriendo
$dockerRunning = docker info 2>$null
if (-not $?) {
    Write-Host "[ERROR] Docker no esta corriendo. Por favor inicia Docker Desktop." -ForegroundColor Red
    exit 1
}

# Ir al directorio del script
Set-Location $PSScriptRoot

# Verificar si los contenedores están corriendo
$postgresRunning = docker ps | Select-String "logistics_postgres"
if (-not $postgresRunning) {
    Write-Host "[INFO] Levantando bases de datos..." -ForegroundColor Yellow
    docker-compose up -d
    Write-Host "[INFO] Esperando a que las bases de datos inicien..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "[OK] Bases de datos corriendo" -ForegroundColor Green
Write-Host "    - PostgreSQL: localhost:5433" -ForegroundColor Gray
Write-Host "    - MongoDB: localhost:27017" -ForegroundColor Gray
Write-Host ""

Write-Host "[INFO] Iniciando API..." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   API disponible en:" -ForegroundColor White
Write-Host "   http://localhost:8000" -ForegroundColor Green
Write-Host "   http://localhost:8000/docs (Swagger)" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Presiona Ctrl+C para detener" -ForegroundColor Yellow
Write-Host ""

# Ejecutar la API
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
