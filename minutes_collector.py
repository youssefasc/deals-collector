"""
جامع «نون مينتس» (noon Minutes مصر) — مستقل تماماً عن باقي الجوامع.

المصدر: صفحات الموقع العامة minutes.noon.com/egypt-ar (مسموحة في robots.txt — الممنوع بس /_svc/ و /_vs/).
كل صفحة قسم فيها بيانات منظمة (schema.org JSON-LD) اللي الموقع بينشرها لمحركات البحث:
الاسم، SKU، العلامة التجارية، الصورة، السعر، السعر قبل الخصم — وكمان حالة التوفر (isBuyable).

النظام:
- طابور مهام (Priority Queue): كل مهمة = صفحة من قسم، وليها ميعاد تحديث.
- الصفحات اللي فيها خصومات/تغييرات = أولوية (كل دقيقة لو المعدل يسمح)، الباقي بيتلف عليه كل FULL_EVERY دقيقة.
- معدل طلبات ثابت ومهذب (RATE ثانية بين كل طلب) + تهدئة تلقائية لو الموقع رجّع 429/403/5xx.
- إعادة محاولة تلقائية للمهام الفاشلة.
- منتج جديد / تغير سعر / انتهاء خصم / نفاد / رجوع توفر → بتتسجل في قاعدة البيانات (ingest_products) مع تاريخ الأسعار.
- تفاصيل إضافية (الوصف، الحجم، عدد القطع، الماركة) من صفحة المنتج — للمنتجات الجديدة بس وبهدوء.
- تقرير حالة حقيقي كل دقيقة (status_noon_minutes): المعدل الفعلي لدورة الأولوية ودورة الكتالوج كله.
"""
import asyncio, json, os, re, random, time, heapq
import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://unwzvhdwxmlmknvgvrhp.supabase.co")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
INGEST_TOKEN = os.environ["INGEST_TOKEN"]
BASE = "https://minutes.noon.com/egypt-ar"
STORE = "noon_minutes"
REGION = "مصر — المنطقة الافتراضية للموقع"
RATE = float(os.environ.get("MINUTES_RATE", "1.2"))            # ثواني بين كل طلب والتاني (≈ 50 صفحة/دقيقة)
PRIORITY_EVERY = int(os.environ.get("PRIORITY_EVERY", "60"))    # ثانية — صفحات الخصومات
FULL_EVERY = int(os.environ.get("FULL_EVERY", "30")) * 60       # ثانية — باقي الكتالوج
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "0")) or None
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------- تصنيف أقسام نون مينتس لأقسام الموقع ----------
def site_category(code: str) -> str:
    c = code.lower()
    if "mobile" in c and "access" not in c: return "mobiles"
    if "laptop" in c: return "laptops"
    if "headphone" in c or "speaker" in c: return "audio"
    if "gaming" in c: return "gaming"
    if any(k in c for k in ("makeup", "skin", "fragrance", "bath_body", "grooming", "hair", "oral", "feminine", "beauty")): return "beauty"
    if any(k in c for k in ("home_improvement", "kitchen", "bath_bedding", "household", "laundry", "tissues", "disposables", "party")): return "home"
    return "grocery"


class Limiter:
    """طلب واحد كل RATE ثانية لكل الجامع، ولو الموقع اشتكى بنهدّي تلقائياً."""
    def __init__(self, rate):
        self.rate = rate; self.slow = 1.0; self.next = 0.0; self.lock = asyncio.Lock()

    async def wait(self):
        async with self.lock:
            now = time.monotonic()
            if self.next > now:
                await asyncio.sleep(self.next - now)
            self.next = max(now, self.next) + self.rate * self.slow + random.uniform(0, 0.3)

    def complain(self):
        self.slow = min(self.slow * 2, 30)

    def ok(self):
        self.slow = max(1.0, self.slow * 0.97)


class Collector:
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30, follow_redirects=True, headers={
            "User-Agent": UA, "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8", "Accept": "text/html"})
        self.db = httpx.AsyncClient(timeout=60, headers={
            "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"})
        self.lim = Limiter(RATE)
        self.q = []                      # (due, seq, cat, page)
        self.seq = 0
        self.pages = {}                  # (cat,page) -> {"prio": bool, "fails": int}
        self.known = {}                  # pid -> (price, list_price, in_stock)
        self.need_details = []
        self.details_done = set()
        self.st = {"started": time.time(), "requests": 0, "errors": 0, "items_seen": 0, "inserted": 0, "changed": 0,
                   "new_products": 0, "price_changes": 0, "discount_ended": 0, "out_of_stock": 0, "back_in_stock": 0,
                   "prio_cycle_secs": None, "full_cycle_secs": None, "categories": 0}
        self.prio_done_at = {}           # (cat,page) -> last refresh time (للقياس الفعلي)
        self.full_round_start = time.time(); self.full_seen = set()

    # ---------- HTTP ----------
    async def get(self, url, tries=4):
        for i in range(tries):
            await self.lim.wait()
            try:
                r = await self.http.get(url)
                self.st["requests"] += 1
                if r.status_code == 200:
                    self.lim.ok(); return r.text
                if r.status_code in (403, 429) or r.status_code >= 500:
                    self.lim.complain(); log("HTTP", r.status_code, url, "→ تهدئة", f"x{self.lim.slow:.1f}")
                    await asyncio.sleep(min(300, 10 * 2 ** i))
                    continue
                return None                                   # 404 وغيره: الصفحة مش موجودة
            except Exception as e:
                log("net error", type(e).__name__, url)
                await asyncio.sleep(5 * 2 ** i)
        self.st["errors"] += 1
        return None

    # ---------- قراءة صفحة القسم ----------
    @staticmethod
    def parse_listing(html: str):
        m = re.search(r'<script id="catalog-json-ld[^>]*>(.*?)</script>', html, re.S)
        items = json.loads(m.group(1)).get("itemListElement", []) if m else []
        # حالة التوفر: كل منتج في بيانات الصفحة ليه sku وبعده isBuyable
        buy = {}
        for mm in re.finditer(r'sku:"(Z[A-Z0-9]+-\d+)"(.{0,4000}?)isBuyable:(!0|!1)', html, re.S):
            buy.setdefault(mm.group(1), mm.group(3) == "!0")
        nb = re.search(r'nbPages:(\d+)', html)
        hits = re.search(r'nbHits:(\d+)', html)
        return items, buy, int(nb.group(1)) if nb else 1, int(hits.group(1)) if hits else None

    def to_item(self, el, buy, cat):
        it = el.get("item") or {}
        off = it.get("offers") or {}
        sku = it.get("sku")
        price = off.get("price")
        if not sku or price in (None, ""):
            return None
        price = float(price)
        strike = ((off.get("priceSpecification") or {}).get("price"))
        lp = float(strike) if strike and float(strike) > price else price
        disc = round((1 - price / lp) * 100) if lp > price else 0
        img = (it.get("image") or [None])[0]
        if img:
            img = img.replace("width=1400", "width=400")
        return {"store": STORE, "pid": sku, "title": it.get("name"), "image": img, "url": it.get("url"),
                "price": price, "list_price": lp, "discount_pct": disc, "in_stock": buy.get(sku, True),
                "category": site_category(cat), "src_category": cat,
                "_brand": ((it.get("brand") or {}).get("name"))}

    # ---------- قاعدة البيانات ----------
    async def rpc(self, fn, payload):
        for i in range(4):
            try:
                r = await self.db.post(f"{SUPABASE_URL}/rest/v1/rpc/{fn}", json={"token": INGEST_TOKEN, **payload})
                if r.status_code in (200, 204):
                    try:
                        return r.json() if r.content else True
                    except Exception:
                        return True
                log("DB", fn, r.status_code, r.text[:150])
            except Exception as e:
                log("DB exception", fn, str(e)[:120])
            await asyncio.sleep(3 * 2 ** i)
        self.st["errors"] += 1
        return None

    async def load_known(self):
        """الأسعار الحالية من قاعدة البيانات — عشان نعرف الجديد والمتغير."""
        off = 0
        while True:
            r = await self.db.get(f"{SUPABASE_URL}/rest/v1/products", params={
                "select": "pid,price,list_price,in_stock", "store": f"eq.{STORE}", "order": "pid", "limit": "1000", "offset": str(off)})
            rows = r.json() if r.status_code == 200 else []
            for x in rows:
                self.known[x["pid"]] = (float(x["price"] or 0), float(x["list_price"] or 0), x["in_stock"])
            if len(rows) < 1000:
                break
            off += 1000
        r = await self.db.get(f"{SUPABASE_URL}/rest/v1/product_details", params={"select": "id", "store": f"eq.{STORE}", "limit": "100000"})
        if r.status_code == 200:
            self.details_done = {x["id"] for x in r.json()}
        log("known products:", len(self.known), "with details:", len(self.details_done))

    async def save(self, items):
        # منع التكرار: نفس المنتج ممكن يظهر في أكتر من صفحة
        uniq = {}
        for it in items:
            uniq[it["pid"]] = it
        items = list(uniq.values())
        out, details = [], []
        for it in items:
            brand = it.pop("_brand", None)
            old = self.known.get(it["pid"])
            if old is None:
                self.st["new_products"] += 1
            else:
                op, olp, ost = old
                if abs(op - it["price"]) > 0.001: self.st["price_changes"] += 1
                if olp > op and not (it["list_price"] > it["price"]): self.st["discount_ended"] += 1
                if ost and not it["in_stock"]: self.st["out_of_stock"] += 1
                if (ost is False) and it["in_stock"]: self.st["back_in_stock"] += 1
            self.known[it["pid"]] = (it["price"], it["list_price"], it["in_stock"])
            out.append(it)
            did = f"{STORE}:{it['pid']}"
            if did not in self.details_done:
                details.append({"id": did, "store": STORE, "brand": brand, "source_category": it["src_category"], "region": REGION})
                self.details_done.add(did)
                self.need_details.append((did, it["url"]))
        for i in range(0, len(out), 100):
            res = await self.rpc("ingest_products", {"items": out[i:i + 100]})
            if res:
                self.st["inserted"] += res.get("inserted", 0); self.st["changed"] += res.get("changed", 0)
        if details:
            await self.rpc("ingest_details", {"items": details})
        self.st["items_seen"] += len(out)

    # ---------- الطابور ----------
    def push(self, due, cat, page):
        self.seq += 1
        heapq.heappush(self.q, (due, self.seq, cat, page))

    async def discover(self):
        html = await self.get(f"{BASE}/categories/")
        cats = sorted(set(re.findall(r'href="/egypt-ar/category/([A-Za-z0-9_]+)/', html or "")))
        if not cats:
            raise RuntimeError("مالقيتش أقسام في صفحة الأقسام")
        self.st["categories"] = len(cats)
        now = time.time()
        for c in cats:
            if (c, 1) not in self.pages:
                self.pages[(c, 1)] = {"prio": True, "fails": 0}
                self.push(now, c, 1)
        log("categories:", len(cats))

    async def do_page(self, cat, page):
        url = f"{BASE}/category/{cat}/" + (f"?page={page}" if page > 1 else "")
        html = await self.get(url)
        meta = self.pages.setdefault((cat, page), {"prio": False, "fails": 0})
        now = time.time()
        if html is None:
            meta["fails"] += 1
            self.push(now + min(3600, 60 * 2 ** meta["fails"]), cat, page)   # إعادة محاولة بتأخير متزايد
            return
        meta["fails"] = 0
        items, buy, nb_pages, hits = self.parse_listing(html)
        its = [x for x in (self.to_item(e, buy, cat) for e in items) if x]
        if page == 1:
            meta["hits"] = hits
            for p in range(2, nb_pages + 1):                                   # صفحات جديدة ظهرت
                if (cat, p) not in self.pages:
                    self.pages[(cat, p)] = {"prio": True, "fails": 0}
                    self.push(now, cat, p)
        if its:
            await self.save(its)
        # أولوية = الصفحة فيها خصم أو منتج غير متوفر (عشان نلحق انتهاء الخصم ورجوع التوفر بسرعة)
        meta["prio"] = any(x["discount_pct"] > 0 for x in its) or any(not x["in_stock"] for x in its)
        last = self.prio_done_at.get((cat, page))
        if meta["prio"] and last:
            gap = now - last
            c = self.st["prio_cycle_secs"]
            self.st["prio_cycle_secs"] = round(gap if c is None else c * 0.9 + gap * 0.1)
        self.prio_done_at[(cat, page)] = now
        self.full_seen.add((cat, page))
        if len(self.full_seen) >= len(self.pages):
            self.st["full_cycle_secs"] = round(now - self.full_round_start)
            self.full_round_start = now; self.full_seen = set()
        if its or page == 1:
            self.push(now + (PRIORITY_EVERY if meta["prio"] else FULL_EVERY), cat, page)

    async def details_worker(self):
        """الوصف والحجم وعدد القطع من صفحة المنتج — للمنتجات الجديدة بس، طلب كل ٤ ثواني تقريباً."""
        while True:
            if not self.need_details:
                await asyncio.sleep(10); continue
            did, url = self.need_details.pop(0)
            await asyncio.sleep(3)
            html = await self.get(url, tries=2)
            if not html:
                continue
            for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
                try:
                    d = json.loads(m.group(1))
                except Exception:
                    continue
                if d.get("@type") != "Product":
                    continue
                props = {p.get("name"): p.get("value") for p in d.get("additionalProperty") or []}
                await self.rpc("ingest_details", {"items": [{
                    "id": did, "store": STORE, "brand": (d.get("brand") or {}).get("name"),
                    "barcode": d.get("gtin13") or d.get("gtin") or d.get("gtin12") or d.get("mpn"),
                    "description": d.get("description"), "size": d.get("size"),
                    "pack_count": props.get("Item Pack Quantity") or props.get("عدد العبوات"), "region": REGION}]})
                break

    async def status_loop(self):
        while True:
            await asyncio.sleep(60)
            prio = sum(1 for v in self.pages.values() if v.get("prio"))
            st = {**self.st, "pages": len(self.pages), "priority_pages": prio, "queue": len(self.q),
                  "details_pending": len(self.need_details), "region": REGION, "rate_sec": RATE, "slowdown": round(self.lim.slow, 2),
                  "target_priority_secs": PRIORITY_EVERY, "_at": time.time()}
            await self.rpc("collector_set_state", {"k": "status_noon_minutes", "v": st})
            log("status:", json.dumps({k: st[k] for k in ("pages", "priority_pages", "requests", "items_seen", "new_products",
                                                          "price_changes", "prio_cycle_secs", "full_cycle_secs", "errors")}, ensure_ascii=False))

    async def run(self):
        await self.load_known()
        await self.discover()
        asyncio.create_task(self.details_worker())
        asyncio.create_task(self.status_loop())
        t_end = time.time() + RUN_SECONDS if RUN_SECONDS else None
        last_discover = time.time()
        while not t_end or time.time() < t_end:
            if time.time() - last_discover > 6 * 3600:
                last_discover = time.time(); await self.discover()
            if not self.q:
                await asyncio.sleep(5); continue
            due, _, cat, page = self.q[0]
            wait = due - time.time()
            if wait > 0:
                await asyncio.sleep(min(wait, 5)); continue
            heapq.heappop(self.q)
            try:
                await self.do_page(cat, page)
            except Exception as e:
                self.st["errors"] += 1
                log("page error", cat, page, repr(e)[:150])
                self.push(time.time() + 120, cat, page)
        log("run window finished")


if __name__ == "__main__":
    asyncio.run(Collector().run())
