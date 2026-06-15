@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

:: Запуск трейнера через Python (обхід блокування Windows Security для .exe)
:: Потрібні права адміністратора для доступу до пам'яті гри

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Запит прав адміністратора...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "PYTHONPATH=%~dp0"
set "PATH=%LocalAppData%\Programs\Python\Python314;%LocalAppData%\Programs\Python\Python314\Scripts;%PATH%"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ПОМИЛКА] Python не знайдено. Встановіть Python 3.10+ з python.org
    echo Потім: pip install pymem
    pause
    exit /b 1
)

echo Запуск EAW FOC Trainer...
python -c "import pymem" >nul 2>&1
if %errorlevel% neq 0 (
    echo Встановлення pymem...
    pip install pymem -q
)

python -c "import keyboard" >nul 2>&1
if %errorlevel% neq 0 (
    echo Встановлення keyboard...
    pip install keyboard -q
)

start "" pythonw "%~dp0trainer_main.py"
if %errorlevel% neq 0 (
    python "%~dp0trainer_main.py"
)
exit /b 0
