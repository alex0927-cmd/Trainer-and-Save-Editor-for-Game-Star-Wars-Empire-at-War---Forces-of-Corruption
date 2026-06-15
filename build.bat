@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo === EAW FOC Tools Build ===
echo.

where uv >nul 2>&1
if %errorlevel%==0 (
    uv pip install -r requirements.txt --python python
) else (
    pip install -r requirements.txt
)

if not exist "dist" mkdir dist

echo.
echo Компіляція Trainer...
python -m PyInstaller --noconfirm EAW_FOC_Trainer.spec

echo.
echo Компіляція Editor...
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name "EAW_FOC_Editor" ^
    --paths "%~dp0" ^
    --collect-submodules pymem ^
    --hidden-import shared --hidden-import shared.paths --hidden-import shared.xml_store ^
    --hidden-import editor --hidden-import editor.app ^
    editor_main.py

if exist "dist\EAW_FOC_Trainer.exe" (
    powershell -NoProfile -Command "Unblock-File -LiteralPath 'dist\EAW_FOC_Trainer.exe'" 2>nul
    echo [OK] dist\EAW_FOC_Trainer.exe
)
if exist "dist\EAW_FOC_Editor.exe" (
    powershell -NoProfile -Command "Unblock-File -LiteralPath 'dist\EAW_FOC_Editor.exe'" 2>nul
    echo [OK] dist\EAW_FOC_Editor.exe
)

echo.
echo Якщо Windows блокує .exe — використовуйте Запуск_Трейнера.bat
pause
