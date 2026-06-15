@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

where gh >nul 2>&1
if %errorlevel% neq 0 (
    echo [ПОМИЛКА] GitHub CLI (gh) не знайдено. Встановіть: winget install GitHub.cli
    pause
    exit /b 1
)

gh auth status >nul 2>&1
if %errorlevel% neq 0 (
    echo Спочатку увійдіть у GitHub:
    echo   gh auth login
    pause
    exit /b 1
)

if not exist "release\EAW_FOC_Tools_v1.0.0_Windows.zip" (
    echo Збірка release zip...
    call scripts\pack_release.bat
)

echo Створення GitHub Release v1.0.0...
gh release create v1.0.0 "release\EAW_FOC_Tools_v1.0.0_Windows.zip" ^
  --title "v1.0.0 — Trainer + XML Editor (Windows)" ^
  --notes-file "scripts\RELEASE_NOTES_v1.0.0.md"

if %errorlevel%==0 (
    echo.
    echo [OK] Release опубліковано!
    gh release view v1.0.0 --web
) else (
    echo [ПОМИЛКА] Не вдалося створити release. Можливо тег v1.0.0 вже існує.
)
pause
