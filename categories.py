"""تصنيف منتجات أمازون لأقسام الموقع، من رمز القسم ونوع المنتج اللي أمازون بترجعهم."""

ACCESSORY_TYPES = ("CASE", "COVER", "ACCESSORY", "PROTECTOR", "STRAP", "BAND", "CABLE", "HOLDER",
                   "MOUNT", "STAND", "SKIN", "STICKER", "ADAPTER", "CHARGER")


def categorize(gl: str, ptype: str) -> str:
    gl = (gl or "").lower()
    pt = (ptype or "").upper()
    acc = any(x in pt for x in ACCESSORY_TYPES)
    if gl.startswith("gl_wireless"):
        return "mobile_acc" if acc or pt not in ("CELLULAR_PHONE", "MOBILE_PHONE", "SMARTPHONE") else "mobiles"
    if pt in ("TABLET_COMPUTER",):
        return "tablets"
    if pt in ("NOTEBOOK_COMPUTER", "PERSONAL_COMPUTER", "LAPTOP"):
        return "laptops"
    if gl in ("gl_pc",):
        return "computer_acc"
    if pt in ("TELEVISION",) or "TELEVISION" in pt:
        return "tvs"
    if pt in ("HEADPHONES", "SPEAKERS", "EARBUDS", "SOUNDBAR") or "HEADPHONE" in pt or "SPEAKER" in pt:
        return "audio"
    if "WATCH" in pt and gl in ("gl_wireless", "gl_ce") and "BAND" not in pt and "STRAP" not in pt:
        return "smartwatches"
    if gl in ("gl_major_appliances",) or pt in ("WASHER", "DRYER", "REFRIGERATOR", "AIR_CONDITIONER", "MICROWAVE_OVEN"):
        return "appliances"
    if gl in ("gl_ce", "gl_camera", "gl_electronics"):
        return "electronics"
    if gl in ("gl_video_games",):
        return "gaming"
    if gl in ("gl_kitchen", "gl_home", "gl_home_improvement", "gl_furniture", "gl_lawn_and_garden"):
        if gl == "gl_kitchen" and any(x in pt for x in ("BLENDER", "MIXER", "FRYER", "KETTLE", "COFFEE", "TOASTER", "OVEN", "PROCESSOR", "JUICER", "GRILL")):
            return "appliances"
        return "home"
    if gl in ("gl_grocery",):
        return "grocery"
    if gl in ("gl_beauty", "gl_luxury_beauty", "gl_personal_care_appliances"):
        return "beauty"
    if gl in ("gl_drugstore", "gl_health"):
        return "health"
    if gl in ("gl_apparel", "gl_shoes", "gl_luggage", "gl_jewelry", "gl_watch"):
        return "fashion"
    if gl in ("gl_toy", "gl_baby_product"):
        return "kids"
    if gl in ("gl_sports",):
        return "sports"
    if gl in ("gl_automotive",):
        return "auto"
    if gl in ("gl_book", "gl_office_product"):
        return "books_office"
    return "other"
