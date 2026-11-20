# ═══════════════════════════════════════════════════════════════════
#  جامع «عروض متتفوتش» — 2B ودبي فون على كمبيوتر Windows (المتجرين اللي بيرفضوا السيرفرات)
#  بيشتغل ١٥ دقيقة كل ٣ ساعات بس عشان يوفّر النت
#  باقي المتاجر بيجمعها الجامع السحابي على Supabase لوحده
#  بيعمل كل حاجة لوحده: Python + Git + الكود + المتصفح + مهمة تشتغل مع فتح الكمبيوتر
#  وبيرجّع الجامع لو وقع، وبيحدّث نفسه من GitHub كل ١٥ دقيقة.
# ═══════════════════════════════════════════════════════════════════
param([string]$Token = "", [string]$GitToken = "", [switch]$NoTask)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$App  = Join-Path $env:LOCALAPPDATA "OroodCollector"
$Src  = Join-Path $App "src"
$Repo = "https://github.com/youssefasc/deals-collector.git"
function Say($m) { Write-Host "▶ $m" -ForegroundColor Cyan }
New-Item -ItemType Directory -Force -Path $App | Out-Null

function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}
function Need($exe, $wingetId) {
  if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
    Say "تثبيت $wingetId ..."
    winget install --id $wingetId -e --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    Refresh-Path
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { throw "$exe ماتثبتش — ثبّته يدوي وشغّل الملف تاني" }
  }
}
Need git "Git.Git"
Need python "Python.Python.3.12"

# 1) الكود — أول مرة GitHub هيفتح صفحة تسجيل دخول في المتصفح (تسجيل آمن، من غير ما تكتب باسورد هنا)
if (-not (Test-Path (Join-Path $Src ".git"))) {
  Say "تحميل الكود من GitHub ..."
  if ($GitToken) { git clone -q ("https://x-access-token:$GitToken@github.com/youssefasc/deals-collector.git") $Src }
  else { git clone -q $Repo $Src }
} else { Say "تحديث الكود ..."; git -C $Src pull -q }

# 2) بيئة بايثون + المتصفح
$Py = Join-Path $App "venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { Say "تجهيز بيئة بايثون ..."; python -m venv (Join-Path $App "venv") }
Say "تثبيت المكتبات ..."
& $Py -m pip install -q --upgrade pip
& $Py -m pip install -q -r (Join-Path $Src "requirements.txt")
Say "تثبيت متصفح Chromium ..."
& $Py -m playwright install chromium | Out-Null

# 3) الإعدادات — المفتاح بيتحفظ على جهازك بس
$EnvFile = Join-Path $App "collector.env"
if (-not $Token -and (Test-Path $EnvFile)) { $Token = ((Get-Content $EnvFile | Where-Object { $_ -like "INGEST_TOKEN=*" }) -replace "^INGEST_TOKEN=","") }
if (-not $Token) {
  $sec = Read-Host "الصق مفتاح الجامع (INGEST_TOKEN) ودوس Enter" -AsSecureString
  $Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
}
$Key = ((Select-String -Path (Join-Path $Src ".github\workflows\collector.yml") -Pattern "SUPABASE_KEY: (\S+)").Matches[0].Groups[1].Value)
@"
SUPABASE_URL=https://unwzvhdwxmlmknvgvrhp.supabase.co
SUPABASE_KEY=$Key
INGEST_TOKEN=$Token
AMAZON_MAIN=0
ONLY_STORES=2b,dubaiphone
RUN_MINUTES=15
EVERY_HOURS=3
DB_CONCURRENCY=1
SWEEP_WORKERS=2
PYTHONUNBUFFERED=1
PYTHONIOENCODING=utf-8
"@ | Set-Content -Encoding UTF8 $EnvFile
icacls $EnvFile /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null

# 4) سكريبت التشغيل الدائم
Copy-Item (Join-Path $Src "deploy\windows\run-loop.ps1") (Join-Path $App "run-loop.ps1") -Force

# 5) الكمبيوتر مايناميش وهو على الشاحن
powercfg /change standby-timeout-ac 0 2>$null
powercfg /change hibernate-timeout-ac 0 2>$null

# 6) مهمة تشتغل مع فتح الكمبيوتر، مخفية، وترجع لو وقعت
if (-not $NoTask) {
  Say "تسجيل التشغيل التلقائي ..."
  $act = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$App\run-loop.ps1`""
  $trg = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
  $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
         -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName "OroodCollector" -Action $act -Trigger $trg -Settings $set -Force | Out-Null
  Start-ScheduledTask -TaskName "OroodCollector"
}
Say "خلصنا ✅  الجامع شغال في الخلفية ومش هيظهر له شباك."
Say "اللوج هنا: $App\collector.log"
