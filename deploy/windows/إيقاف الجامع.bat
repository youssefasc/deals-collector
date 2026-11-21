@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unregister-ScheduledTask -TaskName OroodCollector -Confirm:$false -ErrorAction SilentlyContinue; Unregister-ScheduledTask -TaskName OroodCollectorStatus -Confirm:$false -ErrorAction SilentlyContinue; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*OroodCollector*' -or $_.ExecutablePath -like '*OroodCollector*' -or $_.ExecutablePath -like '*ms-playwright*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host 'الجامع اتوقف واتشال من التشغيل التلقائي'"
pause
