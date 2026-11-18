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
SWEEP_DELAY = float(os.environ.get("SWEEP_DELAY", "1.2"))
HOT_PAGES = int(os.environ.get("HOT_PAGES", "2"))

# صفحات بنلقط منها رابط مصدر البيانات (كل صفحة عروض ليها مصدر بفلاتر مختلفة)
SOURCE_PAGES = [p for p in os.environ.get("SOURCE_PAGES", "https://www.amazon.eg/deals,https://www.amazon.eg/whitefriday").split(",") if p.strip()]

stats = {"requests": 0, "items": 0, "inserted": 0, "changed": 0, "errors": 0, "since": time.time()}


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

    async def ingest(self, items: list):
        if not items:
            return
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
                log("feed found:", src)
                for k, v in q.items():
                    log("   ", k, "=", unquote(v)[:300])
            else:
                log("no data feed found on", src, "| title:", (await self.page.title())[:60])

    async def _eval(self, url):
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


async def hot_loop(amz: Amazon, db: DB):
    while True:
        t0 = time.time()
        if time.time() >= amz.backoff_until:
            for feed in list(amz.feeds):
                for i in range(HOT_PAGES):
                    items = await amz.fetch(feed, i * 30)
                    if items:
                        await db.ingest(items)
        await asyncio.sleep(max(1.0, HOT_SECONDS - (time.time() - t0)))


async def sweep_loop(amz: Amazon, db: DB):
    while True:
        for feed in list(amz.feeds):
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
                await asyncio.sleep(SWEEP_DELAY + random.uniform(0, 0.6))
            log(f"sweep done: {feed} → {total} products in {int(time.time() - t0)}s")
            await db.set_state("last_sweep:" + feed, {"products": total, "seconds": int(time.time() - t0)})
        await asyncio.sleep(30)


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
        await amz.discover()
        if not amz.feeds:
            log("no feeds — retrying in 5 min")
            await asyncio.sleep(300)
            return
        await asyncio.gather(hot_loop(amz, db), sweep_loop(amz, db), stats_loop(db),
                             refresh_loop(amz))


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
