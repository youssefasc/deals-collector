#!/usr/bin/env bash
# تثبيت جامع «عروض متتفوتش» على سيرفر Ubuntu (Oracle Cloud Always Free — Ampere A1 / ARM64)
# آمن تشغيله أكتر من مرة. بيعمل:
#   Docker + Swap 4GB + نسخة الكود + بناء الصورة + تشغيل الجامع (يرجع لوحده لو وقع)
#   + تحديث تلقائي كل 15 دقيقة من GitHub + مراقب (watchdog) كل 5 دقايق
# المتغيرات المطلوبة في /opt/collector/collector.env:
#   INGEST_TOKEN   مفتاح الجامع (نفس اللي في Supabase)
#   GITHUB_TOKEN   توكن GitHub للقراءة بس (Fine-grained → Contents: Read-only على الريبو ده)
set -euo pipefail
APP=/opt/collector
REPO=youssefasc/deals-collector
ENVF=$APP/collector.env
log(){ echo "[collector-install] $*"; }

[ -f "$ENVF" ] || { echo "ملف $ENVF مش موجود"; exit 1; }
set -a; . "$ENVF"; set +a
: "${INGEST_TOKEN:?INGEST_TOKEN ناقص}"; : "${GITHUB_TOKEN:?GITHUB_TOKEN ناقص}"

log "Docker + git"
export DEBIAN_FRONTEND=noninteractive
command -v docker >/dev/null || { apt-get update -y; apt-get install -y docker.io git; }
systemctl enable --now docker

log "Swap 4GB (أمان للمتصفح)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

log "الكود"
if [ ! -d $APP/src/.git ]; then
  git clone -q "https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git" $APP/src
else
  git -C $APP/src remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git"
  git -C $APP/src pull -q
fi

# متغيرات الجامع نفسه (من غير توكن GitHub)
K=$(grep -o 'SUPABASE_KEY: .*' $APP/src/.github/workflows/collector.yml | cut -d' ' -f2)
cat > $APP/runtime.env <<ENV
SUPABASE_URL=${SUPABASE_URL:-https://unwzvhdwxmlmknvgvrhp.supabase.co}
SUPABASE_KEY=${SUPABASE_KEY:-$K}
INGEST_TOKEN=${INGEST_TOKEN}
AMAZON_MAIN=${AMAZON_MAIN:-0}
DB_CONCURRENCY=${DB_CONCURRENCY:-1}
SWEEP_WORKERS=${SWEEP_WORKERS:-2}
PYTHONUNBUFFERED=1
ENV
chmod 600 $APP/runtime.env $ENVF

install -m 755 $APP/src/deploy/oracle/collector-run.sh /usr/local/bin/collector-run
install -m 755 $APP/src/deploy/oracle/collector-update.sh /usr/local/bin/collector-update
install -m 755 $APP/src/deploy/oracle/collector-watchdog.sh /usr/local/bin/collector-watchdog
cp $APP/src/deploy/oracle/collector-*.service $APP/src/deploy/oracle/collector-*.timer /etc/systemd/system/
systemctl daemon-reload

log "بناء وتشغيل"
/usr/local/bin/collector-run
systemctl enable --now collector-update.timer collector-watchdog.timer
log "تمام ✅ — اللوج: sudo docker logs -f collector"
