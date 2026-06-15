@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONPATH=%~dp0"
set "PATH=%LocalAppData%\Programs\Python\Python314;%LocalAppData%\Programs\Python\Python314\Scripts;%PATH%"
start "" pythonw "%~dp0editor_main.py"
exit /b 0
