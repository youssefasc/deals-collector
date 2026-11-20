@echo off
chcp 65001 >nul
echo جامع عروض متتفوتش - التثبيت والتشغيل
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
