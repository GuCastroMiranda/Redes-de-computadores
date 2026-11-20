@echo off
chcp 65001 >nul
cd /d "%~dp0"
title NetProbe Wi-Fi
python run.py
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar. Verifique se o Python esta instalado: python --version
  pause
)
