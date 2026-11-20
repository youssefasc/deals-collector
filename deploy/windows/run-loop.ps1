# بيشغّل الجامع على طول: لو وقع يرجّعه، ولو فيه تحديث على GitHub يجيبه ويعيد التشغيل،
# ولو هنّج (مفيش نبضة ١٥ دقيقة) يعيد تشغيله.
$App = Join-Path $env:LOCALAPPDATA "OroodCollector"
$Src = Join-Path $App "src"
$Py  = Join-Path $App "venv\Scripts\python.exe"
$Log = Join-Path $App "collector.log"
$Beat = Join-Path $env:TEMP "collector_alive"
function L($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [loop] $m" | Out-File -Append -Encoding UTF8 $Log }

# المتغيرات من الملف
Get-Content (Join-Path $App "collector.env") | ForEach-Object {
  if ($_ -match "^\s*([^#=]+)=(.*)$") { [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process") }
}
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")

function Start-Collector {
  if ((Test-Path $Log) -and (Get-Item $Log).Length -gt 20MB) { Move-Item $Log "$Log.old" -Force }
  L "starting collector ($(git -C $Src log -1 --format='%h %s' 2>$null))"
  return Start-Process -FilePath $Py -ArgumentList "main.py" -WorkingDirectory $Src -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput "$Log.out" -RedirectStandardError "$Log.err"
}
function Stop-Collector($p) {
  # بنقفل الشجرة كلها (بايثون في الـ venv بيشتغل كعمليتين على Windows)
  if ($p) { taskkill /T /F /PID $p.Id 2>$null | Out-Null }
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*main.py*" -and ((Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)" -ErrorAction SilentlyContinue).Name -ne "explorer.exe") -and ($_.ExecutablePath -like "*OroodCollector*" -or $_.ExecutablePath -like "*Python*") } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Get-CimInstance Win32_Process -Filter "Name='chrome.exe' OR Name='headless_shell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -like "*ms-playwright*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

$p = Start-Collector
$started = Get-Date
$lastUpdate = Get-Date
while ($true) {
  Start-Sleep -Seconds 60
  # نقل لوج العملية للوج الرئيسي
  foreach ($f in "$Log.out","$Log.err") { if (Test-Path $f) { Get-Content $f -ErrorAction SilentlyContinue | Out-File -Append -Encoding UTF8 $Log; Clear-Content $f -ErrorAction SilentlyContinue } }

  if ($p.HasExited) { L "collector exited (code $($p.ExitCode)) → restart in 30s"; Stop-Collector $null; Start-Sleep 30; $p = Start-Collector; $started = Get-Date; continue }

  # watchdog: مفيش نبضة من ١٥ دقيقة (بعد أول ١٥ دقيقة من التشغيل)
  if (((Get-Date) - $started).TotalMinutes -gt 15) {
    $age = if (Test-Path $Beat) { ((Get-Date) - (Get-Item $Beat).LastWriteTime).TotalMinutes } else { 999 }
    if ($age -gt 15) { L "no heartbeat for $([int]$age) min → restart"; Stop-Collector $p; $p = Start-Collector; $started = Get-Date; continue }
  }

  # تحديث تلقائي كل ١٥ دقيقة
  if (((Get-Date) - $lastUpdate).TotalMinutes -ge 15) {
    $lastUpdate = Get-Date
    try {
      git -C $Src fetch -q origin main 2>$null
      if ((git -C $Src rev-parse HEAD) -ne (git -C $Src rev-parse origin/main)) {
        L "update found → pulling"
        Stop-Collector $p
        git -C $Src reset -q --hard origin/main
        & $Py -m pip install -q -r (Join-Path $Src "requirements.txt") 2>$null
        Copy-Item (Join-Path $Src "deploy\windows\run-loop.ps1") (Join-Path $App "run-loop.ps1") -Force
        $p = Start-Collector; $started = Get-Date
      }
    } catch { L "update check failed: $_" }
  }
}
