@echo off
REM ============================================================
REM  Genera el ejecutable (.exe) del Conversor MarkItDown
REM  Requisitos: Python instalado y en el PATH.
REM  Uso: doble clic sobre este archivo, o ejecutarlo en cmd.
REM ============================================================

echo.
echo === Conversor MarkItDown - Generador de EXE ===
echo.

echo [1/3] Instalando/actualizando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR instalando dependencias. Revisa el mensaje anterior.
    pause
    exit /b 1
)

echo.
echo [2/3] Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ConversorMarkItDown.spec del /q ConversorMarkItDown.spec

echo.
echo [3/3] Generando el ejecutable (esto puede tardar varios minutos)...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "ConversorMarkItDown" ^
    --collect-all markitdown ^
    --collect-all magika ^
    app.py

if errorlevel 1 (
    echo.
    echo ERROR generando el ejecutable. Revisa el mensaje anterior.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  LISTO. El ejecutable esta en:  dist\ConversorMarkItDown.exe
echo  Ese es el archivo que envias a tus usuarios.
echo ============================================================
echo.
pause
