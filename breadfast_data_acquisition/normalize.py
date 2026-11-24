"""توحيد بيانات Breadfast من أي مصدر مصرّح بيه لصيغة واحدة + كشف التكرار + فحص الاكتمال."""
import re
import unicodedata

# أسماء الأعمدة المحتملة في ملفات المصادر المختلفة → الاسم الموحد
ALIASES = {
    "sku": ["sku", "id", "product_id", "item_id", "رقم المنتج", "كود", "code", "article"],
    "barcode": ["barcode", "ean", "gtin", "upc", "الباركود", "باركود"],
    "title": ["title", "name", "product_name", "item_name", "اسم المنتج", "الاسم", "name_ar"],
    "title_en": ["name_en", "title_en", "english_name"],
    "brand": ["brand", "brand_name", "manufacturer", "الماركة", "العلامة التجارية"],
    "category": ["category", "category_name", "department", "القسم", "التصنيف"],
    "subcategory": ["subcategory", "sub_category", "التصنيف الفرعي"],
    "description": ["description", "desc", "الوصف"],
    "size": ["size", "weight", "volume", "unit_size", "الوزن", "الحجم"],
    "pack_count": ["pack", "pack_count", "pieces", "qty_per_pack", "عدد القطع"],
    "list_price": ["list_price", "original_price", "old_price", "price_before", "السعر الأصلي", "rrp"],
    "price": ["price", "sale_price", "selling_price", "final_price", "سعر البيع", "السعر"],
    "in_stock": ["in_stock", "available", "availability", "stock_status", "متاح", "التوفر"],
    "image": ["image", "image_url", "img", "صورة"],
    "url": ["url", "link", "product_url", "الرابط"],
    "region": ["region", "zone", "area", "city", "المنطقة"],
}

CATEGORY_MAP = [  # توحيد أقسام Breadfast لأقسام المنصة
    (r"beauty|care|cosmetic|عناية|تجميل|شعر|بشرة", "beauty"),
    (r"clean|household|detergent|tissue|منظف|مناديل|منزل", "home"),
    (r"electronic|mobile|charger|إلكترون|شاحن", "audio"),
]


def _key(s):
    return re.sub(r"[\s_\-]+", " ", unicodedata.normalize("NFKC", str(s))).strip().lower()


def map_columns(row: dict) -> dict:
    low = {_key(k): v for k, v in row.items()}
    out = {}
    for std, names in ALIASES.items():
        for n in names:
            v = low.get(_key(n))
            if v not in (None, ""):
                out[std] = v
                break
    return out


def num(v):
    if v in (None, ""):
        return None
    s = re.sub(r"[^\d.,٠-٩]", "", str(v)).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")).replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def boolish(v):
    if v is None or v == "":
        return None
    s = _key(v)
    if s in ("1", "true", "yes", "y", "in stock", "available", "متاح", "نعم", "متوفر"):
        return True
    if s in ("0", "false", "no", "n", "out of stock", "unavailable", "غير متاح", "لا", "نفد"):
        return False
    return None


def clean_brand(b):
    if not b:
        return None
    b = re.sub(r"\s+", " ", str(b)).strip()
    return b.title() if b.isascii() else b


def site_category(cat):
    c = _key(cat or "")
    for pat, k in CATEGORY_MAP:
        if re.search(pat, c):
            return k
    return "grocery"


def normalize(row: dict, source: str, fetched_at: str):
    """يرجّع (منتج موحد, قائمة مشاكل). المنتج None لو ناقصه أساسيات."""
    r = map_columns(row)
    problems = []
    price = num(r.get("price"))
    lp = num(r.get("list_price"))
    sku = str(r.get("sku") or "").strip() or None
    barcode = re.sub(r"\D", "", str(r.get("barcode") or "")) or None
    title = (r.get("title") or "").strip() or None
    if not (sku or barcode):
        problems.append("مفيش رقم منتج ولا باركود")
    if not title:
        problems.append("مفيش اسم")
    if price is None or price <= 0:
        problems.append("مفيش سعر صالح")
    if problems:
        return None, problems
    if lp is None or lp < price:
        lp = price
    return {
        "pid": sku or f"bc{barcode}",
        "barcode": barcode, "title": title, "title_en": r.get("title_en"),
        "brand": clean_brand(r.get("brand")),
        "src_category": " / ".join(x for x in (r.get("category"), r.get("subcategory")) if x) or None,
        "category": site_category(r.get("category")),
        "description": r.get("description"), "size": r.get("size"),
        "pack_count": str(r["pack_count"]) if r.get("pack_count") else None,
        "price": price, "list_price": lp,
        "discount_pct": round((1 - price / lp) * 100) if lp > price else 0,
        "in_stock": boolish(r.get("in_stock")) if boolish(r.get("in_stock")) is not None else True,
        "image": r.get("image"), "url": r.get("url"),
        "region": r.get("region") or "غير محدد في المصدر",
        "source": source, "source_at": fetched_at,
    }, []


def dedupe(items):
    """تكرار = نفس الباركود، أو نفس الرقم، أو نفس (الاسم+الحجم+الماركة). بيحتفظ بأحدث نسخة."""
    seen, out, dups = {}, [], 0
    for it in items:
        keys = [k for k in (
            it["barcode"] and f"b:{it['barcode']}",
            f"p:{it['pid']}",
            f"n:{_key(it['title'])}|{_key(it.get('size') or '')}|{_key(it.get('brand') or '')}") if k]
        hit = next((seen[k] for k in keys if k in seen), None)
        if hit is not None:
            dups += 1
            merged = dict(out[hit])
            merged.update({k: v for k, v in it.items() if v not in (None, "")})   # الأحدث يكسب، والناقص بيتكمّل من القديم
            out[hit] = merged
        else:
            out.append(it)
            hit = len(out) - 1
        for k in keys:
            seen[k] = hit
    return out, dups


FIELDS = ["barcode", "brand", "src_category", "description", "size", "pack_count", "image", "url", "region"]


def completeness(items):
    n = len(items) or 1
    return {f: round(100 * sum(1 for i in items if i.get(f)) / n) for f in FIELDS}
