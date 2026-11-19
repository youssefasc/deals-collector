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
        res = await page.evaluate(TALABAT_JS, f"{TALABAT_VENDOR}?aid={TALABAT_AID}")
        norm = lambda l: l.split("?")[0]
        queue = [norm(l) for l in (res.get("links") or []) if len(norm(l).strip("/").split("/")) == vparts + 2]
        if not queue:
            log("talabat: no categories found", res.get("err"), res.get("title"))
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
                r = await page.evaluate(TALABAT_JS, f"{sub}?aid={TALABAT_AID}&page={pg}")
                if r.get("err"):
                    stats["errors"] += 1
                    log("talabat error", sub, pg, r.get("err"))
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
