"""
تشغيل استقبال كتالوج Breadfast من المصادر المصرح بيها.

  python -m breadfast_data_acquisition.run            # يقرا كل الملفات في data/breadfast/inbox
  BREADFAST_API_URL=... BREADFAST_API_KEY=... python -m breadfast_data_acquisition.run   # فيد/API رسمي

لو مفيش أي مصدر مفعّل → بيطبع ده وبيقف من غير ما يكتب أي حاجة.
"""
import csv, glob, io, json, os, sys, time, datetime
import httpx
from .normalize import normalize, dedupe, completeness

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://unwzvhdwxmlmknvgvrhp.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "")
STORE = "breadfast"
INBOX = os.environ.get("BREADFAST_INBOX", "data/breadfast/inbox")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read_files():
    """vendor_file / supplier_export: CSV أو JSON أو XLSX."""
    for path in sorted(p for p in glob.glob(os.path.join(INBOX, "*")) if not p.endswith("README.txt")):
        ext = path.lower().rsplit(".", 1)[-1]
        src = f"file:{os.path.basename(path)}"
        at = datetime.datetime.fromtimestamp(os.path.getmtime(path), datetime.timezone.utc).isoformat()
        if ext == "csv":
            with open(path, encoding="utf-8-sig") as f:
                yield src, at, list(csv.DictReader(f))
        elif ext == "json":
            d = json.load(open(path, encoding="utf-8"))
            yield src, at, d if isinstance(d, list) else d.get("products") or d.get("items") or []
        elif ext in ("xlsx", "xlsm"):
            import openpyxl
            ws = openpyxl.load_workbook(path, read_only=True, data_only=True).active
            rows = list(ws.iter_rows(values_only=True))
            head = [str(h or "") for h in rows[0]] if rows else []
            yield src, at, [dict(zip(head, r)) for r in rows[1:]]


def read_official_api():
    """official_api: فيد رسمي بعد اتفاقية مع Breadfast. الشكل المتوقع: JSON list أو {products:[...]} مع صفحات."""
    url, key = os.environ.get("BREADFAST_API_URL"), os.environ.get("BREADFAST_API_KEY")
    if not url:
        return
    rows, page = [], 1
    with httpx.Client(timeout=60, headers={"Authorization": f"Bearer {key}"} if key else {}) as c:
        while True:
            r = c.get(url, params={"page": page})
            r.raise_for_status()
            d = r.json()
            chunk = d if isinstance(d, list) else d.get("products") or d.get("items") or []
            rows += chunk
            if not chunk or (isinstance(d, dict) and not d.get("next") and page >= int(d.get("pages", page))):
                break
            page += 1
    yield "official_api", now_iso(), rows


def rpc(fn, payload):
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/rpc/{fn}", timeout=120,
                   headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"},
                   json={"token": INGEST_TOKEN, **payload})
    r.raise_for_status()
    return r.json() if r.content else None


def existing_ids():
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/products", timeout=60, params={"select": "pid,price", "store": f"eq.{STORE}", "in_stock": "is.true", "limit": "200000"},
                  headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    return {x["pid"]: x["price"] for x in r.json()} if r.status_code == 200 else {}


def process(source, at, rows, dry=False):
    good, bad = [], 0
    for row in rows:
        it, probs = normalize(row, source, at)
        if it:
            good.append(it)
        else:
            bad += 1
    items, dups = dedupe(good)
    comp = completeness(items)
    print(f"[{source}] صفوف {len(rows)} · صالحة {len(good)} · مرفوضة {bad} · مكرر {dups} · نهائي {len(items)}")
    print("   اكتمال الحقول %:", json.dumps(comp, ensure_ascii=False))
    if dry or not items:
        return
    before = existing_ids()
    prods = [{"store": STORE, **{k: it[k] for k in ("pid", "title", "image", "url", "price", "list_price", "discount_pct", "in_stock", "category", "src_category")}} for it in items]
    for i in range(0, len(prods), 50):
        rpc("ingest_products", {"items": prods[i:i + 50]})
    det = [{"id": f"{STORE}:{it['pid']}", "store": STORE, **{k: it.get(k) for k in ("brand", "barcode", "description", "size", "pack_count", "region", "title_en", "source", "source_at")},
            "source_category": it["src_category"]} for it in items]
    for i in range(0, len(det), 200):
        rpc("ingest_details", {"items": det[i:i + 200]})
    now_ids = {it["pid"] for it in items}
    removed = set(before) - now_ids if source == "official_api" else set()   # الحذف بيتحسب بس من مصدر كامل رسمي
    if removed:
        gone = [{"store": STORE, "pid": p, "price": before[p], "in_stock": False} for p in removed]
        for i in range(0, len(gone), 50):
            rpc("ingest_products", {"items": gone[i:i + 50]})
        print(f"   منتجات اختفت من الكتالوج الرسمي: {len(removed)} (بتتعلّم غير متوفرة)")
    rpc("log_acquisition_run", {"r": {"store": STORE, "source": source, "rows_in": len(rows), "rows_valid": len(good), "rows_dup": dups,
                                      "new_products": len(now_ids - set(before)), "removed_products": len(removed), "completeness": comp}})


def main():
    dry = "--dry" in sys.argv
    found = False
    for gen in (read_official_api(), read_files()):
        for source, at, rows in gen or []:
            found = True
            process(source, at, rows, dry)
    if not found:
        print("مفيش مصدر بيانات مصرّح بيه مفعّل لـ Breadfast:")
        print(" - official_api: BREADFAST_API_URL مش متحدد (محتاج اتفاقية مع Breadfast)")
        print(f" - vendor_file / supplier_export: الفولدر {INBOX} فاضي")
        print("مفيش أي بيانات اتكتبت.")


if __name__ == "__main__":
    main()
