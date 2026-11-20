#!/usr/bin/env bash
# لو الجامع واقف أو مهنّج (مفيش نبضة من 15 دقيقة) → إعادة تشغيل
running=$(docker inspect -f '{{.State.Running}}' collector 2>/dev/null || echo false)
if [ "$running" != "true" ]; then
  echo "watchdog: collector not running → start"; docker start collector || /usr/local/bin/collector-run; exit 0
fi
started=$(date -d "$(docker inspect -f '{{.State.StartedAt}}' collector)" +%s)
beat=$(docker exec collector cat /tmp/collector_alive 2>/dev/null | cut -d. -f1)
now=$(date +%s)
if [ $((now - started)) -gt 900 ] && { [ -z "$beat" ] || [ $((now - beat)) -gt 900 ]; }; then
  echo "watchdog: no heartbeat for 15m → restart"; docker restart collector
fi
