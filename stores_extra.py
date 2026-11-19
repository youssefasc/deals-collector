"""جامع نون وجوميا.

الفكرة: بنفتح صفحات الأقسام في متصفح حقيقي، وبنقرا بيانات المنتجات اللي الموقع نفسه
بيحطها جوه الصفحة (نون: __NEXT_DATA__ / جوميا: window.__STORE__)، ولو مش لاقيينها
بنقرا الكروت من الصفحة مباشرة.
"""
import asyncio
import json
import os
import random
import re
import time

NOON_AFF = os.environ.get("NOON_AFF", "")      # لو عندك كود أفلييت لنون (هيتضاف للينك)
JUMIA_AFF = os.environ.get("JUMIA_AFF", "")    # لو عندك لينك أفلييت لجوميا

NOON_SOURCES = [s.split("|") for s in os.environ.get("NOON_SOURCES", "|".join([])).split(",") if "|" in s] or [
    ("electronics-and-mobiles/mobiles-and-accessories/mobiles-20905", "mobiles"),
    ("electronics-and-mobiles/computers-and-accessories/laptops", "laptops"),
    ("electronics-and-mobiles/computers-and-accessories/tablets", "tablets"),
    ("electronics-and-mobiles/television-and-video/televisions", "tvs"),
    ("electronics-and-mobiles/portable-audio-and-video/headphones-24056", "audio"),
    ("electronics-and-mobiles/wearable-technology", "smartwatches"),
    ("electronics-and-mobiles", "electronics"),
    ("home-and-kitchen/home-appliances-31235", "appliances"),
    ("home-and-kitchen", "home"),
    ("beauty", "beauty"),
    ("health", "health"),
    ("grocery-store", "grocery"),
    ("fashion", "fashion"),
    ("baby-products", "kids"),
    ("toys-and-games", "kids"),
    ("sports-and-outdoors", "sports"),
]

JUMIA_SOURCES = [
    ("mobile-phones", "mobiles"),
    ("laptops", "laptops"),
    ("tablets", "tablets"),
    ("televisions", "tvs"),
    ("headphones", "audio"),
    ("smart-watches", "smartwatches"),
    ("electronics", "electronics"),
    ("home-office-appliances", "appliances"),
    ("home-office", "home"),
    ("health-beauty", "beauty"),
    ("groceries", "grocery"),
    ("fashion", "fashion"),
    ("baby-products", "kids"),
    ("toys-games", "kids"),
    ("sporting-goods", "sports"),
]

# بيقرا المنتجات من أي JSON جوه الصفحة: بيدوّر على أي مصفوفة عناصرها فيها sku + اسم + سعر
NOON_JS = r"""() => {
  const out = [];
  const seen = new Set();
  const num = v => { if (v == null) return null; const n = parseFloat(String(v).replace(/[^0-9.]/g, '')); return isNaN(n) ? null : n; };
  const take = o => {
    if (!o || typeof o !== 'object') return;
    const sku = o.sku || o.sku_config || o.offer_code;
    const name = o.name || o.title;
    const price = num(o.sale_price ?? o.salePrice ?? o.price);
    if (!sku || !name || !price || seen.has(sku)) return;
    seen.add(sku);
    const was = num(o.price ?? o.was_price ?? o.wasPrice);
    const img = o.image_key ? `https://f.nooncdn.com/p/${o.image_key}.jpg` : (o.image_keys && o.image_keys[0] ? `https://f.nooncdn.com/p/${o.image_keys[0]}.jpg` : (o.image || null));
    const slug = o.url || o.slug || '';
    out.push({sku: String(sku), name: String(name), price, was: (was && was > price) ? was : null, img, slug: String(slug),
              oos: o.is_buyable === false || o.isBuyable === false});
  };
  const walk = (v, d) => {
    if (!v || d > 14) return;
    if (Array.isArray(v)) { for (const x of v) { take(x); walk(x, d + 1); } return; }
    if (typeof v === 'object') for (const k in v) walk(v[k], d + 1);
  };
  let src = 'none';
  const nd = document.getElementById('__NEXT_DATA__');
  if (nd) { try { walk(JSON.parse(nd.textContent), 0); src = 'next'; } catch (e) {} }
  if (!out.length) {
    for (const s of document.querySelectorAll('script')) {
      const t = s.textContent || '';
      if (t.length < 2000 || !/sku/.test(t)) continue;
      const m = t.match(/\{[\s\S]*\}/);
      if (!m) continue;
      try { walk(JSON.parse(m[0]), 0); src = 'script'; } catch (e) {}
    }
  }
  if (!out.length) {
    // آخر حل: الكروت نفسها
    for (const a of document.querySelectorAll('a[href*="/p/"]')) {
      const href = a.getAttribute('href') || '';
      const m = href.match(/\/([A-Z0-9]{8,})\/p\//i);
      if (!m || seen.has(m[1])) continue;
      const box = a.closest('div[class*="ProductBox"], div[class*="productContainer"], div') || a;
      const txt = box.innerText || '';
      const prices = [...txt.matchAll(/([\d,]+(?:\.\d+)?)/g)].map(x => num(x[1])).filter(x => x && x > 1);
      const name = (box.querySelector('[data-qa*="name"], [class*="name"], [title]') || {}).textContent || a.getAttribute('title') || '';
      if (!name || !prices.length) continue;
      seen.add(m[1]);
      const img = (box.querySelector('img') || {}).src || null;
      out.push({sku: m[1], name: name.trim(), price: Math.min(...prices.slice(0, 2)), was: prices.length > 1 ? Math.max(...prices.slice(0, 2)) : null,
                img, slug: href, oos: false});
      src = 'dom';
    }
  }
  return {items: out, src, title: document.title, url: location.href};
}"""

JUMIA_JS = r"""() => {
  const out = [];
  const num = v => { if (v == null) return null; const n = parseFloat(String(v).replace(/[^0-9.]/g, '')); return isNaN(n) ? null : n; };
  let src = 'none', next = false;
  const st = window.__STORE__;
  if (st && Array.isArray(st.products)) {
    src = 'store';
    for (const p of st.products) {
      const pr = p.prices || {};
      const price = num(pr.rawPrice ?? pr.price);
      if (!p.sku || !price) continue;
      const was = num(pr.rawOldPrice ?? pr.oldPrice);
      out.push({sku: p.sku, name: p.displayName || p.name, price, was: (was && was > price) ? was : null,
                img: p.image || null, slug: p.url || '', oos: p.isBuyable === false});
    }
    try { next = !!(st.pagination && st.pagination.currentPage < st.pagination.totalPages); } catch (e) {}
  }
  if (!out.length) {
    for (const art of document.querySelectorAll('article.prd')) {
      const a = art.querySelector('a.core'); if (!a) continue;
      const sku = a.getAttribute('data-gtm-id') || a.getAttribute('data-ga4-item_id') || a.getAttribute('data-id') || a.getAttribute('href');
      const name = (art.querySelector('.name') || {}).textContent;
      const price = num((art.querySelector('.prc') || {}).textContent);
      if (!sku || !name || !price) continue;
      const was = num((art.querySelector('.old') || {}).textContent);
      const im = art.querySelector('img');
      out.push({sku, name: name.trim(), price, was: (was && was > price) ? was : null,
                img: im ? (im.getAttribute('data-src') || im.src) : null, slug: a.getAttribute('href') || '', oos: false});
      src = 'dom';
    }
    next = !!document.querySelector('a[aria-label="الصفحة التالية"], a[aria-label="Next Page"]');
  }
  return {items: out, src, next, title: document.title};
}"""


def _noon_item(x, cat):
    sku = x["sku"]
    slug = (x.get("slug") or "").strip("/")
    if slug.startswith("http"):
        url = slug
    elif "/p/" in slug:
        url = "https://www.noon.com" + ("" if slug.startswith("/") else "/") + slug
    else:
        url = f"https://www.noon.com/egypt-ar/{slug + '/' if slug else ''}{sku}/p/"
    if NOON_AFF:
        url += ("&" if "?" in url else "?") + NOON_AFF
    pct = round((1 - x["price"] / x["was"]) * 100) if x.get("was") else None
    return {"store": "noon", "pid": sku, "title": x["name"][:300], "image": x.get("img"), "url": url,
            "price": x["price"], "list_price": x.get("was"), "discount_pct": pct, "category": cat,
            "src_category": "noon", "in_stock": not x.get("oos")}


def _jumia_item(x, cat):
    slug = x.get("slug") or ""
    url = slug if slug.startswith("http") else "https://www.jumia.com.eg" + ("" if slug.startswith("/") else "/") + slug
    if JUMIA_AFF:
        url = JUMIA_AFF + url
    pct = round((1 - x["price"] / x["was"]) * 100) if x.get("was") else None
    return {"store": "jumia", "pid": str(x["sku"])[:80], "title": (x.get("name") or "")[:300], "image": x.get("img"),
            "url": url, "price": x["price"], "list_price": x.get("was"), "discount_pct": pct, "category": cat,
            "src_category": "jumia", "in_stock": not x.get("oos")}


async def _new_page(ctx):
    page = await ctx.new_page()
    return page


async def noon_loop(ctx, db, log, stats, gate, cfg):
    page = await _new_page(ctx)
    first = True
    while True:
        await gate("noon")
        t0, total = time.time(), 0
        for path, cat in NOON_SOURCES:
            for pg in range(1, int(cfg("noon_pages", 50)) + 1):
                await gate("noon")
                url = f"https://www.noon.com/egypt-ar/{path}/?limit=50&page={pg}"
                stats["requests"] += 1
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    await asyncio.sleep(1.5)
                    res = await page.evaluate(NOON_JS)
                except Exception as e:
                    stats["errors"] += 1
                    log("noon error", path, pg, str(e)[:100])
                    await asyncio.sleep(10)
                    break
                items = [_noon_item(x, cat) for x in res.get("items") or []]
                if first or not items:
                    log(f"noon {path} p{pg}: {len(items)} items via {res.get('src')} | {res.get('title', '')[:50]}")
                    first = False
                if not items:
                    break
                total += len(items)
                stats["items"] += len(items)
                await db.ingest(items)
                await asyncio.sleep(cfg("noon_delay", 2.0) + random.uniform(0, 1.0))
        log(f"noon done: {total} products in {int(time.time() - t0)}s")
        await asyncio.sleep(60)


async def jumia_loop(ctx, db, log, stats, gate, cfg):
    page = await _new_page(ctx)
    first = True
    while True:
        await gate("jumia")
        t0, total = time.time(), 0
        for path, cat in JUMIA_SOURCES:
            for pg in range(1, int(cfg("jumia_pages", 50)) + 1):
                await gate("jumia")
                url = f"https://www.jumia.com.eg/ar/{path}/?page={pg}"
                stats["requests"] += 1
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    await asyncio.sleep(1.0)
                    res = await page.evaluate(JUMIA_JS)
                except Exception as e:
                    stats["errors"] += 1
                    log("jumia error", path, pg, str(e)[:100])
                    await asyncio.sleep(10)
                    break
                items = [_jumia_item(x, cat) for x in res.get("items") or []]
                if first or not items:
                    log(f"jumia {path} p{pg}: {len(items)} items via {res.get('src')} | {res.get('title', '')[:50]}")
                    first = False
                if not items:
                    break
                total += len(items)
                stats["items"] += len(items)
                await db.ingest(items)
                if not res.get("next") and res.get("src") == "store":
                    break
                await asyncio.sleep(cfg("jumia_delay", 2.0) + random.uniform(0, 1.0))
        log(f"jumia done: {total} products in {int(time.time() - t0)}s")
        await asyncio.sleep(60)


# ═══════════════════ طلبات مارت ═══════════════════
# صفحات طلبات مارت مفتوحة: كل قسم فرعي بيعرض أول 20 منتج بأسعارها جوه __NEXT_DATA__
TALABAT_BASE = "https://www.talabat.com"
TALABAT_CAT = {
    "beauty": "beauty", "personal-care": "health", "pharma-wellness": "health", "cleaning-laundry": "health",
    "household-essentials": "home", "paper-plastic": "home", "baby-corner": "kids", "electronics": "electronics",
    "stationery-games": "books_office", "pet-care": "other",
}

TALABAT_JS = r"""async (path) => {
  try {
    const r = await fetch(path, {credentials: 'include'});
    if (!r.ok) return {err: r.status};
    const h = await r.text();
    const m = h.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
    if (!m) return {err: 'nodata', title: (h.match(/<title>([^<]*)/) || [])[1]};
    const j = JSON.parse(m[1]);
    let arr = [];
    const walk = (v, d) => {
      if (!v || d > 14) return;
      if (Array.isArray(v)) { if (v[0] && v[0].dhVendorId && 'price' in v[0]) { arr = arr.concat(v); return; } v.forEach(x => walk(x, d + 1)); return; }
      if (typeof v === 'object') for (const k in v) walk(v[k], d + 1);
    };
    walk(j, 0);
    const links = [...new Set([...h.matchAll(/href="(\/egypt\/talabat-mart\/[a-z0-9-]+(?:\/[a-z0-9-]+)?)"/g)].map(x => x[1]))]
      .filter(l => !/\/product\/|\/categories$/.test(l));
    return {items: arr.map(p => ({sku: p.sku, title: p.title, slug: p.slug, price: p.price, was: p.originalPrice,
                                  img: p.image, oos: p.inStock === false})), links};
  } catch (e) { return {err: String(e)}; }
}"""


def _talabat_item(x, cat):
    price, was = x.get("price"), x.get("was")
    if not x.get("sku") or not price:
        return None
    was = was if was and was > price else None
    pct = round((1 - price / was) * 100) if was else None
    return {"store": "talabat", "pid": str(x["sku"]), "title": (x.get("title") or "")[:300], "image": x.get("img"),
            "url": f"{TALABAT_BASE}/egypt/talabat-mart/product/{x.get('slug') or 'p'}/s/{x['sku']}",
            "price": price, "list_price": was, "discount_pct": pct, "category": cat,
            "src_category": "talabat", "in_stock": not x.get("oos")}


TALABAT_VENDOR = os.environ.get("TALABAT_VENDOR", "/egypt/grocery/619848/maadi-old-el-nahda-street")
TALABAT_AID = os.environ.get("TALABAT_AID", "9838")   # منطقة التوصيل (المعادي) — بتفتح كل منتجات طلبات مارت بالصفحات


async def _tal_get(ctx, path):
    """صفحة من طلبات مارت بطلب HTTP عادي — وبنقرا بيانات المنتجات من __NEXT_DATA__."""
    try:
        r = await ctx.request.get(TALABAT_BASE + path, timeout=40000)
        if r.status != 200:
            return {"err": r.status}
        h = await r.text()
    except Exception as e:
        return {"err": str(e)[:80]}
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    if not m:
        return {"err": "nodata"}
    try:
        j = json.loads(m.group(1))
    except Exception:
        return {"err": "badjson"}
    arr = []
    def walk(v, d):
        if not v or d > 14:
            return
        if isinstance(v, list):
            if v and isinstance(v[0], dict) and v[0].get("dhVendorId") and "price" in v[0]:
                arr.extend(v); return
            for x in v: walk(x, d + 1)
        elif isinstance(v, dict):
            for x in v.values(): walk(x, d + 1)
    walk(j, 0)
    vend = re.escape(TALABAT_VENDOR)
    links = sorted(set(re.findall(r'href="(' + vend + r'/[a-z0-9-]+/[a-z0-9-]+)', h)))
    return {"items": [{"sku": p.get("sku"), "title": p.get("title"), "slug": p.get("slug"), "price": p.get("price"),
                       "was": p.get("originalPrice"), "img": p.get("image"), "oos": p.get("inStock") is False} for p in arr],
            "links": links}


async def talabat_loop(ctx, db, log, stats, gate, cfg):
    page = await _new_page(ctx)
    try:
        await page.goto(f"{TALABAT_BASE}{TALABAT_VENDOR}?aid={TALABAT_AID}", wait_until="domcontentloaded", timeout=40000)
        log("talabat store:", (await page.title())[:70])
    except Exception as e:
        log("talabat home error", str(e)[:100])
    vparts = len(TALABAT_VENDOR.strip("/").split("/"))
    while True:
        await gate("talabat")
        t0, total = time.time(), 0
        res = await _tal_get(ctx, f"{TALABAT_VENDOR}?aid={TALABAT_AID}")
        norm = lambda l: l.split("?")[0]
        queue = [norm(l) for l in (res.get("links") or []) if len(norm(l).strip("/").split("/")) == vparts + 2]
        if not queue:
            # طلبات رافض (حماية) — منكررش المحاولة كتير: نستنى ساعتين ونجرب تاني بهدوء
            # Exponential backoff: ٣٠ د ← ساعة ← ٢ ← ٤ ← ٨ ← ١٢ ساعة (أقصى حد) — من غير ما نضغط على الموقع
            _tb = min(43200, max(1800, (globals().get("_TAL_BACK") or 900) * 2)); globals()["_TAL_BACK"] = _tb
            log("talabat error blocked", res.get("err"), f"— next try in {_tb // 60} min")
            await asyncio.sleep(_tb)
            continue
        globals()["_TAL_BACK"] = 0
        seen_pages = set()
        while queue:
            sub = queue.pop(0)
            if sub in seen_pages:
                continue
            seen_pages.add(sub)
            top = sub.strip("/").split("/")[vparts]
            cat = TALABAT_CAT.get(top, "grocery")
            seen_skus = set()
            for pg in range(1, 60):
                await gate("talabat")
                stats["requests"] += 1
                r = await _tal_get(ctx, f"{sub}?aid={TALABAT_AID}&page={pg}")
                if r.get("err"):
                    stats["errors"] += 1
                    log("talabat error", sub, pg, r.get("err"))
                    if r.get("err") in (403, 429):
                        await asyncio.sleep(600)   # رفض — نهدى ١٠ دقايق قبل القسم اللي بعده
                    else:
                        await asyncio.sleep(5)
                    break
                if pg == 1:
                    for l in (r.get("links") or []):
                        l = norm(l)
                        if len(l.strip("/").split("/")) == vparts + 2 and l not in seen_pages:
                            queue.append(l)
                items = [i for i in (_talabat_item(x, cat) for x in r.get("items") or []) if i and i["pid"] not in seen_skus]
                if not items:
                    break
                seen_skus.update(i["pid"] for i in items)
                total += len(items)
                stats["items"] += len(items)
                await db.ingest(items)
                await asyncio.sleep(cfg("talabat_delay", 1.5) + random.uniform(0, 1.0))
        log(f"talabat done: {total} products from {len(seen_pages)} categories in {int(time.time() - t0)}s")
        await asyncio.sleep(300)


# ═══════════════════ 2B (Magento — واجهة GraphQL العامة بتاعة الموقع) ═══════════════════
TWOB_Q = """query($p:Int!,$n:Int!){products(filter:{price:{from:"1"}},pageSize:$n,currentPage:$p){total_count
 items{sku name url_key small_image{url} stock_status
  price_range{minimum_price{regular_price{value} final_price{value}}} categories{url_path}}}}"""


def _cat_from_path(path: str) -> str:
    p = (path or "").lower()
    for k, c in [("tablet", "tablets"), ("mobile", "mobiles"), ("laptop", "laptops"), ("notebook", "laptops"),
                 ("monitor", "computer_acc"), ("screen", "tvs"), ("tv", "tvs"), ("watch", "smartwatches"),
                 ("headphone", "audio"), ("earbud", "audio"), ("speaker", "audio"), ("audio", "audio"),
                 ("gaming", "gaming"), ("playstation", "gaming"), ("console", "gaming"), ("accessor", "mobile_acc"),
                 ("computer", "computer_acc"), ("printer", "computer_acc"), ("appliance", "appliances"),
                 ("kitchen", "appliances"), ("air-condition", "appliances"), ("ac", "appliances"),
                 ("personal-care", "health"), ("beauty", "beauty")]:
        if k in p:
            return c
    return "electronics"


async def _polite(evaluate, log, name, pg):
    """لو المتجر قال "استنى" (403/429) — بنستنى ٢ ← ٥ ← ١٠ دقايق ونعيد نفس الصفحة، من غير ما نضغط عليه."""
    for wait in (0, 120, 300, 600):
        if wait:
            log(f"{name}: rate-limited on page {pg} — waiting {wait // 60} min then retrying same page")
            await asyncio.sleep(wait)
        res = await evaluate()
        if not (isinstance(res, dict) and res.get("err") in (403, 429)):
            return res
    return res


async def twob_loop(ctx, db, log, stats, gate, cfg):
    """2B بيسمح بطلب واحد وبعدين بيرفض لو الطلبات قريبة من بعض — فبنبعت صفحة كبيرة واحدة كل فترة،
    ونحفظ آخر صفحة وصلنالها في القاعدة (Resume) عشان نكمل منها حتى بعد إعادة التشغيل."""
    page = await _new_page(ctx)
    js = """async ([q, p, n]) => { try { const r = await fetch('/graphql', {method: 'POST',
        headers: {'Content-Type': 'application/json', Store: 'ar'}, body: JSON.stringify({query: q, variables: {p, n}})});
        if (!r.ok) return {err: r.status}; return await r.json(); } catch (e) { return {err: String(e)}; } }"""
    st = {}
    try:
        st = (await db.get_state("twob_progress")) or {}
    except Exception:
        st = {}
    pg, size, back = int(st.get("page") or 1), int(st.get("size") or 300), 0
    while True:
        await gate("2b")
        try:
            await page.goto("https://2b.com.eg/ar/", wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            log("2b home error", str(e)[:100])
        stats["requests"] += 1
        res = await page.evaluate(js, [TWOB_Q, pg, size])
        data = ((res or {}).get("data") or {}).get("products") or {}
        if res.get("err") or not data:
            stats["errors"] += 1
            back = min(43200, max(21600, back * 2))   # ٦ ساعات ← ١٢ ساعة — من غير تكرار طلبات بلا جدوى
            log("2b error", pg, res.get("err") or str(res.get("errors"))[:80], f"— retry same page in {back // 60} min")
            if res.get("errors") and size > 100:
                size = max(100, size // 2)   # لو الصفحة كبيرة زيادة عن المسموح نصغّرها
            await asyncio.sleep(back)
            continue
        back = 0
        items = []
        for x in data.get("items") or []:
            pr = ((x.get("price_range") or {}).get("minimum_price") or {})
            price = (pr.get("final_price") or {}).get("value")
            was = (pr.get("regular_price") or {}).get("value")
            if not price or not x.get("sku"):
                continue
            was = was if was and was > price else None
            paths = " ".join(c.get("url_path") or "" for c in (x.get("categories") or []))
            items.append({"store": "2b", "pid": x["sku"], "title": (x.get("name") or "")[:300],
                          "image": (x.get("small_image") or {}).get("url"),
                          "url": f"https://2b.com.eg/ar/{x.get('url_key')}.html",
                          "price": price, "list_price": was,
                          "discount_pct": round((1 - price / was) * 100) if was else None,
                          "category": _cat_from_path(paths), "src_category": "2b",
                          "in_stock": x.get("stock_status") == "IN_STOCK"})
        stats["items"] += len(items)
        await db.ingest(items)
        total = data.get("total_count") or 0
        pages = max(1, -(-total // size))
        log(f"2b page {pg}/{pages}: {len(items)} products (catalog {total})")
        pg = 1 if pg >= pages else pg + 1
        await db.set_state("twob_progress", {"page": pg, "size": size, "pages": pages, "total": total, "at": time.time()})
        await asyncio.sleep(cfg("2b_gap", 600) + random.uniform(0, 60))


# ═══════════════════ B.TECH (صفحات الأقسام فيها بيانات المنتجات جاهزة) ═══════════════════
BTECH_CATS = ["mobiles-tablets", "laptop-pc", "tvs-projectors", "electronics", "large-home-appliances",
              "small-home-appliances", "air-conditioners", "wearables", "personal-care", "gaming-area"]
BTECH_MAP = {"mobiles-tablets": "mobiles", "laptop-pc": "laptops", "tvs-projectors": "tvs", "electronics": "electronics",
             "large-home-appliances": "appliances", "small-home-appliances": "appliances",
             "air-conditioners": "appliances", "wearables": "smartwatches", "personal-care": "health",
             "gaming-area": "gaming"}

BTECH_JS = r"""async (u) => { try {
  const r = await fetch(u); if (!r.ok) return {err: r.status};
  const h = (await r.text()).replace(/\\"/g, '"');
  const out = []; const re = /\{"variant_id":"([^"]+)","product_id":"[^"]*","offer_id":"([^"]*)","sku":"([^"]*)","name":"((?:[^"\\]|\\.)*)"[\s\S]*?"thumbnail_url":"([^"]*)","price":\{"final_price":([\d.]+)[\s\S]*?"base_price":([\d.]+)[\s\S]*?"is_in_stock":(true|false)/g;
  let m; while ((m = re.exec(h))) out.push({vid: m[1], offer: m[2], sku: m[3], name: m[4], img: m[5], price: +m[6], was: +m[7], stock: m[8] === 'true'});
  const tp = (h.match(/"total_pages":(\d+)/) || [])[1];
  return {items: out, pages: tp ? +tp : null};
} catch (e) { return {err: String(e)}; } }"""


async def btech_loop(ctx, db, log, stats, gate, cfg):
    page = await _new_page(ctx)
    try:
        await page.goto("https://btech.com/ar", wait_until="domcontentloaded", timeout=40000)
        log("btech home:", (await page.title())[:60])
    except Exception as e:
        log("btech home error", str(e)[:100])
    while True:
        await gate("btech")
        t0, total = time.time(), 0
        # الموقع مبيقلّبش صفحات من السيرفر — فبنلف على كل الأقسام الفرعية (من الـsitemap) وكل قسم بيدي أول ٢٠ منتج
        try:
            leaves = await page.evaluate("""async () => { const x = await (await fetch('/sitemap.xml')).text();
              const c = [...new Set(x.split('<loc>').slice(1).map(v => v.split('</loc>')[0].replace('https://btech.com', '')).filter(v => v.startsWith('/ar/c/')))];
              return c.filter(a => !c.some(b => b !== a && b.startsWith(a + '/'))); }""")
        except Exception as e:
            log("btech sitemap error", str(e)[:100]); leaves = []
        paths = leaves or [f"/ar/c/{x}" for x in BTECH_CATS]
        seen = set()
        for path in paths:
            slug = path.split("/")[3] if path.count("/") >= 3 else path
            pg, pages = 1, 1
            while pg <= 1:
                await gate("btech")
                stats["requests"] += 1
                res = await page.evaluate(BTECH_JS, path)
                if res.get("err"):
                    stats["errors"] += 1
                    log("btech error", slug, pg, res.get("err"))
                    break
                pages = res.get("pages") or pages
                items = []
                for x in res.get("items") or []:
                    if x["vid"] in seen or not x["price"]:
                        continue
                    seen.add(x["vid"])
                    was = x["was"] if x["was"] and x["was"] > x["price"] else None
                    items.append({"store": "btech", "pid": x["vid"], "title": x["name"][:300],
                                  "image": f"https://media.btech.com/catalogs/{x['img']}" if x["img"] else None,
                                  "url": f"https://btech.com/ar/p/{x['vid']}?offering_id={x['offer']}",
                                  "price": x["price"], "list_price": was,
                                  "discount_pct": round((1 - x["price"] / was) * 100) if was else None,
                                  "category": BTECH_MAP.get(slug, "electronics"), "src_category": "btech",
                                  "in_stock": x["stock"]})
                if not items:
                    break
                total += len(items)
                stats["items"] += len(items)
                await db.ingest(items)
                pg += 1
                await asyncio.sleep(cfg("btech_delay", 2.0) + random.uniform(0, 1.0))
        log(f"btech done: {total} products in {int(time.time() - t0)}s")
        await asyncio.sleep(600)


# ═══════════════════ كارفور مصر (صفحات الأقسام فيها بيانات المنتجات جاهزة) ═══════════════════
CARREFOUR_JS = r"""async (u) => { try {
  const r = await fetch(u); if (!r.ok) return {err: r.status};
  const h = (await r.text()).replace(/\\"/g, '"');
  const out = []; const seen = new Set();
  const re = /"stock":\{"stockLevelStatus":"(\w+)"\}[^{}]*?"imageUrl":"([^"]*)"[^{}]*?"productId":"(\d+)","productName":"((?:[^"\\]|\\.)*)"[^{}]*?"sellingPrice":([\d.]+),"markedPrice":([\d.]+)[^{}]*?"productUrl":"([^"]*)"/g;
  let m; while ((m = re.exec(h))) { if (seen.has(m[3])) continue; seen.add(m[3]);
    out.push({stock: m[1], img: m[2], id: m[3], name: m[4], price: +m[5], was: +m[6], url: m[7]}); }
  const pg = h.match(/"pagination":\{"pageSize":\d+,"totalPages":(\d+)/);
  const cats = [...new Set([...h.matchAll(/\/mafegy\/ar\/(?:[a-z0-9-]+\/)?c\/(FEGY\d+)/g)].map(x => x[1]))];
  return {items: out, pages: pg ? +pg[1] : null, cats};
} catch (e) { return {err: String(e)}; } }"""
CARREFOUR_SEED = ["FEGY1500000", "FEGY1660100", "FEGY1660500", "FEGY6000000", "FEGY1200000", "FEGY1610000"]


async def carrefour_loop(ctx, db, log, stats, gate, cfg):
    page = await _new_page(ctx)
    try:
        await page.goto("https://www.carrefouregypt.com/mafegy/ar/", wait_until="domcontentloaded", timeout=40000)
        log("carrefour home:", (await page.title())[:60])
    except Exception as e:
        log("carrefour home error", str(e)[:100])
    while True:
        await gate("carrefour")
        t0, total = time.time(), 0
        home = await page.evaluate(CARREFOUR_JS, "/mafegy/ar/")
        queue = list(dict.fromkeys(CARREFOUR_SEED + (home.get("cats") or [])))
        done, seen = set(), set()
        while queue and len(done) < int(cfg("carrefour_max_cats", 300)):
            code = queue.pop(0)
            if code in done:
                continue
            done.add(code)
            pg, pages = 0, 1
            while pg < min(pages or 1, 100):
                await gate("carrefour")
                stats["requests"] += 1
                res = await page.evaluate(CARREFOUR_JS, f"/mafegy/ar/c/{code}?currentPage={pg}")
                if res.get("err"):
                    stats["errors"] += 1
                    log("carrefour error", code, pg, res.get("err"))
                    break
                if pg == 0:
                    for c in res.get("cats") or []:
                        if c not in done:
                            queue.append(c)
                pages = res.get("pages") or pages
                items = []
                for x in res.get("items") or []:
                    if x["id"] in seen or not x["price"]:
                        continue
                    seen.add(x["id"])
                    was = x["was"] if x["was"] and x["was"] > x["price"] else None
                    items.append({"store": "carrefour", "pid": x["id"], "title": x["name"][:300],
                                  "image": (x["img"] or "").split("?")[0] or None,
                                  "url": "https://www.carrefouregypt.com" + x["url"],
                                  "price": x["price"], "list_price": was,
                                  "discount_pct": round((1 - x["price"] / was) * 100) if was else None,
                                  "category": "grocery", "src_category": "carrefour:" + code,
                                  "in_stock": x["stock"] == "inStock"})
                if not res.get("items"):
                    break
                total += len(items)
                stats["items"] += len(items)
                await db.ingest(items)
                pg += 1
                await asyncio.sleep(cfg("carrefour_delay", 2.0) + random.uniform(0, 1.0))
        log(f"carrefour done: {total} products from {len(done)} categories in {int(time.time() - t0)}s")
        await asyncio.sleep(600)


# ═══════════════════ دريم 2000 (متجر Shopify — products.json العام) ═══════════════════
def _guess_cat(title: str, ptype: str = "") -> str:
    t = f"{title} {ptype}".lower()
    for k, c in [("تابلت", "tablets"), ("ايباد", "tablets"), ("ipad", "tablets"), ("لابتوب", "laptops"), ("laptop", "laptops"),
                 ("شاشة", "tvs"), ("تلفزيون", "tvs"), ("tv", "tvs"), ("ساعة", "smartwatches"), ("watch", "smartwatches"),
                 ("سماع", "audio"), ("headphone", "audio"), ("earbud", "audio"), ("سبيكر", "audio"),
                 ("جراب", "mobile_acc"), ("شاحن", "mobile_acc"), ("كابل", "mobile_acc"), ("باور بانك", "mobile_acc"),
                 ("موبايل", "mobiles"), ("هاتف", "mobiles"), ("iphone", "mobiles"), ("ايفون", "mobiles"),
                 ("galaxy", "mobiles"), ("جالكسي", "mobiles"), ("بلايستيشن", "gaming"), ("playstation", "gaming")]:
        if k in t:
            return c
    return "electronics"


async def dream_loop(ctx, db, log, stats, gate, cfg):
    page = await _new_page(ctx)
    try:
        await page.goto("https://dream2000.com/", wait_until="domcontentloaded", timeout=40000)
        log("dream2000 home:", (await page.title())[:60])
    except Exception as e:
        log("dream2000 home error", str(e)[:100])
    js = """async (p) => { try { const r = await fetch('/products.json?limit=250&page=' + p);
        if (!r.ok) return {err: r.status}; return await r.json(); } catch (e) { return {err: String(e)}; } }"""
    while True:
        await gate("dream2000")
        t0, total = time.time(), 0
        for pg in range(1, 200):
            await gate("dream2000")
            stats["requests"] += 1
            res = await _polite(lambda: page.evaluate(js, pg), log, "dream2000", pg)
            if res.get("err"):
                stats["errors"] += 1
                log("dream2000 error", pg, res.get("err"))
                break
            prods = res.get("products") or []
            if not prods:
                break
            items = []
            for p in prods:
                vs = p.get("variants") or []
                v = next((x for x in vs if x.get("available")), vs[0] if vs else None)
                if not v:
                    continue
                price = float(v.get("price") or 0)
                was = float(v.get("compare_at_price") or 0) or None
                if not price:
                    continue
                was = was if was and was > price else None
                img = ((p.get("images") or [{}])[0] or {}).get("src")
                items.append({"store": "dream2000", "pid": str(p["id"]), "title": (p.get("title") or "")[:300],
                              "image": img, "url": f"https://dream2000.com/products/{p.get('handle')}",
                              "price": price, "list_price": was,
                              "discount_pct": round((1 - price / was) * 100) if was else None,
                              "category": _guess_cat(p.get("title") or "", p.get("product_type") or ""),
                              "src_category": "dream2000", "in_stock": any(x.get("available") for x in vs)})
            total += len(items)
            stats["items"] += len(items)
            await db.ingest(items)
            await asyncio.sleep(cfg("dream_delay", 2.0) + random.uniform(0, 1.0))
        log(f"dream2000 done: {total} products in {int(time.time() - t0)}s")
        await asyncio.sleep(600)


# ═══════════════════ دبي فون (صفحات الأقسام فيها بيانات المنتجات جاهزة) ═══════════════════
DUBAI_JS = r"""async (u) => { try {
  const r = await fetch(u); if (!r.ok) return {err: r.status};
  const h = (await r.text()).replace(/\\"/g, '"');
  const re = /\{"id":(\d+),"slug":"([^"]+)","name":"((?:[^"\\]|\\.)*)"[^{}]*?"base_image":"([^"]*)","price":\{"amount":([\d.]+)[^{}]*\},"selling_price":\{"amount":([\d.]+)[^{}]*\}[\s\S]*?"in_stock":(true|false)/g;
  const out = []; let m;
  const pct = {};
  h.split('href="/shop/').slice(1).forEach(seg => { const slug = seg.split('"')[0]; const mm = seg.slice(0, 4000).split('href="/shop/')[0].match(/خصم\s*(\d+)\s*%/); if (mm) pct[slug] = +mm[1]; });
  const spec = [...h.matchAll(/"slug":"([^"]+)"[^{}]*?"has_special_price":true/g)].map(x => x[1]).filter(x => !pct[x]);
  for (const sl of spec.slice(0, 40)) { try { const ph = await (await fetch('/shop/' + sl)).text();
    const mm = ph.match(/خصم\s*(\d+)\s*%/) || ph.replace(/\\"/g, '"').match(/"special_price_percent(?:age)?":"?(\d+)/); if (mm) pct[sl] = +mm[1]; } catch (e) {} }
  while ((m = re.exec(h))) { let was = +m[5]; const p = +m[6]; const d = pct[m[2]]; if (d && !(was > p)) was = Math.round(p / (1 - d / 100));
    out.push({id: m[1], slug: m[2], name: m[3], img: m[4], was, price: p, stock: m[7] === 'true'}); }
  const lp = (h.match(/"last_page":(\d+)/) || [])[1];
  const cats = [...new Set([...h.matchAll(/href="(\/category\/[a-z0-9-]+)"/g)].map(x => x[1]))];
  return {items: out, pages: lp ? +lp : 1, cats};
} catch (e) { return {err: String(e)}; } }"""


async def dubai_loop(ctx, db, log, stats, gate, cfg):
    page = await _new_page(ctx)
    try:
        await page.goto("https://www.dubaiphone.net/", wait_until="domcontentloaded", timeout=40000)
        log("dubaiphone home:", (await page.title())[:60])
    except Exception as e:
        log("dubaiphone home error", str(e)[:100])
    while True:
        await gate("dubaiphone")
        t0, total = time.time(), 0
        home = await page.evaluate(DUBAI_JS, "/")
        queue = list(home.get("cats") or [])
        done, seen = set(), set()
        while queue and len(done) < 200:
            c = queue.pop(0)
            if c in done:
                continue
            done.add(c)
            pg, pages = 1, 1
            while pg <= min(pages, 60):
                await gate("dubaiphone")
                stats["requests"] += 1
                res = await page.evaluate(DUBAI_JS, f"{c}?page={pg}")
                if res.get("err"):
                    stats["errors"] += 1
                    log("dubaiphone error", c, pg, res.get("err"))
                    break
                if pg == 1:
                    queue += [x for x in (res.get("cats") or []) if x not in done]
                pages = res.get("pages") or 1
                items = []
                for x in res.get("items") or []:
                    if x["id"] in seen or not x["price"]:
                        continue
                    seen.add(x["id"])
                    was = x["was"] if x["was"] > x["price"] else None
                    items.append({"store": "dubaiphone", "pid": x["id"], "title": x["name"][:300], "image": x["img"] or None,
                                  "url": f"https://www.dubaiphone.net/shop/{x['slug']}", "price": x["price"],
                                  "list_price": was, "discount_pct": round((1 - x["price"] / was) * 100) if was else None,
                                  "category": _guess_cat(x["name"]), "src_category": "dubaiphone", "in_stock": x["stock"]})
                total += len(items)
                stats["items"] += len(items)
                await db.ingest(items)
                pg += 1
                await asyncio.sleep(cfg("dubai_delay", 2.0) + random.uniform(0, 1.0))
        log(f"dubaiphone done: {total} products from {len(done)} categories in {int(time.time() - t0)}s")
        await asyncio.sleep(600)



# ═══════════════════ Feed Adapter عام — لأي فيد منتجات رسمي (JSON / CSV) ═══════════════════
# الإعداد من collector config:  "feeds": [{"store": "breadfast", "url": "...", "format": "json"|"csv",
#   "items_path": "data.products", "map": {"pid": "id", "title": "name", "price": "price", "list_price": "old_price",
#   "image": "image", "url": "link", "category": "category", "in_stock": "available"}, "every_min": 60, "headers": {...}}]
def _dig(o, path):
    for k in [p for p in (path or "").split(".") if p]:
        o = o.get(k) if isinstance(o, dict) else (o[int(k)] if isinstance(o, list) and k.isdigit() and int(k) < len(o) else None)
    return o


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("EGP", "").replace("ج.م", "").strip())
    except Exception:
        return None


async def feed_loop(db, log, stats, gate, cfg, http):
    import csv, io
    last = {}
    while True:
        feeds = cfg("feeds", []) or []
        for f in feeds:
            store, url = f.get("store"), f.get("url")
            if not store or not url or cfg("off_store_" + store, False):
                continue
            if time.time() - last.get(url, 0) < 60 * float(f.get("every_min", 60)):
                continue
            last[url] = time.time()
            try:
                r = await http.get(url, headers=f.get("headers") or {}, timeout=60, follow_redirects=True)
                if r.status_code != 200:
                    log(f"feed {store} error {r.status_code}")
                    continue
                if f.get("format") == "csv":
                    rows = list(csv.DictReader(io.StringIO(r.text)))
                else:
                    rows = _dig(r.json(), f.get("items_path")) or []
                m = f.get("map") or {}
                items = []
                for x in rows:
                    g = lambda k: _dig(x, m.get(k, k))
                    pid, price = g("pid"), _num(g("price"))
                    if not pid or not price:
                        continue
                    was = _num(g("list_price"))
                    was = was if was and was > price else None
                    stock = g("in_stock")
                    items.append({"store": store, "pid": str(pid), "title": str(g("title") or "")[:300],
                                  "image": g("image"), "url": g("url"), "price": price, "list_price": was,
                                  "discount_pct": round((1 - price / was) * 100) if was else None,
                                  "category": f.get("category") or g("category") or "other", "src_category": "feed:" + store,
                                  "in_stock": stock not in (False, 0, "0", "false", "out of stock", "OUT_OF_STOCK")})
                for i in range(0, len(items), 200):
                    await db.ingest(items[i:i + 200])
                stats["items"] += len(items)
                log(f"feed {store} done: {len(items)} products from {len(rows)} rows")
            except Exception as e:
                log(f"feed {store} error", str(e)[:100])
        await asyncio.sleep(60)
