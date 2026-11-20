#!/usr/bin/env bash
# نشر تلقائي زي Railway: لو فيه كود جديد على GitHub يبني ويشغّل النسخة الجديدة
set -euo pipefail
APP=/opt/collector
cd $APP/src
git fetch -q origin main
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
  git reset -q --hard origin/main
  /usr/local/bin/collector-run
fi
