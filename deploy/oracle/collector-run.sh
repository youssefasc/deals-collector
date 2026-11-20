#!/usr/bin/env bash
# يبني صورة الجامع من الكود الحالي ويشغّلها (ويرجع لوحده لو وقع)
set -euo pipefail
APP=/opt/collector
docker build -q -t collector:latest $APP/src >/dev/null
docker rm -f collector >/dev/null 2>&1 || true
docker run -d --name collector --restart unless-stopped --env-file $APP/runtime.env \
  --shm-size=1g --log-opt max-size=20m --log-opt max-file=3 collector:latest >/dev/null
docker image prune -f >/dev/null 2>&1 || true
echo "collector started: $(git -C $APP/src log -1 --format='%h %s')"
