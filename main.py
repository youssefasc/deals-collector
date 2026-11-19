"""جامع الأسعار — خدمة مستقلة عن البوت.

بيقرأ عروض أمازون مصر من مصدر البيانات الداخلي لصفحات العروض (d2b products/search)،
اللي بيرجّع ٣٠ منتج في الطلب الواحد بالاسم والسعر والسعر قبل الخصم ونوع المنتج،
ويسجّلها في Supabase. قاعدة البيانات نفسها بتحسب نزول السعر وأقل سعر و"قوة اللقطة".

طبقتين:
  - الطبقة السريعة: كل HOT_SECONDS ثانية بيقرأ أول صفحات كل مصدر (اللي فيها الجديد).
  - المسح الكامل: بيلف على كل صفحات كل مصدر بالراحة (طلب كل SWEEP_DELAY ثانية).
"""
import asyncio
import json
import os
import random
import re
import time
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit, unquote

import httpx
from playwright.async_api import async_playwright

from categories import categorize

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://unwzvhdwxmlmknvgvrhp.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "")
AMAZON_TAG = os.environ.get("AMAZON_TAG", "3rodmattfwt4-21")
HOT_SECONDS = float(os.environ.get("HOT_SECONDS", "10"))
SWEEP_DELAY = float(os.environ.get("SWEEP_DELAY", "0.6"))
SWEEP_WORKERS = int(os.environ.get("SWEEP_WORKERS", "3"))
HOT_PAGES = int(os.environ.get("HOT_PAGES", "2"))

# صفحات بنلقط منها رابط مصدر البيانات (كل صفحة عروض ليها مصدر بفلاتر مختلفة)
SOURCE_PAGES = [p for p in os.environ.get("SOURCE_PAGES", "https://www.amazon.eg/deals,https://www.amazon.eg/whitefriday").split(",") if p.strip()]

# أقسام أمازون مصر الرئيسية (أرقامها من فلتر الأقسام في صفحات العروض)
DEPARTMENTS = [
    ("18018103031", "electronics"), ("18020638031", "supermarket"), ("18021876031", "health_household"),
    ("18017989031", "beauty"), ("18021934031", "home_kitchen"), ("18018166031", "fashion"),
    ("18022561031", "video_games"), ("18017932031", "baby"), ("18022504031", "toys"),
    ("18022447031", "sports"), ("18021991031", "tools_home_improvement"), ("18022276031", "office"),
    ("18017875031", "automotive"), ("18022333031", "pets"), ("18019024031", "garden"),
    ("18018046031", "books"), ("18017808031", "arts_crafts"), ("18022048031", "industrial"),
    ("18022219031", "musical_instruments"), ("18029450031", "other"),
]

# صفحات بحث أمازون بفلتر "كل الخصومات" — فيها آلاف عروض السوبرماركت والمنظفات اللي مش موجودة في صفحة العروض
SEARCH_SOURCES = [s.split(":") for s in os.environ.get(
    "SEARCH_SOURCES", "grocery:grocery,hpc:health,baby:kids,beauty:beauty").split(",") if ":" in s]
# أقسام بنجمع منها **كل** المنتجات (مش المخفّضة بس) — عشان نلقط أي نزول سعر
# الصيغة: رقم القسم في أمازون : التصنيف (smart = بنحدد موبايل/إكسسوار… من اسم المنتج)
NODE_SOURCES = [s.split(":") for s in os.environ.get("NODE_SOURCES",
    "18020637031:grocery,21832868031:phones,21832872031:computers,21832881031:tvs_node,"
    "21832869031:audio,21832878031:smartwatches").split(",") if ":" in s]
NODE_DELAY = float(os.environ.get("NODE_DELAY", "2.0"))
AMAZON_NOW_SMID = os.environ.get("AMAZON_NOW_SMID", "A31TYDXOWA7X1E")
RESALE_NODE = os.environ.get("RESALE_NODE", "27972173031")
TOP_PAGES = int(os.environ.get("TOP_PAGES", "4"))      # أول كام صفحة (الأكثر مبيعاً) بتتفحص كتير
TOP_DELAY = float(os.environ.get("TOP_DELAY", "1.5"))
SEARCH_DELAY = float(os.environ.get("SEARCH_DELAY", "1.0"))
SEARCH_MAX_PAGES = int(os.environ.get("SEARCH_MAX_PAGES", "400"))

PRICE_BANDS = [(1, 100), (100, 250), (250, 500), (500, 1000), (1000, 2500), (2500, 5000),
               (5000, 15000), (15000, 200000)]

stats = {"requests": 0, "items": 0, "inserted": 0, "changed": 0, "errors": 0, "since": time.time()}


CFG = {}   # إعدادات بتتغير من لوحة التحكم (بتتقري كل دقيقة)


def cfg(k, default):
    v = CFG.get(k)
    return default if v is None else v


_STORE_OF = {"dream2000": "dream2000", "dubaiphone": "dubaiphone", "2b": "2b", "btech": "btech", "carrefour": "carrefour", "talabat": "talabat", "noon": "noon", "jumia": "jumia", "coupons": "amazon", "deals": "amazon", "hot": "amazon", "search": "amazon", "nodes": "amazon", "top": "amazon",
             "now": "amazon_now", "resale": "amazon_resale"}


async def gate(name: str):
    """بيوقف اللفة لو اتقفلت من لوحة التحكم (أو لو المتجر بتاعها اتقفل، أو الجامع كله واقف)."""
    while CFG.get("paused") or CFG.get("off_" + name) or CFG.get("off_store_" + _STORE_OF.get(name, "")):
        await asyncio.sleep(10)


async def config_loop(db):
    global CFG
    while True:
        try:
            r = await db.client.post(f"{SUPABASE_URL}/rest/v1/rpc/collector_get_config", json={"token": INGEST_TOKEN})
            if r.status_code == 200 and isinstance(r.json(), dict):
                if r.json() != CFG:
                    log("config:", r.json())
                CFG = r.json()
        except Exception:
            pass
        await asyncio.sleep(30)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def parse_product(pr: dict):
    try:
        asin = (pr.get("asin") or "").upper()
        if not asin:
            return None
        price, orig = None, None
        for k, v in (pr.get("price") or {}).items():
            if not isinstance(v, dict):
                continue
            n = _num(v.get("price"))
            if n is None:
                continue
            if k == "priceToPay":
                price = n
            elif v.get("strikethrough") or k in ("basisPrice", "listPrice", "wasPrice", "strikePrice"):
                orig = max(orig or 0, n)
        if not price:
            return None
        pct = round((1 - price / orig) * 100) if orig and orig > price else None
        img = None
        im = pr.get("image") or {}
        for key in ("hiRes", "lowRes"):
            b = (im.get(key) or {})
            if b.get("baseUrl"):
                img = f"{b['baseUrl']}.{b.get('extension') or 'jpg'}"
                break
        cat = pr.get("productCategory") or {}
        gl, pt = cat.get("symbol") or "", cat.get("productType") or ""
        state = ((pr.get("dealDetails") or {}).get("state") or "").upper()
        return {
            "store": "amazon", "pid": asin, "title": (pr.get("title") or "")[:300], "image": img,
            "url": f"https://www.amazon.eg/dp/{asin}?tag={AMAZON_TAG}",
            "price": price, "list_price": orig, "discount_pct": pct,
            "category": categorize(gl, pt), "src_category": f"{gl}|{pt}"[:80],
            "in_stock": state not in ("SOLD_OUT", "EXPIRED", "ENDED"),
        }
    except Exception:
        return None


class DB:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30, headers={
            "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"})

    _sem = None

    async def ingest(self, items: list):
        if not items:
            return
        # مش أكتر من كتابتين في نفس الوقت — عشان قاعدة البيانات متتخنقش والموقع يفضل سريع
        if DB._sem is None:
            DB._sem = asyncio.Semaphore(int(os.environ.get("DB_CONCURRENCY", "2")))
        async with DB._sem:
            await self._ingest(items)

    async def _ingest(self, items: list):
        items = sorted(items, key=lambda x: (x.get("store", ""), x.get("pid", "")))  # ترتيب ثابت يمنع الـ deadlock
        # الكوبونات اللي ظاهرة على المنتجات ("وفّر 10% بالكوبون") بتتسجل في جدول الكوبونات
        coupons = []
        for it in items:
            c = it.pop("_coupon", None)
            if c and not CFG.get("off_coupons"):
                coupons.append({"id": f"{it['store']}:{it['pid']}", "store": it["store"], "title": it.get("title"),
                                "discount": c, "url": it.get("url"), "image": it.get("image"),
                                "product_id": f"{it['store']}:{it['pid']}"})
        if coupons:
            try:
                await self.client.post(f"{SUPABASE_URL}/rest/v1/rpc/ingest_coupons",
                                       json={"token": INGEST_TOKEN, "items": coupons})
                stats["coupons"] = stats.get("coupons", 0) + len(coupons)
            except Exception:
                pass
        try:
            r = await self.client.post(f"{SUPABASE_URL}/rest/v1/rpc/ingest_products",
                                       json={"token": INGEST_TOKEN, "items": items})
            if r.status_code >= 300:
                stats["errors"] += 1
                log("DB error", r.status_code, r.text[:200])
                return
            res = r.json()
            stats["inserted"] += res.get("inserted", 0)
            stats["changed"] += res.get("changed", 0)
        except Exception as e:
            stats["errors"] += 1
            log("DB exception", str(e)[:150])

    async def set_state(self, k: str, v):
        try:
            await self.client.post(f"{SUPABASE_URL}/rest/v1/rpc/collector_set_state",
                                   json={"token": INGEST_TOKEN, "k": k, "v": v})
        except Exception:
            pass


class Amazon:
    def __init__(self, page):
        self.page = page
        self.feeds = {}      # name -> (parts, query dict)
        self.backoff_until = 0

    async def discover(self):
        """بنفتح كل صفحة عروض ونلقط أول طلب لمصدر البيانات بتاعها."""
        for src in SOURCE_PAGES:
            urls = []

            def on_resp(r):
                if "/d2b/api/v1/products/search" in r.url:
                    urls.append(r.url)
            self.page.on("response", on_resp)
            try:
                await self.page.goto(src, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(4)
                for _ in range(10):
                    if urls:
                        break
                    await self.page.mouse.wheel(0, 2500)
                    await asyncio.sleep(1)
            except Exception as e:
                log("discover error", src, str(e)[:120])
            finally:
                self.page.remove_listener("response", on_resp)
            if urls:
                parts = urlsplit(urls[0])
                q = dict(parse_qsl(parts.query, keep_blank_values=True))
                self.feeds[src] = (parts, q)
                # المصدر بيرجّع ٥٠٠ منتج بس في المرة — فبنعمل نسخة منه لكل قسم لوحده
                try:
                    flt = json.loads(q.get("filters") or "{}")
                    if "includedDepartments" in flt:
                        for dep_id, dep_name in DEPARTMENTS:
                            f2 = dict(flt)
                            f2["includedDepartments"] = [dep_id]
                            q2 = dict(q)
                            q2["filters"] = json.dumps(f2, separators=(",", ":"))
                            self.feeds[f"{src}#{dep_name}"] = (parts, q2)
                        log(f"   + {len(DEPARTMENTS)} department feeds")
                        for days in (30, 60, 90):
                            f4 = dict(flt)
                            f4["includedTags"] = [f"PIMA_PRICE_MIN_GV_{days}D"]
                            q4 = dict(q)
                            q4["filters"] = json.dumps(f4, separators=(",", ":"))
                            self.feeds[f"{src}#lowest_{days}d"] = (parts, q4)
                        # كل قسم بيقف عند ~٥٠٠ — نقسّمه كمان بنطاقات سعر (لو المصدر بيقبل فلتر السعر)
                        key = "price"
                        if key:
                            n = 0
                            for dep_id, dep_name in DEPARTMENTS:
                                for lo, hi in PRICE_BANDS:
                                    f3 = dict(flt)
                                    f3["includedDepartments"] = [dep_id]
                                    q3 = dict(q)
                                    q3["filters"] = json.dumps(f3, separators=(",", ":"))
                                    # فلتر السعر بيتبعت كبراميتر لوحده (ده اللي الصفحة نفسها بتعمله)
                                    q3["rangeRefinementFilters"] = json.dumps(
                                        [{"id": "price", "min": lo, "max": hi}], separators=(",", ":"))
                                    self.feeds[f"{src}#{dep_name}@{lo}-{hi}"] = (parts, q3)
                                    n += 1
                            # النسخ المقسّمة بتغطي القسم كله، فمش محتاجين نسخة القسم الكاملة
                            for dep_id, dep_name in DEPARTMENTS:
                                self.feeds.pop(f"{src}#{dep_name}", None)
                            log(f"   + {n} department×price feeds")
                except Exception as e:
                    log("department feeds error", str(e)[:100])
                log("feed found:", src)
                for k, v in q.items():
                    log("   ", k, "=", unquote(v)[:300])
            else:
                log("no data feed found on", src, "| title:", (await self.page.title())[:60])

    async def heal(self, err: str):
        """لو صفحة أمازون وقعت (Target crashed / closed) بنفتح صفحة جديدة بدل ما كل الطلبات تفشل للأبد."""
        if not re.search(r"crash|closed|Target", err or "", re.I):
            return
        if getattr(self, "_healing", False):
            await asyncio.sleep(5)
            return
        self._healing = True
        try:
            log("amazon page crashed — opening a new page")
            ctx = self.page.context
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = await ctx.new_page()
            await self.page.goto("https://www.amazon.eg/", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(2)
        except Exception as e:
            log("heal failed", str(e)[:100])
        finally:
            self._healing = False

    async def _eval(self, url):
        try:
            return await self._eval_raw(url)
        except Exception as e:
            await self.heal(str(e))
            raise

    async def _eval_raw(self, url):
        return await self.page.evaluate("""async (u) => {
            try { const r = await fetch(u, {credentials: 'include', headers: {'accept': 'application/json'}});
                  if (!r.ok) return {err: r.status}; return await r.json(); }
            catch (e) { return {err: String(e)}; } }""", url)

    async def fetch(self, feed: str, start: int):
        parts, q = self.feeds[feed]
        q = dict(q)
        q["startIndex"] = str(start)
        q["pageSize"] = q.get("pageSize") or "30"
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), ""))
        stats["requests"] += 1
        try:
            data = await self._eval(url)
        except Exception as e:
            stats["errors"] += 1
            log("fetch error", str(e)[:100])
            await asyncio.sleep(3)
            return None
        if isinstance(data, dict) and data.get("err"):
            stats["errors"] += 1
            if data["err"] in (403, 429, 503):
                self.backoff_until = time.time() + 120
                log("blocked/rate-limited:", data["err"], "— backing off 2 min")
            return None
        prods = (data or {}).get("products") or []
        out = [p for p in (parse_product(x) for x in prods) if p]
        stats["items"] += len(out)
        return out


SEARCH_JS = """async (u) => {
  try {
    const r = await fetch(u, {credentials: 'include'});
    if (!r.ok) return {err: r.status};
    const d = new DOMParser().parseFromString(await r.text(), 'text/html');
    const num = s => { if (!s) return null; const v = parseFloat(s.replace(/[^0-9.,]/g, '').replace(/,/g, '')); return isNaN(v) ? null : v; };
    const items = [...d.querySelectorAll('[data-component-type="s-search-result"][data-asin]')]
      .filter(e => e.dataset.asin && !e.querySelector('.puis-sponsored-label-text'))
      .map(e => ({
        asin: e.dataset.asin,
        title: (e.querySelector('h2')?.getAttribute('aria-label') || e.querySelector('h2')?.textContent || '').trim(),
        price: num(e.querySelector('.a-price:not(.a-text-price) .a-offscreen')?.textContent),
        list: num(e.querySelector('.a-price.a-text-price .a-offscreen')?.textContent),
        img: e.querySelector('img.s-image')?.getAttribute('src') || null,
        oos: /غير متوفر|Currently unavailable/i.test(e.textContent),
        txt: (e.innerText || e.textContent || '').replace(/\\s+/g, ' ').slice(0, 500)
      }));
    const blocked = /captcha|عذر/i.test(d.title || '') ;
    return {items, blocked, hasNext: !!d.querySelector('.s-pagination-next:not(.s-pagination-disabled)')};
  } catch (e) { return {err: String(e)}; }
}"""


_AR = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def used_price(txt: str):
    """سعر المستعمل من نص الكارت: "EGP 100.04(1 used offer)" أو "100.04 جنيه (1 عرض مستعمل)"."""
    t = (txt or "").translate(_AR).replace("٬", ",").replace("٫", ".").replace("\u200f", "")
    m = (re.search(r"(?:EGP|جنيه)\s*([\d,]+(?:\.\d+)?)\s*\(?\s*\d+\+?\s*(?:used|عرض|عروض)", t, re.I)
         or re.search(r"([\d,]+(?:\.\d+)?)\s*(?:جنيه|EGP)\s*\(?\s*\d+\+?\s*(?:used|عرض|عروض)", t, re.I))
    try:
        return float(m.group(1).replace(",", "")) if m else None
    except ValueError:
        return None


_COUPON_RE = re.compile(
    r"(?:وفّ?ر|وفر|Save)\s*([\d.,]+\s*(?:%|٪|جنيه|EGP)?|EGP\s*[\d.,]+)\s*(?:مع|بال|ب)?\s*(?:كوبون|الكوبون|with coupon|coupon)", re.I)


def coupon_of(txt: str):
    t = (txt or "").translate(_AR).replace("٫", ".")
    m = _COUPON_RE.search(t)
    return m.group(1).strip() if m else None


def search_item(x: dict, cat: str, store: str = "amazon"):
    price, lst = x.get("price"), x.get("list")
    if not x.get("asin") or not price:
        return None
    pct = round((1 - price / lst) * 100) if lst and lst > price else None
    img = x.get("img")
    if img:
        img = re.sub(r"\._[^/]*_\.", "._AC_SL500_.", img)
    a = x["asin"].upper()
    url = {"amazon_now": f"https://www.amazon.eg/dp/{a}?smid={AMAZON_NOW_SMID}&tag={AMAZON_TAG}",
           "amazon_resale": f"https://www.amazon.eg/dp/{a}?aod=1&condition=used&tag={AMAZON_TAG}"}.get(
        store, f"https://www.amazon.eg/dp/{a}?tag={AMAZON_TAG}")
    return {"store": store, "pid": a, "title": (x.get("title") or "")[:300], "image": img, "url": url,
            "price": price, "list_price": lst, "discount_pct": pct,
            "category": cat, "src_category": "search", "in_stock": not x.get("oos"),
            "_coupon": coupon_of(x.get("txt"))}


_ACC = re.compile(r"جراب|كفر|غطاء|حافظة|اسكرينة|واقي|لاصقة|شاحن|كابل|كيبل|حامل|ستاند|سماعة|باور ?بانك|"
                  r"case|cover|protector|charger|cable|holder|stand|adapter|mount|strap|sleeve|bag|حقيبة|شنطة", re.I)


def classify(cat: str, title: str) -> str:
    t = title or ""
    if cat == "phones":
        if _ACC.search(t):
            return "mobile_acc"
        if re.search(r"تابلت|تاب |ايباد|آيباد|ipad|tablet|galaxy tab|\bpad\b", t, re.I):
            return "tablets"
        if re.search(r"موبايل|هاتف|جوال|تليفون|iphone|galaxy|redmi|xiaomi|poco|oppo|realme|vivo|honor|infinix|tecno|nokia|motorola|phone", t, re.I):
            return "mobiles"
        return "mobile_acc"
    if cat == "computers":
        if _ACC.search(t):
            return "computer_acc"
        if re.search(r"لابتوب|لاب توب|laptop|notebook|macbook|chromebook", t, re.I):
            return "laptops"
        if re.search(r"تابلت|ايباد|آيباد|ipad|tablet", t, re.I):
            return "tablets"
        return "computer_acc"
    if cat == "tvs_node":
        if re.search(r"تلفزيون|تليفزيون|شاشة|\btv\b|television|oled|qled", t, re.I) and not _ACC.search(t):
            return "tvs"
        return "electronics"
    return cat


async def search_loop(amz, db: "DB"):
    """كل مصدر بحث (سوبرماركت، منظفات، موبايلات…) بيتلف عليه بالتوازي مع الباقيين."""
    tasks = [search_source_loop(amz, db, a, c) for a, c in SEARCH_SOURCES]
    tasks += [search_source_loop(amz, db, n, c, node=True) for n, c in NODE_SOURCES]
    await asyncio.gather(*tasks)


async def search_source_loop(amz, db: "DB", alias: str, cat: str, node: bool = False):
    while True:
        await gate("nodes" if node else "search")
        if True:
            t0, total, page = time.time(), 0, 1
            while page <= SEARCH_MAX_PAGES:
                if time.time() < amz.backoff_until:
                    await asyncio.sleep(5)
                    continue
                url = (f"https://www.amazon.eg/s?rh=n%3A{alias}&fs=true&language=ar_AE&page={page}" if node else
                       f"https://www.amazon.eg/s?i={alias}&rh=p_n_deal_type%3A26901036031"
                       f"&language=ar_AE&page={page}")
                stats["requests"] += 1
                try:
                    res = await amz.page.evaluate(SEARCH_JS, url)
                except Exception as e:
                    stats["errors"] += 1
                    log("search error", str(e)[:100])
                    await amz.heal(str(e))
                    await asyncio.sleep(10)
                    break
                if res.get("err") or res.get("blocked"):
                    stats["errors"] += 1
                    if res.get("err") in (403, 429, 503) or res.get("blocked"):
                        amz.backoff_until = time.time() + 60
                        log("search blocked:", res.get("err") or "captcha", "— backing off 1 min")
                    break
                items = [i for i in (search_item(x, classify(cat, x.get("title"))) for x in res.get("items") or []) if i]
                stats["items"] += len(items)
                if items:
                    total += len(items)
                    await db.ingest(items)
                if not res.get("hasNext"):
                    break
                page += 1
                await asyncio.sleep((cfg("node_delay", NODE_DELAY) if node else cfg("search_delay", SEARCH_DELAY)) + random.uniform(0, 1.0))
                await gate("nodes" if node else "search")
            log(f"search done: {alias} → {total} products, {page} pages in {int(time.time() - t0)}s")
        await asyncio.sleep(20)


async def fetch_search(amz, url):
    stats["requests"] += 1
    try:
        res = await amz.page.evaluate(SEARCH_JS, url)
    except Exception as e:
        stats["errors"] += 1
        log("search error", str(e)[:100])
        await amz.heal(str(e))
        return None
    if res.get("err") or res.get("blocked"):
        stats["errors"] += 1
        if res.get("err") in (403, 429, 503) or res.get("blocked"):
            amz.backoff_until = time.time() + 60
            log("search blocked:", res.get("err") or "captcha", "— backing off 1 min")
        return None
    return res


def top_urls():
    """أول صفحات كل قسم (مرتبة بالأكثر مبيعاً) — دي المنتجات المهمة اللي لازم نلقط نزولها بسرعة."""
    out = []
    for n, c in NODE_SOURCES:
        out.append((lambda p, n=n: f"https://www.amazon.eg/s?rh=n%3A{n}&fs=true&language=ar_AE&page={p}", c, "amazon"))
    for a, c in SEARCH_SOURCES:
        out.append((lambda p, a=a: f"https://www.amazon.eg/s?i={a}&rh=p_n_deal_type%3A26901036031&language=ar_AE&page={p}", c, "amazon"))
    out.append((lambda p: f"https://www.amazon.eg/s?me={AMAZON_NOW_SMID}&fs=true&language=ar_AE&page={p}", "grocery", "amazon_now"))
    return out


async def top_loop(amz, db: "DB"):
    """بيلف على أول صفحات كل الأقسام باستمرار (كل كام دقيقة) عشان الأكثر مبيعاً يتفحص أكتر من الباقي."""
    while True:
        await gate("top")
        t0, n = time.time(), 0
        for fn, cat, store in top_urls():
            for p in range(1, int(cfg("top_pages", TOP_PAGES)) + 1):
                while time.time() < amz.backoff_until:
                    await asyncio.sleep(5)
                res = await fetch_search(amz, fn(p))
                if not res:
                    break
                items = [i for i in (search_item(x, classify(cat, x.get("title")), store) for x in res.get("items") or []) if i]
                stats["items"] += len(items)
                n += len(items)
                await db.ingest(items)
                if not res.get("hasNext"):
                    break
                await asyncio.sleep(cfg("top_delay", TOP_DELAY) + random.uniform(0, 0.5))
        log(f"top pass: {n} bestsellers checked in {int(time.time() - t0)}s")
        await asyncio.sleep(5)


async def amazon_now_loop(amz, db: "DB"):
    """أمازون ناو = منتجات البائع A31TYDXOWA7X1E (توصيل خلال دقايق)."""
    while True:
        await gate("now")
        t0, total, page = time.time(), 0, 1
        while page <= 200:
            while time.time() < amz.backoff_until:
                await asyncio.sleep(5)
            res = await fetch_search(amz, f"https://www.amazon.eg/s?me={AMAZON_NOW_SMID}&fs=true&language=ar_AE&page={page}")
            if not res:
                break
            items = [i for i in (search_item(x, "grocery", "amazon_now") for x in res.get("items") or []) if i]
            for i in items:
                i["category"] = None   # التصنيف بيتاخد من نفس المنتج في أمازون لو موجود
            total += len(items)
            stats["items"] += len(items)
            await db.ingest(items)
            if not res.get("hasNext"):
                break
            page += 1
            await asyncio.sleep(SEARCH_DELAY + random.uniform(0, 1.0))
        log(f"amazon now done: {total} products, {page} pages in {int(time.time() - t0)}s")
        await asyncio.sleep(120)


async def resale_loop(amz, db: "DB"):
    """أمازون مستعمل (ريسيل). أمازون بيقفل التقليب بعد ~13 صفحة، فبنقسم بشرائح سعر
    وأي شريحة توصل للحد بنقسمها نصين."""
    while True:
        await gate("resale")
        t0, total = time.time(), 0
        bands = [[0, 50], [50, 100], [100, 200], [200, 400], [400, 800], [800, 1600], [1600, 3200],
                 [3200, 6400], [6400, 12800], [12800, 25600], [25600, 2000000]]
        while bands:
            lo, hi = bands.pop(0)
            page, capped = 1, False
            while True:
                while time.time() < amz.backoff_until:
                    await asyncio.sleep(5)
                url = (f"https://www.amazon.eg/s?i=warehouse-deals&bbn={RESALE_NODE}&rh=n%3A{RESALE_NODE}"
                       f"%2Cp_36%3A{lo * 100}-{hi * 100}&s=price-asc-rank&language=ar_AE&page={page}")
                res = await fetch_search(amz, url)
                if not res:
                    break
                items = []
                for x in res.get("items") or []:
                    up = used_price(x.get("txt"))
                    if up:
                        x["price"], x["list"] = up, None
                    it = search_item(x, None, "amazon_resale")
                    if it:
                        items.append(it)
                total += len(items)
                stats["items"] += len(items)
                await db.ingest(items)
                if not res.get("hasNext"):
                    break
                page += 1
                if page > 13:
                    capped = True
                    break
                await asyncio.sleep(SEARCH_DELAY + random.uniform(0, 1.0))
            if capped and hi - lo > 2:
                mid = (lo + hi) // 2
                bands[:0] = [[lo, mid], [mid, hi]]
        log(f"resale done: {total} products in {int(time.time() - t0)}s")
        await asyncio.sleep(300)


def _promo_text(pr: dict):
    """نص الكوبون من بيانات أمازون: "أنت تدفع 4740 جنيه باستخدام القسيمة"."""
    for p in (pr.get("promotions") or []):
        if not isinstance(p, dict):
            continue
        frags = ((p.get("label") or {}).get("fragments") or [])
        txt = ""
        for f in frags:
            if f.get("text"):
                txt += f["text"]
            elif f.get("money"):
                try:
                    txt += f"{float(f['money']['amount']):,.0f} جنيه"
                except Exception:
                    pass
        txt += (p.get("messaging") or {}).get("text") or ""
        if txt.strip():
            return txt.strip()
    return None


async def coupon_loop(amz, db: "DB"):
    """كوبونات أمازون (القسائم): صفحة العروض بفلتر الكوبونات، لكل قسم لوحده."""
    while True:
        await gate("coupons")
        base = next((v for k, v in amz.feeds.items() if "#" not in k), None)
        if not base:
            await asyncio.sleep(60)
            continue
        parts, q0 = base
        t0, total = time.time(), 0
        for dep_id, dep_name in [(None, "all")] + DEPARTMENTS:
            flt = json.loads(q0.get("filters") or "{}")
            flt["promotionTypes"] = ["COUPON"]
            flt["includedDepartments"] = [dep_id] if dep_id else []
            q = dict(q0)
            q["filters"] = json.dumps(flt, separators=(",", ":"))
            for start in range(0, 600, 30):
                while time.time() < amz.backoff_until:
                    await asyncio.sleep(5)
                q["startIndex"], q["pageSize"] = str(start), "30"
                url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), ""))
                stats["requests"] += 1
                try:
                    data = await amz._eval(url)
                except Exception:
                    break
                prods = (data or {}).get("products") or [] if isinstance(data, dict) and not data.get("err") else []
                if not prods:
                    break
                items, coupons = [], []
                for pr in prods:
                    it = parse_product(pr)
                    if not it:
                        continue
                    items.append(it)
                    txt = _promo_text(pr)
                    coupons.append({"id": f"amazon:{it['pid']}", "store": "amazon", "title": it["title"],
                                    "discount": txt or "عليه كوبون", "url": it["url"], "image": it["image"],
                                    "product_id": f"amazon:{it['pid']}"})
                await db.ingest(items)
                if coupons:
                    try:
                        await db.client.post(f"{SUPABASE_URL}/rest/v1/rpc/ingest_coupons",
                                             json={"token": INGEST_TOKEN, "items": coupons})
                        total += len(coupons)
                    except Exception:
                        pass
                await asyncio.sleep(cfg("sweep_delay", SWEEP_DELAY) + random.uniform(0, 0.6))
        log(f"coupons done: {total} amazon coupons in {int(time.time() - t0)}s")
        await asyncio.sleep(600)


async def hot_loop(amz: Amazon, db: DB):
    while True:
        t0 = time.time()
        await gate("hot")
        if time.time() >= amz.backoff_until:
            base = [f for f in amz.feeds if "#" not in f]
            deps = [f for f in amz.feeds if "#" in f]
            hot = base + ([deps[int(t0 // HOT_SECONDS) % len(deps)]] if deps else [])
            for feed in hot:
                for i in range(HOT_PAGES):
                    items = await amz.fetch(feed, i * 30)
                    if items:
                        await db.ingest(items)
        await asyncio.sleep(max(1.0, HOT_SECONDS - (time.time() - t0)))


async def sweep_loop(amz: Amazon, db: DB):
    """أكتر من عامل بيلفوا على مصادر العروض في نفس الوقت."""
    async def worker(n):
        while True:
            feeds = [f for i, f in enumerate(sorted(amz.feeds)) if i % SWEEP_WORKERS == n]
            await sweep_feeds(amz, db, feeds)
            await asyncio.sleep(10)
    await asyncio.gather(*(worker(i) for i in range(SWEEP_WORKERS)))


async def sweep_feeds(amz: Amazon, db: DB, feeds):
    if True:
        for feed in feeds:
            await gate("deals")
            start, empty, t0, total = HOT_PAGES * 30, 0, time.time(), 0
            while start < 10000:
                if time.time() < amz.backoff_until:
                    await asyncio.sleep(5)
                    continue
                items = await amz.fetch(feed, start)
                if items is None:
                    empty += 1
                    if empty >= 3:
                        break
                elif not items:
                    break
                else:
                    empty = 0
                    total += len(items)
                    await db.ingest(items)
                start += 30
                await asyncio.sleep(cfg("sweep_delay", SWEEP_DELAY) + random.uniform(0, 0.6))
            log(f"sweep done: {feed} → {total} products in {int(time.time() - t0)}s")
            await db.set_state("last_sweep:" + feed, {"products": total, "seconds": int(time.time() - t0)})


async def stats_loop(db: DB):
    while True:
        await asyncio.sleep(60)
        mins = max(1, (time.time() - stats["since"]) / 60)
        log(f"stats: {stats['requests']} req, {stats['items']} items read, {stats['inserted']} new, "
            f"{stats['changed']} price changes, {stats['errors']} errors ({stats['requests'] / mins:.0f} req/min)")
        await db.set_state("stats", {k: v for k, v in stats.items()})


async def main():
    if not (SUPABASE_KEY and INGEST_TOKEN):
        log("missing SUPABASE_KEY / INGEST_TOKEN")
        return
    db = DB()
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        ctx = await browser.new_context(locale="ar-EG", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"))
        await ctx.route(re.compile(r".*\.(png|jpe?g|gif|webp|svg|woff2?|ttf|mp4)(\?.*)?$"), lambda r: r.abort())
        page = await ctx.new_page()
        await page.goto("https://www.amazon.eg/", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        amz = Amazon(page)
        # لو أمازون رجّع صفحة "عذرًا" نحاول تاني بعد شوية بدل ما نقف ٥ دقايق
        for attempt in range(6):
            await amz.discover()
            if amz.feeds:
                break
            log(f"no feeds (attempt {attempt + 1}) — retrying in 30s")
            await asyncio.sleep(30)
            try:
                await page.goto("https://www.amazon.eg/", wait_until="domcontentloaded", timeout=45000)
            except Exception:
                pass
        import stores_extra
        ctx2 = await browser.new_context(locale="ar-EG", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"))
        await ctx2.route(re.compile(r".*\.(png|jpe?g|gif|webp|svg|woff2?|ttf|mp4|css)(\?.*)?$"), lambda r: r.abort())
        loops = [search_loop(amz, db), top_loop(amz, db), amazon_now_loop(amz, db), resale_loop(amz, db),
                 stats_loop(db), refresh_loop(amz), config_loop(db),
                 stores_extra.noon_loop(ctx2, db, log, stats, gate, cfg),
                 stores_extra.jumia_loop(ctx2, db, log, stats, gate, cfg),
                 stores_extra.talabat_loop(ctx2, db, log, stats, gate, cfg),
                 stores_extra.twob_loop(ctx2, db, log, stats, gate, cfg),
                 stores_extra.btech_loop(ctx2, db, log, stats, gate, cfg),
                 stores_extra.carrefour_loop(ctx2, db, log, stats, gate, cfg),
                 stores_extra.dream_loop(ctx2, db, log, stats, gate, cfg),
                 stores_extra.dubai_loop(ctx2, db, log, stats, gate, cfg)]
        if amz.feeds:
            loops += [hot_loop(amz, db), sweep_loop(amz, db), coupon_loop(amz, db)]
        else:
            log("deals feed not found — running search sources only")
        await asyncio.gather(*loops)


async def refresh_loop(amz: Amazon):
    """كل نص ساعة بنجدد الجلسة (الكوكيز) عشان الطلبات تفضل شغالة."""
    while True:
        await asyncio.sleep(1800)
        try:
            await amz.page.goto("https://www.amazon.eg/", wait_until="domcontentloaded", timeout=45000)
            log("session refreshed")
        except Exception as e:
            log("refresh error", str(e)[:100])


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            log("crashed:", str(e)[:200])
        time.sleep(10)
