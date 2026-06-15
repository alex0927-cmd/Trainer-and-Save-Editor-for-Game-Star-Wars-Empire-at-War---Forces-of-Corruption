@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

if not exist "dist\EAW_FOC_Trainer.exe" (
    echo Спочатку зберіть exe: build.bat
    exit /b 1
)

set "STAGING=release\EAW_FOC_Tools_v1.0.0_Windows"
set "ZIP=release\EAW_FOC_Tools_v1.0.0_Windows.zip"

if exist "%STAGING%" rmdir /s /q "%STAGING%"
mkdir "%STAGING%"

copy /y "dist\EAW_FOC_Trainer.exe" "%STAGING%\"
copy /y "dist\EAW_FOC_Editor.exe" "%STAGING%\"
copy /y "Запуск_Трейнера.bat" "%STAGING%\"
copy /y "Запуск_Редактора.bat" "%STAGING%\"
copy /y "README.md" "%STAGING%\"
copy /y "INSTALL.md" "%STAGING%\"

if exist "%ZIP%" del /f "%ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path '%STAGING%\*' -DestinationPath '%ZIP%' -Force"

echo [OK] %ZIP%
exit /b 0
