@echo off
REM run.bat - Script para ejecutar HybridLogisticsHub en Windows
REM Uso: doble clic o ejecutar desde terminal

echo ============================================
echo    HybridLogisticsHub - Iniciando...
echo ============================================
echo.

REM Verificar si Docker está corriendo
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no esta corriendo. Por favor inicia Docker Desktop.
    pause
    exit /b 1
)

REM Ir al directorio del script
cd /d "%~dp0"

REM Verificar si los contenedores están corriendo
docker ps | findstr "logistics_postgres" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Levantando bases de datos...
    docker-compose up -d
    echo [INFO] Esperando a que las bases de datos inicien...
    timeout /t 5 /nobreak >nul
)

echo.
echo [OK] Bases de datos corriendo
echo     - PostgreSQL: localhost:5433
echo     - MongoDB: localhost:27017
echo.

REM Activar entorno virtual y ejecutar
echo [INFO] Iniciando API...
echo.
echo ============================================
echo    API disponible en:
echo    http://localhost:8000
echo    http://localhost:8000/docs (Swagger)
echo ============================================
echo.
echo Presiona Ctrl+C para detener
echo.

..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
