@echo off
rem ===================================================================
rem  INICIAR.bat - forma oficial de abrir o NetProbe Wi-Fi.
rem  Basta dar dois cliques neste arquivo.
rem  Ele procura o Python (comando "python" ou "py") e executa o run.py.
rem ===================================================================
chcp 65001 >nul
cd /d "%~dp0"
title NetProbe Wi-Fi

where python >nul 2>nul
if %errorlevel%==0 (
  python run.py %*
  goto fim
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run.py %*
  goto fim
)
echo.
echo Python nao encontrado. Instale o Python 3.8 ou mais novo em https://www.python.org
echo (marque a opcao "Add Python to PATH" na instalacao).

:fim
echo.
echo NetProbe encerrado.
pause
