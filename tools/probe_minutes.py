import re, json, urllib.request, gzip, sys
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}), timeout=30)
    b = r.read(); b = gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b
    return b.decode("utf-8", "replace")
for u in sys.argv[1:]:
    t = get(u)
    links = set(re.findall(r'now-product/(Z[A-Z0-9]+-\d+)', t))
    ld = re.search(r'<script id="catalog-json-ld[^>]*>(.*?)</script>', t, re.S)
    items = json.loads(ld.group(1)).get("itemListElement", []) if ld else []
    m = re.search(r'nbHits:(\d+)', t); p = re.search(r'nbPages:(\d+)', t)
    stock = re.findall(r'(isBuyable|inStock|is_buyable|stock[A-Za-z]*):(!0|!1|\d+)', t)
    from collections import Counter
    print(u, "links", len(links), "ld", len(items), "nbHits", m and m.group(1), "nbPages", p and p.group(1), "kb", len(t)//1024, Counter(stock).most_common(6))
    if items: print("  first:", items[0]["item"]["name"], items[0]["item"]["offers"]["price"])
