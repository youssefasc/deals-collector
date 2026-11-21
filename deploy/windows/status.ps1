# شباك حالة الجامع — بالعربي، بيوريك الجامع بيعمل إيه دلوقتي (بيتحدّث كل ثانيتين)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$App  = Join-Path $env:LOCALAPPDATA "OroodCollector"
$Log  = Join-Path $App "collector.log"
$Stat = Join-Path $App "status.txt"

$f = New-Object Windows.Forms.Form
$f.Text = "جامع عروض متتفوتش"
$f.RightToLeft = "Yes"; $f.RightToLeftLayout = $true
$f.Size = New-Object Drawing.Size(720, 520); $f.StartPosition = "CenterScreen"
$f.Font = New-Object Drawing.Font("Segoe UI", 11)
$f.BackColor = [Drawing.Color]::White

$head = New-Object Windows.Forms.Label
$head.Dock = "Top"; $head.Height = 70; $head.Padding = New-Object Windows.Forms.Padding(12)
$head.Font = New-Object Drawing.Font("Segoe UI", 15, [Drawing.FontStyle]::Bold)
$f.Controls.Add($head)

$box = New-Object Windows.Forms.ListBox
$box.Dock = "Fill"; $box.RightToLeft = "Yes"; $box.Font = New-Object Drawing.Font("Segoe UI", 10)
$box.IntegralHeight = $false
$f.Controls.Add($box); $box.BringToFront()

$foot = New-Object Windows.Forms.Label
$foot.Dock = "Bottom"; $foot.Height = 30; $foot.Padding = New-Object Windows.Forms.Padding(8, 4, 8, 4)
$foot.ForeColor = [Drawing.Color]::Gray
$foot.Text = "تقدر تقفل الشباك ده عادي — الجامع هيفضل شغال في الخلفية. ولإيقافه افتح «إيقاف الجامع»."
$f.Controls.Add($foot)

function Tr($l) {
  # ترجمة سطور اللوج المهمة لكلام عربي مفهوم
  $map = @(
    @('\[loop\] starting collector', 'بدأ الجمع ▶'),
    @('\[loop\] batch done → next run at (\S+)', 'خلصت الدفعة ✅ — الدفعة الجاية الساعة $1'),
    @('\[loop\] collector exited', 'الجامع وقف فجأة — بيرجع يشتغل لوحده ↻'),
    @('\[loop\] update found', 'فيه تحديث جديد — بيتنزل ⬇'),
    @('\[loop\] no heartbeat', 'الجامع كان مهنّج — اتعاد تشغيله ↻'),
    @('2b page (\d+)/(\d+): (\d+) products', '2B: صفحة $1 من $2 — $3 منتج'),
    @('2b (home )?error.*(403|blocked)', '2B رفض الطلب دلوقتي — هيحاول تاني بعد شوية'),
    @('2b (home )?error', '2B: خطأ مؤقت — هيحاول تاني'),
    @('dubaiphone done: (\d+) products from (\d+) categories', 'دبي فون: خلص — $1 منتج من $2 قسم ✅'),
    @('dubaiphone home:', 'دبي فون: فتح الموقع'),
    @('dubaiphone (home )?error.*(403|429|blocked)', 'دبي فون رفض الطلب دلوقتي — هيحاول تاني بعد شوية'),
    @('dubaiphone (home )?error', 'دبي فون: خطأ مؤقت — هيحاول تاني')
  )
  foreach ($m in $map) {
    $r = [regex]::Match($l, $m[0])
    if ($r.Success) { $tm = if ($l -match '\d\d:\d\d(:\d\d)?') { $Matches[0] } else { '' }; return "$tm   " + $r.Result($m[1]) }
  }
  return $null
}

$script:pos = 0
$timer = New-Object Windows.Forms.Timer; $timer.Interval = 2000
$timer.Add_Tick({
  $running = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*main.py*" }).Count -gt 0
  $st = if (Test-Path $Stat) { Get-Content $Stat -Raw -Encoding UTF8 } else { "" }
  if ($running) { $head.Text = "🟢 شغال وبيجمع من 2B ودبي فون دلوقتي"; $head.ForeColor = [Drawing.Color]::FromArgb(22,130,60) }
  elseif ($st) { $head.Text = "⏸ " + $st.Trim(); $head.ForeColor = [Drawing.Color]::FromArgb(200,110,0) }
  else { $head.Text = "🔴 الجامع مش شغال — افتح «تشغيل الجامع»"; $head.ForeColor = [Drawing.Color]::Firebrick }
  if (Test-Path $Log) {
    $all = @(Get-Content $Log -Encoding UTF8 -ErrorAction SilentlyContinue)
    if ($all.Count -lt $script:pos) { $script:pos = 0 }
    $new = $all[$script:pos..($all.Count - 1)]; $script:pos = $all.Count
    foreach ($l in $new) { if ($l) { $t = Tr $l; if ($t) { $box.Items.Add($t) | Out-Null } } }
    while ($box.Items.Count -gt 300) { $box.Items.RemoveAt(0) }
    if ($box.Items.Count) { $box.TopIndex = $box.Items.Count - 1 }
  }
})
$timer.Start()
[void]$f.ShowDialog()
