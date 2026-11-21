@echo off
chcp 65001 >nul
rem خط بيدعم العربي في الشاشة السودا (بدل علامات ????)
if not "%1"=="go" (
  reg add "HKCU\Console" /v FaceName /t REG_SZ /d "Courier New" /f >nul
  reg add "HKCU\Console\%%SystemRoot%%_system32_cmd.exe" /v FaceName /t REG_SZ /d "Courier New" /f >nul
  start "جامع عروض متتفوتش" cmd /c ""%~f0" go"
  exit /b
)
echo جامع عروض متتفوتش - التثبيت والتشغيل
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
