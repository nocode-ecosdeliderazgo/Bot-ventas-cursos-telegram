# Script para activar automáticamente el entorno virtual
# Este script se ejecuta automáticamente al abrir una terminal en este proyecto

Write-Host "Verificando entorno virtual..." -ForegroundColor Cyan

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Entorno virtual encontrado. Activando..." -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "Entorno virtual activado. Python: $(python --version)" -ForegroundColor Green
    
    # Verificar si las dependencias están instaladas
    $installed_packages = pip list | Select-String "asyncpg|python-telegram-bot"
    if ($installed_packages) {
        Write-Host "Dependencias principales instaladas" -ForegroundColor Green
    } else {
        Write-Host "Algunas dependencias pueden no estar instaladas. Ejecuta: pip install -r requirements.txt" -ForegroundColor Yellow
    }
} else {
    Write-Host "Entorno virtual no encontrado en .\venv\" -ForegroundColor Red
    Write-Host "Para crear el entorno virtual ejecuta: python -m venv venv" -ForegroundColor Yellow
}

Write-Host "Listo para trabajar en el bot de ventas!" -ForegroundColor Cyan 