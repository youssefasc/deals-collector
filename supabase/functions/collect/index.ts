// ═══════════════════════════════════════════════════════════════════════════
//  جامع «عروض متتفوتش» السحابي — Supabase Edge Function (مجاني، من غير متصفح)
//  pg_cron بينادي الدالة كل دقيقة → بتاخد أقدم متجر مستحق من جدول collect_jobs،
//  تشتغل عليه لحد ~١٠٠ ثانية، وتحفظ مكان وقوفها. لو المتجر فشل بيتأخر تلقائياً
//  (٥ د ← ١٠ ← ٢٠ … لحد ١٢ ساعة) من غير ما يأثر على باقي المتاجر.
//  كل الطلبات HTTP عادية لصفحات/واجهات عامة — من غير أي تمويه أو تخطّي حماية.
// ═══════════════════════════════════════════════════════════════════════════
const SB_URL = Deno.env.get("SUPABASE_URL")!;
const SB_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ||
  (() => { try { return JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}").default; } catch { return ""; } })();
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";
const BUDGET_MS = 100_000;          // وقت الشغل في كل نداء (الحد المجاني ١٥٠ ثانية)
const AMAZON_TAG = "3rodmattfwt4-21";
const AMAZON_NOW_SMID = "A1ZDHAJPXGB6WS";

type Item = Record<string, unknown>;
type Step = { items: Item[]; cursor: any; done: boolean; note?: string };

// ─────────────────────────── أدوات ───────────────────────────
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const jitter = (ms: number) => sleep(ms + Math.random() * 800);

class HttpErr extends Error { constructor(public status: number, msg: string) { super(msg); } }

async function get(url: string, init: RequestInit = {}): Promise<string> {
  const r = await fetch(url, {
    ...init,
    headers: { "User-Agent": UA, "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
               "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", ...(init.headers || {}) },
    signal: AbortSignal.timeout(30_000),
  });
  const t = await r.text();
  if (!r.ok) throw new HttpErr(r.status, `${r.status} ${url.slice(0, 90)}`);
  return t;
}

async function rpc(fn: string, args: unknown) {
  const r = await fetch(`${SB_URL}/rest/v1/rpc/${fn}`, {
    method: "POST", body: JSON.stringify(args),
    headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json" },
  });
  const t = await r.text();
  if (!r.ok) throw new Error(`rpc ${fn} ${r.status}: ${t.slice(0, 200)}`);
  return t ? JSON.parse(t) : null;
}

async function patchJob(store: string, patch: Record<string, unknown>) {
  await fetch(`${SB_URL}/rest/v1/collect_jobs?store=eq.${store}`, {
    method: "PATCH", body: JSON.stringify({ ...patch, updated_at: new Date().toISOString() }),
    headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json", Prefer: "return=minimal" },
  });
}

let _token = "";
async function ingestToken() {
  if (_token) return _token;
  const r = await fetch(`${SB_URL}/rest/v1/collector_state?key=eq.ingest_token&select=value`,
    { headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` } });
  _token = (await r.json())[0]?.value ?? "";
  return _token;
}

async function ingest(items: Item[]) {
  if (!items.length) return;
  for (let i = 0; i < items.length; i += 200) await rpc("ingest_products", { token: await ingestToken(), items: items.slice(i, i + 200) });
}

const num = (v: unknown): number | null => {
  if (v && typeof v === "object") v = (v as any).amount ?? (v as any).value ?? (v as any).price;
  if (v === null || v === undefined || v === "") return null;
  const n = parseFloat(String(v).replace(/,/g, ""));
  return isNaN(n) ? null : n;
};
const pct = (p: number, was: number | null) => (was && was > p ? Math.round((1 - p / was) * 100) : null);
const unesc = (s: string) => { try { return JSON.parse(`"${s}"`); } catch { return s; } };

function guessCat(t: string): string {
  t = t.toLowerCase();
  const m: [string, string][] = [["تابلت", "tablets"], ["ايباد", "tablets"], ["ipad", "tablets"], ["لابتوب", "laptops"], ["laptop", "laptops"],
    ["شاشة", "tvs"], ["تلفزيون", "tvs"], ["tv", "tvs"], ["ساعة", "smartwatches"], ["watch", "smartwatches"],
    ["سماع", "audio"], ["headphone", "audio"], ["earbud", "audio"], ["سبيكر", "audio"],
    ["جراب", "mobile_acc"], ["شاحن", "mobile_acc"], ["كابل", "mobile_acc"], ["باور بانك", "mobile_acc"], ["cable", "mobile_acc"], ["charger", "mobile_acc"], ["power bank", "mobile_acc"],
    ["موبايل", "mobiles"], ["هاتف", "mobiles"], ["iphone", "mobiles"], ["ايفون", "mobiles"], ["router", "electronics"],
    ["galaxy", "mobiles"], ["جالكسي", "mobiles"], ["بلايستيشن", "gaming"], ["playstation", "gaming"]];
  for (const [k, c] of m) if (t.includes(k)) return c;
  return "electronics";
}

// ─────────────────────────── دريم ٢٠٠٠ (Shopify products.json العامة) ───────────────────────────
async function dream2000(c: any): Promise<Step> {
  const page = c?.page || 1;
  const j = JSON.parse(await get(`https://dream2000.com/products.json?limit=250&page=${page}`));
  const prods = j.products || [];
  const items: Item[] = [];
  for (const p of prods) {
    const vs = p.variants || [];
    const v = vs.find((x: any) => x.available) || vs[0];
    if (!v) continue;
    const price = num(v.price); if (!price) continue;
    let was = num(v.compare_at_price); was = was && was > price ? was : null;
    items.push({ store: "dream2000", pid: String(p.id), title: String(p.title || "").slice(0, 300),
      image: p.images?.[0]?.src || null, url: `https://dream2000.com/products/${p.handle}`,
      price, list_price: was, discount_pct: pct(price, was), category: guessCat(`${p.title} ${p.product_type || ""}`),
      src_category: "dream2000", in_stock: vs.some((x: any) => x.available) });
  }
  await jitter(1500);
  return { items, cursor: { page: page + 1 }, done: prods.length === 0 };
}

// ─────────────────────────── اتصالات e& (JSON العام اللي صفحات المتجر بتطلبه) ───────────────────────────
const ET_SEED = [29, 2, 27, 5, 36, 35, 26];
function etProducts(o: any): any[] {
  if (Array.isArray(o)) {
    if (o.length && typeof o[0] === "object" && o[0] && ["price", "finalPrice", "productPrice", "sku", "originalPrice"].some((k) => k in o[0])) return o;
    for (const x of o) { const r = etProducts(x); if (r.length) return r; }
  } else if (o && typeof o === "object") {
    for (const k of ["products", "productList", "items"]) if (Array.isArray(o[k]) && o[k].length) return o[k];
    for (const v of Object.values(o)) { const r = etProducts(v); if (r.length) return r; }
  }
  return [];
}
async function etisalat(c: any): Promise<Step> {
  c = c?.queue ? c : { queue: [...ET_SEED], done: [], cid: null, page: 0, cat: "" };
  if (c.cid === null) {
    while (c.queue.length && c.done.includes(c.queue[0])) c.queue.shift();
    if (!c.queue.length) return { items: [], cursor: null, done: true };
    c.cid = c.queue.shift(); c.page = 0;
  }
  const j = JSON.parse(await get(`https://eand.com.eg/eshopapi/v1/category/getCategoryWithSubCategories?categoryId=${c.cid}&count=48&page=${c.page}`,
    { headers: { Accept: "application/json" } }));
  const resp = j.response || {};
  if (c.page === 0) {
    c.cat = resp.category?.description?.name || String(c.cid);
    for (const sc of resp.subCategories || resp.children || resp.category?.children || []) if (sc?.id && !c.done.includes(sc.id)) c.queue.push(sc.id);
  }
  const rest = Object.fromEntries(Object.entries(resp).filter(([k]) => k !== "category" && k !== "subCategories"));
  const prods = etProducts(rest);
  const items: Item[] = [];
  for (const p of prods) {
    const d = p.description || {};
    const name = d.name || p.name || p.productName; const pid = p.id || p.sku;
    if (!name || !pid) continue;
    let price: number | null = null;
    for (const k of ["finalPrice", "productSpecialPrice", "specialPrice", "salePrice", "price"]) { price = num(p[k]); if (price) break; }
    if (!price) continue;
    let was: number | null = null;
    for (const k of ["originalPrice", "productPrice", "oldPrice", "listPrice", "price"]) { const v = num(p[k]); if (v && v > price) { was = v; break; } }
    let img = (typeof p.image === "object" ? p.image?.imageUrl : p.image) || (p.images || []).find((x: any) => x?.imageUrl)?.imageUrl || null;
    if (img && img.startsWith("/")) img = "https://www.eand.com.eg" + img;
    const stock = p.available ?? (p.quantity == null ? true : p.quantity > 0);
    items.push({ store: "etisalat", pid: String(pid), title: String(name).slice(0, 300), image: img,
      url: `https://www.eand.com.eg/eshop2/#/product/${encodeURIComponent(String(name).trim().replace(/ /g, "-")).replace(/%2D/g, "-")}?pid=${pid}`,
      price, list_price: was, discount_pct: pct(price, was), category: /mobile|device|5g/i.test(String(c.cat)) && !/watch|tab|ipad/i.test(String(name)) && /gb|ram/i.test(String(name)) ? "mobiles" : guessCat(`${name} ${c.cat}`),
      src_category: String(c.cat), in_stock: !!stock });
  }
  if (prods.length < 48 || !items.length) { c.done.push(c.cid); c.cid = null; } else c.page++;
  await jitter(2500);
  return { items, cursor: c, done: false };
}

// ─────────────────────────── طلبات مارت (بيانات __NEXT_DATA__ في صفحات المتجر) ───────────────────────────
const TAL_BASE = "https://www.talabat.com";
const TAL_VENDOR = "/egypt/grocery/619848/maadi-old-el-nahda-street";
const TAL_AID = "9838";
const TAL_CAT: Record<string, string> = { "beauty": "beauty", "personal-care": "health", "pharma-wellness": "health", "cleaning-laundry": "health",
  "household-essentials": "home", "paper-plastic": "home", "baby-corner": "kids", "electronics": "electronics",
  "stationery-games": "books_office", "pet-care": "other" };
async function talGet(path: string) {
  const h = await get(TAL_BASE + path);
  const m = h.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
  if (!m) throw new Error("talabat: no data");
  const arr: any[] = [];
  const walk = (v: any, d: number) => {
    if (!v || d > 14) return;
    if (Array.isArray(v)) {
      if (v.length && v[0] && typeof v[0] === "object" && v[0].dhVendorId && "price" in v[0]) { arr.push(...v); return; }
      for (const x of v) walk(x, d + 1);
    } else if (typeof v === "object") for (const x of Object.values(v)) walk(x, d + 1);
  };
  walk(JSON.parse(m[1]), 0);
  const esc = TAL_VENDOR.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const links = [...new Set([...h.matchAll(new RegExp(`href="(${esc}/[a-z0-9-]+/[a-z0-9-]+)`, "g"))].map((x) => x[1].split("?")[0]))];
  return { arr, links };
}
async function talabat(c: any): Promise<Step> {
  const depth = TAL_VENDOR.split("/").filter(Boolean).length + 2;
  if (!c?.queue) {
    const { links } = await talGet(`${TAL_VENDOR}?aid=${TAL_AID}`);
    const q = links.filter((l) => l.split("/").filter(Boolean).length === depth);
    if (!q.length) throw new Error("talabat: no categories");
    c = { queue: q, seen: [], sub: null, page: 1 };
  }
  if (!c.sub) {
    while (c.queue.length && c.seen.includes(c.queue[0])) c.queue.shift();
    if (!c.queue.length) return { items: [], cursor: null, done: true };
    c.sub = c.queue.shift(); c.seen.push(c.sub); c.page = 1;
  }
  const { arr, links } = await talGet(`${c.sub}?aid=${TAL_AID}&page=${c.page}`);
  if (c.page === 1) for (const l of links) if (l.split("/").filter(Boolean).length === depth && !c.seen.includes(l) && !c.queue.includes(l)) c.queue.push(l);
  const top = c.sub.split("/").filter(Boolean)[depth - 2];
  const cat = TAL_CAT[top] || "grocery";
  const items: Item[] = [];
  for (const x of arr) {
    const price = num(x.price); if (!x.sku || !price) continue;
    let was = num(x.originalPrice); was = was && was > price ? was : null;
    items.push({ store: "talabat", pid: String(x.sku), title: String(x.title || "").slice(0, 300), image: x.image || null,
      url: `${TAL_BASE}/egypt/talabat-mart/product/${x.slug || "p"}/s/${x.sku}`, price, list_price: was, discount_pct: pct(price, was),
      category: cat, src_category: "talabat", in_stock: x.inStock !== false });
  }
  if (!items.length || c.page >= 60) { c.sub = null; } else c.page++;
  await jitter(2500);
  return { items, cursor: c, done: false };
}

// ─────────────────────────── B.TECH (صفحات الأقسام فيها بيانات المنتجات) ───────────────────────────
const BTECH_MAP: Record<string, string> = { "mobiles-tablets": "mobiles", "laptop-pc": "laptops", "tvs-projectors": "tvs", "electronics": "electronics",
  "large-home-appliances": "appliances", "small-home-appliances": "appliances", "air-conditioners": "appliances", "wearables": "smartwatches",
  "personal-care": "health", "gaming-area": "gaming" };
async function btechLeaves(): Promise<string[]> {
  const x = await get("https://btech.com/sitemap.xml");
  const set = new Set<string>();
  let i = 0;
  while ((i = x.indexOf("<loc>https://btech.com/ar/c/", i)) !== -1) {
    const e = x.indexOf("</loc>", i);
    set.add(x.slice(i + 5 + 17, e)); i = e;
  }
  const all = [...set];
  return all.filter((a) => !all.some((b) => b !== a && b.startsWith(a + "/")));
}
async function btech(c: any): Promise<Step> {
  if (!c?.leaves) c = { leaves: await btechLeaves(), i: 0 };
  if (c.i >= c.leaves.length) return { items: [], cursor: null, done: true };
  const path = c.leaves[c.i++];
  const slug = path.split("/")[3] || "";
  const h = (await get("https://btech.com" + path)).replace(/\\"/g, '"');
  const re = /\{"variant_id":"([^"]+)","product_id":"[^"]*","offer_id":"([^"]*)","sku":"([^"]*)","name":"((?:[^"\\]|\\.)*)"[\s\S]*?"thumbnail_url":"([^"]*)","price":\{"final_price":([\d.]+)[\s\S]*?"base_price":([\d.]+)[\s\S]*?"is_in_stock":(true|false)/g;
  const items: Item[] = []; const seen = new Set<string>(); let m;
  while ((m = re.exec(h))) {
    const price = +m[6]; if (!price || seen.has(m[1])) continue; seen.add(m[1]);
    const was = +m[7] > price ? +m[7] : null;
    items.push({ store: "btech", pid: m[1], title: unesc(m[4]).slice(0, 300), image: m[5] ? `https://media.btech.com/catalogs/${m[5]}` : null,
      url: `https://btech.com/ar/p/${m[1]}?offering_id=${m[2]}`, price, list_price: was, discount_pct: pct(price, was),
      category: BTECH_MAP[slug] || "electronics", src_category: "btech", in_stock: m[8] === "true" });
  }
  await jitter(2000);
  return { items, cursor: c, done: false };
}

// ─────────────────────────── أمازون ناو (نتايج البحث جوه المتجر) ───────────────────────────
const NOW_KW = ["ال", "a", "e", "لبن", "جبن", "زبادي", "زبدة", "بيض", "شاي", "قهوة", "نسكافيه", "سكر", "أرز", "مكرونة", "زيت",
  "سمن", "دقيق", "عدس", "فول", "تونة", "صلصة", "كاتشب", "مايونيز", "عسل", "مربى", "شوكولاتة", "بسكويت", "شيبسي", "مقرمشات",
  "حلويات", "عصير", "مياه", "مشروب", "بيبسي", "كوكاكولا", "مشروب طاقة", "حبوب افطار", "شوفان", "خبز", "توست", "فراخ", "لحم",
  "سجق", "لانشون", "خضار", "فاكهة", "طماطم", "بطاطس", "مجمدات", "ايس كريم", "توابل", "ملح", "خل", "كريمة", "حليب أطفال",
  "حفاضات", "مناديل", "ورق تواليت", "صابون", "شامبو", "معجون اسنان", "فرشاة", "مزيل عرق", "منظف", "مسحوق غسيل", "كلور",
  "سائل اطباق", "معطر", "اكياس", "ألومنيوم", "طعام قطط", "طعام كلاب", "فيتامين", "بنادول", "حفاضة", "بامبرز", "جل", "كريم",
  "لوشن", "شفرات", "فوط", "قطن", "مكسرات", "تمر", "زيتون", "مخلل", "بقوليات", "نودلز", "اندومي", "شوربة", "بهارات"];
const BOOK = /غلاف ورقي|غلاف مقوى|غلاف عادي|غلاف لين|Paperback|Hardcover|Kindle|كيندل|ISBN/i;
const AR = "٠١٢٣٤٥٦٧٨٩";
const amzNum = (s?: string) => {
  if (!s) return null;
  s = s.replace(/[٠-٩]/g, (d) => String(AR.indexOf(d))).replace(/٬/g, ",").replace(/٫/g, ".");
  const v = parseFloat(s.replace(/[^0-9.,]/g, "").replace(/,/g, ""));
  return isNaN(v) ? null : v;
};
function amazonCards(h: string) {
  const parts = h.split('data-component-type="s-search-result"').slice(1);
  const out: any[] = [];
  for (const seg0 of parts) {
    const seg = seg0.slice(0, 25000);
    const asin = (seg.match(/data-asin="([A-Z0-9]{10})"/) || [])[1];
    if (!asin || /puis-sponsored-label-text/.test(seg)) continue;
    const title = (seg.match(/<h2[^>]*aria-label="([^"]+)"/) || seg.match(/<h2[^>]*>[\s\S]*?<span[^>]*>([^<]+)<\/span>/) || [])[1] || "";
    const prices = [...seg.matchAll(/<span class="a-price(?: a-text-price)?"[^>]*>\s*<span class="a-offscreen">([^<]+)<\/span>/g)];
    let price: number | null = null, list: number | null = null;
    for (const p of prices) { if (p[0].includes("a-text-price")) list ??= amzNum(p[1]); else price ??= amzNum(p[1]); }
    const img = (seg.match(/<img[^>]*class="s-image"[^>]*src="([^"]+)"/) || seg.match(/class="s-image"[^>]*?src="([^"]+)"/) || [])[1] || null;
    const text = seg.replace(/<[^>]+>/g, " ");
    out.push({ asin, title: title.replace(/&amp;/g, "&").replace(/&quot;/g, '"').trim(), price, list, img,
      oos: /غير متوفر|Currently unavailable/i.test(text), book: BOOK.test(text) });
  }
  return { out, hasNext: /s-pagination-next(?![^"]*s-pagination-disabled)/.test(h) && !/s-pagination-next[^"]*s-pagination-disabled/.test(h) };
}
async function amazonNow(c: any): Promise<Step> {
  c = c?.kw !== undefined ? c : { kw: 0, page: 1 };
  if (c.kw >= NOW_KW.length) return { items: [], cursor: null, done: true };
  const h = await get(`https://www.amazon.eg/s?k=${encodeURIComponent(NOW_KW[c.kw])}&i=amazonnow&almBrandId=sAuWWBROaG&language=ar_AE&page=${c.page}`);
  if (/captcha/i.test(h.slice(0, 5000)) && !/s-search-result/.test(h)) throw new HttpErr(503, "amazon captcha page");
  const { out, hasNext } = amazonCards(h);
  const items: Item[] = [];
  for (const x of out) {
    if (x.book || /^[0-9]{9}[0-9X]$/.test(x.asin) || !x.price) continue;
    const img = x.img ? x.img.replace(/\._[^/]*_\./, "._AC_SL500_.") : null;
    items.push({ store: "amazon_now", pid: x.asin, title: x.title.slice(0, 300), image: img,
      url: `https://www.amazon.eg/dp/${x.asin}?smid=${AMAZON_NOW_SMID}&tag=${AMAZON_TAG}`, price: x.price, list_price: x.list,
      discount_pct: pct(x.price, x.list), category: null, src_category: "search", in_stock: !x.oos });
  }
  if (!hasNext || !items.length || c.page >= 20) { c.kw++; c.page = 1; } else c.page++;
  await jitter(3000);
  return { items, cursor: c, done: false };
}

// ─────────────────────────── وي (كتالوج الأجهزة على te.eg — robots بيسمح) ───────────────────────────
const TE = "https://te.eg";
const TE_SEEDS = ["/en/web/guest/personal/devices/mobile-phones", "/en/web/guest/personal/devices/routers",
  "/en/web/guest/personal/devices/5g-devices/mobile", "/en/web/guest/personal/devices/fixed-landline-phones",
  "/en/web/guest/personal/devices/usb-modems", "/en/web/guest/personal/devices/4g-routers", "/en/web/guest/personal/devices/accessories"];
function weCards(h: string) {
  // كل جهاز في كارت class="device_main_container": الاسم في card_title، والسعر في choose-plan-price-quantity
  const out: any[] = []; const seen = new Set<string>();
  for (const card of h.split('class="device_main_container"').slice(1)) {
    const c = card.slice(0, 12000);
    const link = c.match(/href="((?:https:\/\/te\.eg)?\/[^"]*?\/w\/([a-z0-9-]+))"/i);
    if (!link || seen.has(link[2])) continue;
    const nums = [...c.matchAll(/choose-plan-price-quantity">\s*(?:<span>)?\s*([\d,]+(?:\.\d+)?)/g)].map((x) => num(x[1])!).filter((x) => x > 0);
    if (!nums.length) continue;
    seen.add(link[2]);
    const name = ((c.match(/card_title"[^>]*>\s*<div>\s*([^<]+?)\s*<\/div>/) || [])[1] || link[2].replace(/-/g, " ")).trim();
    const img = (c.match(/<img[^>]+src="([^"]+)"/) || [])[1] || null;
    const price = nums.length > 1 ? Math.min(...nums) : nums[0];
    const was = nums.length > 1 && Math.max(...nums) > price ? Math.max(...nums) : null;
    out.push({ slug: link[2], url: (link[1].startsWith("http") ? "" : TE) + link[1], price, was,
      img: img ? (img.startsWith("http") ? img : TE + img) : null, name, oos: /out of stock|غير متوفر|نفذ/i.test(c) });
  }
  return out;
}
async function we(c: any): Promise<Step> {
  c = c?.queue ? c : { queue: [...TE_SEEDS], done: [] };
  while (c.queue.length && c.done.includes(c.queue[0])) c.queue.shift();
  if (!c.queue.length) return { items: [], cursor: null, done: true };
  const path = c.queue.shift(); c.done.push(path);
  const h = await get(TE + path);
  for (const l of [...h.matchAll(/href="(?:https:\/\/te\.eg)?(\/en\/web\/guest\/personal\/devices\/[a-z0-9/-]+)"/g)].map((x) => x[1]))
    if (!c.done.includes(l) && !c.queue.includes(l) && c.done.length + c.queue.length < 40) c.queue.push(l);
  const catname = path.split("/devices/")[1] || "";
  const items: Item[] = weCards(h).map((x) => ({ store: "we", pid: x.slug.slice(0, 120), title: x.name.slice(0, 300), image: x.img, url: x.url,
    price: x.price, list_price: x.was, discount_pct: pct(x.price, x.was),
    category: catname.includes("mobile") ? "mobiles" : guessCat(x.name + (catname.includes("router") ? " router" : "")),
    src_category: "we:" + catname, in_stock: !x.oos }));
  await jitter(3000);
  return { items, cursor: c, done: false };
}

const ADAPTERS: Record<string, (c: any) => Promise<Step>> = {
  dream2000, etisalat, talabat, btech, amazon_now: amazonNow, we,
};

// ─────────────────────────── التشغيل ───────────────────────────
async function runJob(job: any) {
  const t0 = Date.now();
  const fn = ADAPTERS[job.store];
  let cursor = job.cursor, total = 0, passDone = false, steps = 0;
  const passStarted = cursor ? job.pass_started : new Date().toISOString();
  let passItems = cursor ? (job.pass_items || 0) : 0;
  try {
    while (Date.now() - t0 < BUDGET_MS) {
      const r = await fn(cursor);
      steps++;
      await ingest(r.items);
      total += r.items.length; passItems += r.items.length;
      cursor = r.cursor;
      if (r.done) { passDone = true; break; }
      await patchJob(job.store, { cursor, pass_items: passItems, pass_started: passStarted });
    }
    const now = new Date();
    await patchJob(job.store, passDone
      ? { cursor: null, locked_until: null, fail_count: 0, last_ok: now.toISOString(), pass_items: 0,
          last_pass_items: passItems, last_pass_secs: Math.round((now.getTime() - new Date(passStarted).getTime()) / 1000),
          next_run: new Date(now.getTime() + job.interval_min * 60_000).toISOString(), pass_started: null }
      : { cursor, locked_until: null, fail_count: 0, last_ok: now.toISOString(), pass_items: passItems, pass_started: passStarted,
          next_run: now.toISOString() });   // لسه مخلصش اللفة → يكمّل في النداء الجاي
    return { store: job.store, steps, items: total, passDone, ms: Date.now() - t0 };
  } catch (e) {
    const fails = (job.fail_count || 0) + 1;
    const status = e instanceof HttpErr ? e.status : 0;
    // ٤٠٣/٤٢٩ = المتجر بيقول استنى → بنهدى أكتر. باقي الأخطاء: ٥ د ← ١٠ ← ٢٠ … لحد ١٢ ساعة
    const base = status === 403 || status === 429 ? 30 : 5;
    const wait = Math.min(720, base * 2 ** (fails - 1));
    await ingest([]).catch(() => {});
    await patchJob(job.store, { cursor, locked_until: null, fail_count: fails, last_err: String(e).slice(0, 300),
      last_err_at: new Date().toISOString(), pass_items: passItems, pass_started: passStarted,
      next_run: new Date(Date.now() + wait * 60_000).toISOString() });
    return { store: job.store, steps, items: total, error: String(e).slice(0, 200), retry_in_min: wait };
  }
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  // التشغيل مسموح بس بمفتاح الجامع (pg_cron بيبعته من قاعدة البيانات)
  if ((req.headers.get("x-collector-key") || "") !== await ingestToken())
    return new Response("forbidden", { status: 403 });
  if (url.searchParams.get("peek")) {   // أداة فحص: أول جزء من صفحة
    const h = await get(url.searchParams.get("peek")!);
    const at = Math.max(0, h.indexOf(url.searchParams.get("near") || "") - 1500);
    return new Response(JSON.stringify({ len: h.length, snip: h.slice(at, at + 6000) }), { headers: { "Content-Type": "application/json" } });
  }
  const store = url.searchParams.get("store");
  const jobs = await rpc("claim_collect_job", { p_store: store });
  if (!jobs?.length) return new Response(JSON.stringify({ idle: true }), { headers: { "Content-Type": "application/json" } });
  const res = await runJob(jobs[0]);
  console.log(JSON.stringify(res));
  return new Response(JSON.stringify(res), { headers: { "Content-Type": "application/json" } });
});
