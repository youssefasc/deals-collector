"""فحص قراءة بس لمصادر بيانات عامة: بيطبع الحالة وجزء من الرد أو نتايج regex."""
import os, re, sys, json, urllib.request, gzip, zlib
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
urls = os.environ.get("URLS", "").split()
pat = os.environ.get("GREP", "")
n = int(os.environ.get("BYTES", "3000") or 3000)
hdr = json.loads(os.environ.get("HDRS") or "{}")
for u in urls:
    print("=" * 19, u)
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8", "Accept-Encoding": "gzip", "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", **hdr})
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read(); st = r.status; h = r.headers
            if h.get("Content-Encoding") == "gzip": b = gzip.decompress(b)
    except urllib.error.HTTPError as e:
        b = e.read(); st = e.code; h = e.headers
    except Exception as e:
        print("ERROR", e); continue
    t = b.decode("utf-8", "replace")
    print("STATUS", st, "SIZE", len(t), "TYPE", h.get("Content-Type"))
    if pat:
        from collections import Counter
        for m, c in Counter(re.findall(pat, t)).most_common(80):
            print(c, (m if isinstance(m, str) else " | ".join(m))[:n])
    else:
        off = int(os.environ.get("OFF", "0") or 0)
        print(t[off:off + n])
