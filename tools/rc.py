#!/usr/bin/env python3
"""Restaurant reservation availability checker (Amsterdam, Zenchef-centric).
Usage:
  rc.py detect <url> [<url>...]      detect booking platform ids on a website
  rc.py zc <rid> [date] [pax]         Zenchef availability (default 2026-09-08, 3)
  rc.py ft <formitable_uid>           map Formitable uid -> Zenchef id
  rc.py bing "<query>"                top organic result URLs from Bing
  rc.py check "<Name>" <url|zc:RID|ft:UID> [date] [pax]   full pipeline, appends JSON line to results.jsonl
"""
import sys, re, json, html, time, os, urllib.parse
import requests, urllib3
urllib3.disable_warnings()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
H = {"User-Agent": UA, "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8", "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"}
DATE = "2026-09-08"; PAX = 3
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results.jsonl")

def get(url, timeout=25, **kw):
    return requests.get(url, headers=H, timeout=timeout, verify=False, allow_redirects=True, **kw)

def fetch_html(url):
    """Return (final_url, text) or (None, error)."""
    tried = []
    variants = [url]
    if not url.startswith("http"): variants = ["https://" + url, "http://" + url]
    u = urllib.parse.urlparse(variants[0])
    host = u.netloc
    if host.startswith("www."):
        variants.append(variants[0].replace("www.", "", 1))
    else:
        variants.append(variants[0].replace("://", "://www.", 1))
    for v in variants:
        try:
            r = get(v)
            if r.status_code < 400 and r.text:
                return r.url, r.text
            tried.append(f"{v} -> {r.status_code}")
        except Exception as e:
            tried.append(f"{v} -> {type(e).__name__}: {str(e)[:80]}")
    return None, "; ".join(tried)

PATTERNS = {
    "zenchef": [r'bookings\.zenchef\.com/results\?[^"\'\s]*?rid=(\d{4,7})', r'zenchef[^"\'\s]{0,80}?rid=(\d{4,7})', r'zc-widget-config[^>]*data-restaurant="(\d{4,7})"', r'data-restaurant="(\d{4,7})"', r'zenchef\.com[^"\'\s]*?[?&]rid=(\d{4,7})', r'restaurantId[=:]"?(\d{5,7})'],
    "formitable": [r'data-restaurant="([0-9a-f]{8})"', r'widget\.formitable\.com/(?:side|formitable|app)?/?([0-9a-f]{8})', r'formitable\.com/[^"\'\s]*?([0-9a-f]{8})(?![0-9a-f])'],
    "guestplan": [r'_gstpln\.accessKey\s*=\s*"([0-9a-f]{20,})"', r'guestplan\.com/[^"\'\s]*?([0-9a-f]{40})'],
    "tebi": [r'data-widget-token="([0-9_a-f]+)"'],
    "thefork_module": [r'module\.lafourchette\.com/[a-z_]+/module/(\d+-\d+)', r'module\.lafourchette\.com/[a-z_]+/module/([0-9a-f-]{20,})'],
    "thefork": [r'(https?://(?:www\.)?thefork\.[a-z.]+/restaurant/[^"\'\s<>]+)'],
    "opentable": [r'(https?://(?:www\.)?opentable\.[a-z.]+/[^"\'\s<>]+)'],
    "sevenrooms": [r'sevenrooms\.com/(?:reservations|explore|widget/reservations)/([a-zA-Z0-9_-]+)'],
    "resengo": [r'(https?://[a-z.]*resengo\.com/[^"\'\s<>]+)'],
    "tableo": [r'(https?://[a-z.]*tableo\.com/[^"\'\s<>]+)'],
    "resos": [r'(https?://[a-z.]*resos\.com/[^"\'\s<>]+)'],
    "superb": [r'(https?://[a-z.]*superbexperience\.com/[^"\'\s<>]+)'],
    "tock": [r'(https?://[a-z.]*exploretock\.com/[^"\'\s<>]+)'],
    "quandoo": [r'(https?://[a-z.]*quandoo\.[a-z]+/[^"\'\s<>]+)'],
    "couverts": [r'(https?://[a-z.]*couverts\.nl/[^"\'\s<>]+)'],
    "eatbookings": [r'(https?://[a-z.]*eat[-]?bookings?\.[a-z]+/[^"\'\s<>]+)'],
    "bookdinners": [r'(https?://[a-z.]*bookdinners\.[a-z]+/[^"\'\s<>]+)'],
    "dinnerbooking": [r'(https?://[a-z.]*dinnerbooking\.com/[^"\'\s<>]+)'],
    "resmio": [r'(https?://[a-z.]*resmio\.com/[^"\'\s<>]+)'],
    "mytable": [r'(https?://[a-z.]*mytable\.[a-z]+/[^"\'\s<>]+)'],
    "resy": [r'(https?://[a-z.]*resy\.com/[^"\'\s<>]+)'],
    "easytable": [r'(https?://[a-z.]*easytable\.[a-z]+/[^"\'\s<>]+)'],
    "hostme": [r'(https?://[a-z.]*hostmeapp\.com/[^"\'\s<>]+)'],
    "gastrofix": [r'(https?://[a-z.]*gastrofix\.[a-z]+/[^"\'\s<>]+)'],
    "restaurantbooking_generic": [r'(https?://[a-z0-9.-]*(?:reserv|booking|book)[a-z0-9.-]*\.[a-z]{2,4}/[^"\'\s<>]{0,120})'],
}

def scan(text):
    found = {}
    for k, pats in PATTERNS.items():
        for p in pats:
            for m in re.finditer(p, text, re.I):
                found.setdefault(k, [])
                v = html.unescape(m.group(1))
                if v not in found[k]: found[k].append(v)
    return found

def reservation_links(base, text):
    links = []
    for m in re.finditer(r'href="([^"]+)"[^>]*>([^<]{0,80})', text, re.I):
        href, label = html.unescape(m.group(1)), m.group(2)
        if re.search(r'reserv|book|tafel|table', href + " " + label, re.I):
            full = urllib.parse.urljoin(base, href)
            if full not in links: links.append(full)
    return links

def detect(urls, max_follow=4):
    out = {"pages": [], "found": {}, "links": []}
    seen = set()
    queue = list(urls)
    while queue and len(out["pages"]) < 1 + max_follow:
        u = queue.pop(0)
        if u in seen: continue
        seen.add(u)
        final, text = fetch_html(u)
        if not final:
            out["pages"].append({"url": u, "error": text}); continue
        out["pages"].append({"url": final, "size": len(text)})
        f = scan(text)
        for k, v in f.items():
            out["found"].setdefault(k, [])
            for x in v:
                if x not in out["found"][k]: out["found"][k].append(x)
        links = reservation_links(final, text)
        for l in links:
            if l not in out["links"]: out["links"].append(l)
        strong = any(k in out["found"] for k in ("zenchef", "formitable", "guestplan", "tebi", "thefork_module", "sevenrooms", "resengo", "tableo", "resos"))
        if strong: break
        # scan same-site / site-builder JS bundles and inline JSON for injected widget ids
        host = urllib.parse.urlparse(final).netloc
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', text, re.I)
        picked = []
        for sc in scripts:
            full = urllib.parse.urljoin(final, html.unescape(sc))
            h = urllib.parse.urlparse(full).netloc
            if h == host or any(x in h for x in ("wixstatic", "parastorage", "squarespace", "webflow", "website-files", "cdn.shopify", "jouwweb", "wp-content")):
                if not re.search(r'jquery|bootstrap|gtm|analytics|polyfill|fontawesome|swiper|lazysizes|wp-includes', full, re.I):
                    picked.append(full)
        for full in picked[:8]:
            try:
                r = get(full, timeout=20)
                if r.status_code < 400 and len(r.text) < 3_000_000:
                    f2 = scan(r.text)
                    for k, v in f2.items():
                        if k == "restaurantbooking_generic": continue
                        out["found"].setdefault(k, [])
                        for x in v:
                            if x not in out["found"][k]: out["found"][k].append(x)
                    out.setdefault("scanned_js", []).append(full)
            except Exception:
                pass
        if any(k in out["found"] for k in ("zenchef", "formitable", "guestplan", "tebi", "thefork_module", "sevenrooms")): break
        # follow same-host reservation links, then common paths
        host = urllib.parse.urlparse(final).netloc
        for l in links:
            if urllib.parse.urlparse(l).netloc == host and l not in seen and l.split('#')[0] != final:
                queue.append(l)
        if not queue:
            for p in ("reserveren", "reservations", "reserveer", "reservation", "reserveringen", "book", "contact", "en/reservations", "nl/reserveren"):
                cand = urllib.parse.urljoin(final, "/" + p)
                if cand not in seen: queue.append(cand)
    return out

def zc_info(rid):
    try:
        r = get(f"https://bookings-middleware.zenchef.com/getRestaurantInfo?restaurantId={rid}", timeout=20)
        if r.status_code == 200 and r.text.startswith("{"):
            j = r.json(); return {"name": j.get("name"), "address": j.get("address"), "zip": j.get("zip"), "city": j.get("city"), "website": j.get("website")}
        return {"error": f"{r.status_code} {r.text[:80]}"}
    except Exception as e:
        return {"error": str(e)[:100]}

def zc_avail(rid, date=DATE, pax=PAX):
    res = {"rid": rid, "date": date, "pax": pax}
    try:
        s = get(f"https://bookings-middleware.zenchef.com/getAvailabilitiesSummary?restaurantId={rid}&date_begin={date}&date_end={date}", timeout=25)
        if not s.text.startswith("["):
            res["error"] = f"summary {s.status_code} {s.text[:100]}"; return res
        sj = s.json()
        day = sj[0] if sj else {}
        res["isOpen"] = day.get("isOpen")
        res["summary_shifts"] = [{"name": sh.get("name"), "closed": sh.get("closed"), "possible_guests": sh.get("possible_guests"), "waitlist": sh.get("waitlist_possible_guests"), "offer_required": sh.get("is_offer_required"), "bookable_to": sh.get("bookable_to")} for sh in day.get("shifts", [])]
        a = get(f"https://bookings-middleware.zenchef.com/getAvailabilities?restaurantId={rid}&date_begin={date}&date_end={date}", timeout=40)
        if a.text.startswith("["):
            aj = a.json(); dayd = aj[0] if aj else {}
            shifts = []
            for sh in dayd.get("shifts", []):
                slots_ok = [sl.get("name") for sl in sh.get("shift_slots", []) if (not sl.get("closed")) and (not sl.get("marked_as_full")) and pax in (sl.get("possible_guests") or [])]
                slots_wait = [sl.get("name") for sl in sh.get("shift_slots", []) if pax in (sl.get("waitlist_possible_guests") or []) and sl.get("name") not in slots_ok]
                comment = sh.get("comment"); 
                if isinstance(comment, dict): comment = comment.get("nl") or comment.get("en") or next(iter(comment.values()), None)
                shifts.append({"name": sh.get("name"), "open": sh.get("open"), "close": sh.get("close"), "marked_as_full": sh.get("marked_as_full"), "offer_required": sh.get("is_offer_required"), "prepayment": sh.get("prepayment_param"), "slots_for_pax": slots_ok, "waitlist_for_pax": slots_wait, "comment": (comment or "")[:300]})
            res["shifts"] = shifts
            res["bookable_slots"] = sorted({t for sh in shifts for t in sh["slots_for_pax"]})
        else:
            res["avail_error"] = f"{a.status_code} {a.text[:100]}"
            res["bookable_slots"] = sorted({sh["name"] for sh in res["summary_shifts"] if not sh["closed"] and pax in (sh["possible_guests"] or [])})
    except Exception as e:
        res["error"] = str(e)[:150]
    return res

def ft_to_zc(uid):
    try:
        r = get(f"https://widget-api.formitable.com/api/restaurant/{uid}/status", timeout=20)
        j = r.json() if r.text.startswith("{") else {}
        return {"uid": uid, "zenchefId": j.get("zenchefId"), "live": j.get("live"), "raw": {k: j.get(k) for k in ("zenchefId", "live", "name")}}
    except Exception as e:
        return {"uid": uid, "error": str(e)[:100]}

def bing(q, n=8):
    import base64
    r = get("https://www.bing.com/search?" + urllib.parse.urlencode({"q": q, "setlang": "nl", "cc": "NL"}), timeout=25)
    urls = []
    for m in re.finditer(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S):
        u = html.unescape(m.group(1)); t = re.sub(r'<[^>]+>', '', m.group(2))
        if "bing.com/ck/a" in u:
            mm = re.search(r'[?&]u=a1([A-Za-z0-9_-]+)', u)
            if mm:
                b = mm.group(1); b += "=" * (-len(b) % 4)
                try: u = base64.urlsafe_b64decode(b).decode("utf-8", "ignore")
                except Exception: pass
        if any(x in u for x in ("bing.com/", "tripadvisor", "yelp.", "facebook.com", "instagram.com", "restaurantguru", "michelin.com", "thefork", "opentable", "google.")):
            continue
        urls.append({"url": u, "title": html.unescape(t)})
        if len(urls) >= n: break
    return urls

def gp_check(key, date=DATE, pax=PAX):
    """Guestplan availability via etender-connect + api.guestplan.com (AccessKey auth)."""
    hdr = {**H, "Authorization": f"AccessKey {key}", "Content-Type": "application/json"}
    out = {"platform": "guestplan", "key": key, "restaurants": []}
    try:
        r = requests.get("https://etender-connect.com/v1/restaurants", headers=hdr, timeout=25, verify=False)
        rests = r.json() if r.text.startswith("[") else []
        if not rests: out["error"] = f"restaurants {r.status_code} {r.text[:100]}"
    except Exception as e:
        out["error"] = str(e)[:120]; return out
    for rest in rests:
        aid = rest.get("id")
        rec = {"accountId": aid, "name": rest.get("name"), "address": rest.get("address"), "city": rest.get("city"), "maxPartySize": rest.get("maxPartySize"), "widgetMessageClosed": (rest.get("settings") or {}).get("widgetMessageClosed")}
        try:
            sv = requests.get(f"https://etender-connect.com/v1/restaurants/{aid}/services?locale=nl", headers=hdr, timeout=25, verify=False)
            services = sv.json() if sv.text.startswith("[") else []
        except Exception: services = []
        rec["services"] = {str(x.get("id")): {"title": x.get("title"), "isRequired": x.get("isRequired"), "isPromoted": x.get("isPromoted"), "min": x.get("minPartySize"), "max": x.get("maxPartySize")} for x in services if not x.get("isDeleted")}
        try:
            a = requests.post("https://api.guestplan.com/api/v2/getAvailability", headers=hdr, json={"accountId": aid, "date": date.replace("-", ""), "partySize": pax}, timeout=30, verify=False)
            trs = (a.json() or {}).get("trs", []) if a.text.startswith("{") else []
            if not a.text.startswith("{"): rec["avail_error"] = f"{a.status_code} {a.text[:100]}"
        except Exception as e:
            trs = []; rec["avail_error"] = str(e)[:120]
        rec["slots_available"] = [t["t"] for t in trs if t.get("a")]
        rec["slots_waitlist"] = [t["t"] for t in trs if t.get("w") and not t.get("a")]
        rec["slot_services"] = {t["t"]: t.get("avs") for t in trs if t.get("a")}
        try:
            d = requests.get(f"https://etender-connect.com/v1/restaurants/{aid}/availability?date={date}&partySize={pax}", headers=hdr, timeout=25, verify=False)
            for day in (d.json() if d.text.startswith("[") else []):
                if day.get("localDate") == date: rec["day"] = {k: day.get(k) for k in ("isOpen", "isAvailable", "isAvailableWithWaitlist")}
        except Exception: pass
        out["restaurants"].append(rec)
    return out

def sr_check(venue, date=DATE, pax=PAX):
    """SevenRooms widget availability (public endpoint)."""
    mm, dd, yy = date[5:7], date[8:10], date[0:4]
    out = {"platform": "sevenrooms", "venue": venue, "shifts": []}
    try:
        url = f"https://www.sevenrooms.com/api-yoa/availability/widget/range?venue={venue}&time_slot=19:00&party_size={pax}&halo_size_interval=64&start_date={mm}-{dd}-{yy}&num_days=1&channel=SEVENROOMS_WIDGET&selected_lang_code=en"
        r = get(url, timeout=40)
        j = r.json()
        if j.get("status") != 200: out["error"] = str(j)[:200]; return out
        shifts = (j.get("data") or {}).get("availability", {}).get(date, [])
        for sh in shifts:
            times = sh.get("times") or []
            out["shifts"].append({"name": sh.get("name"), "category": sh.get("shift_category"), "is_closed": sh.get("is_closed"), "book_times": [t.get("time") for t in times if t.get("type") == "book"], "other_types": sorted({t.get("type") for t in times if t.get("type") != "book"}), "descriptions": sorted({t.get("public_time_slot_description") for t in times if t.get("type") == "book" and t.get("public_time_slot_description")})})
        out["bookable_slots"] = sorted({t for sh in out["shifts"] for t in sh["book_times"] if t})
        out["is_closed"] = all(sh.get("is_closed") for sh in shifts) if shifts else None
    except Exception as e:
        out["error"] = str(e)[:150]
    return out

def tebi_check(token, date=DATE, pax=PAX):
    """Tebi reservations-guest API. token = widget token (data-widget-token) or ledger token."""
    out = {"platform": "tebi", "widget_token": token}
    ledger = token
    try:
        r = requests.get(f"https://live.tebi.co/api/widget/{token}", headers=H, timeout=25, verify=False, allow_redirects=False)
        m = re.search(r'widget/([0-9]+_[0-9a-f]+)', r.headers.get("Location", ""))
        if m: ledger = m.group(1)
    except Exception as e:
        out["resolve_error"] = str(e)[:100]
    out["ledger"] = ledger
    hj = {**H, "Accept": "application/json"}
    base = f"https://live.tebi.co/api/reservations-guest/ledgers/{ledger}"
    try:
        sres = requests.get(f"{base}/reservation-settings", headers=hj, timeout=30, verify=False)
        sj = sres.json() if sres.text.startswith("{") else {}
        if "merchantName" not in sj:
            out["error"] = f"settings {sres.status_code} {sres.text[:120]}"; return out
        out["name"] = sj.get("merchantName")
        out["address"] = ", ".join(x for x in [sj.get("locationAddressLine1"), sj.get("locationAddressLine2"), sj.get("locationAddressLine3")] if x)
        out["minDate"], out["maxDate"], out["maxGroupSize"] = sj.get("minDate"), sj.get("maxDate"), sj.get("maxGroupSize")
        out["services"] = [{"id": x.get("id"), "name": x.get("name"), "prepayment_cents": (x.get("prepaymentPrice") or {}).get("minorUnits")} for x in sj.get("services", []) if not x.get("isArchived")]
        d = requests.get(f"{base}/reservation-dates/{date}?groupSize={pax}", headers=hj, timeout=30, verify=False)
        dj = d.json() if d.text.startswith("{") else {}
        ts = dj.get("timeslots", [])
        if not d.text.startswith("{"): out["dates_error"] = f"{d.status_code} {d.text[:120]}"
        out["slots_available"] = [t.get("time") for t in ts if t.get("availabilityType") == "Available"]
        out["slots_waitlist"] = [t.get("time") for t in ts if t.get("availabilityType") == "Waitlist"]
        out["slots_all"] = [(t.get("time"), t.get("availabilityType")) for t in ts]
        if not out["slots_available"] and out["services"]:
            per = {}
            for sv in out["services"][:8]:
                try:
                    dd = requests.get(f"{base}/reservation-dates/{date}?groupSize={pax}&serviceId={sv['id']}", headers=hj, timeout=30, verify=False)
                    tt = (dd.json() if dd.text.startswith("{") else {}).get("timeslots", [])
                    per[sv["name"]] = {"available": [t.get("time") for t in tt if t.get("availabilityType") == "Available"], "waitlist": [t.get("time") for t in tt if t.get("availabilityType") == "Waitlist"]}
                except Exception: pass
            out["slots_by_service"] = per
            out["slots_available"] = sorted({t for v in per.values() for t in v["available"]})
            if not out["slots_waitlist"]: out["slots_waitlist"] = sorted({t for v in per.values() for t in v["waitlist"]})
        try:
            ia = requests.get(f"{base}/initial-availability?groupSize={pax}", headers=hj, timeout=30, verify=False)
            for dd in (ia.json() if ia.text.startswith("{") else {}).get("dates", []):
                if dd.get("date") == date: out["day_availability"] = dd.get("availability")
        except Exception: pass
    except Exception as e:
        out["error"] = str(e)[:150]
    return out

def ft_check(uid, date=DATE, pax=PAX):
    """Formitable (non-migrated) widget API availability."""
    out = {"platform": "formitable", "uid": uid}
    st = ft_to_zc(uid); out["status_api"] = st
    if st.get("zenchefId"): out["zenchefId"] = st["zenchefId"]; return out
    out["live"] = st.get("live")
    B = "https://widget-api.formitable.com/api"
    try:
        info = get(f"{B}/restaurant/{uid}/nl", timeout=25)
        ij = info.json() if info.text.startswith("{") else {}
        out["name"] = ij.get("name"); out["address"] = ", ".join(x for x in [ij.get("streetAddress"), ij.get("city")] if x)
        out["maxPartySize"] = ij.get("maxPartySize")
        day = get(f"{B}/availability/{uid}/day/{date}/{pax}/nl", timeout=30)
        if day.status_code == 200 and day.text.startswith("["):
            dj = day.json()
            out["slots_available"] = [t.get("timeString") for t in dj if t.get("status") == "AVAILABLE"]
            out["slots_waitlist"] = [t.get("timeString") for t in dj if t.get("status") == "WAITLIST"]
            out["slots_all"] = [(t.get("timeString"), t.get("status")) for t in dj]
        else:
            out["day_error"] = f"{day.status_code} {day.text[:120]}"
        first = get(f"{B}/availability/{uid}/first/{pax}/{date}/nl", timeout=30)
        if first.status_code == 200 and first.text.startswith("{"):
            fj = first.json(); out["first"] = {"time": fj.get("time"), "timeString": fj.get("timeString"), "status": fj.get("status")}
        else:
            out["first_error"] = f"{first.status_code} {first.text[:120]}"
    except Exception as e:
        out["error"] = str(e)[:150]
    return out

def check(name, target, date=DATE, pax=PAX):
    rec = {"name": name, "target": target, "date": date, "pax": pax, "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    f = {}
    if ":" in target and target.split(":", 1)[0] in ("zc", "ft", "gp", "tebi", "sr"):
        k, v = target.split(":", 1)
        f = {{"zc": "zenchef", "ft": "formitable", "gp": "guestplan", "tebi": "tebi", "sr": "sevenrooms"}[k]: [v]}
    else:
        d = detect([target]); rec["detect"] = d; f = d["found"]
    rec["platforms"] = {k: v for k, v in f.items() if k != "restaurantbooking_generic"}
    rid = None
    def finish(status, slots, waitlist, info, used):
        rec["status"] = status; rec["slots"] = slots or []; rec["slots_waitlist"] = waitlist or []; rec["info"] = info; rec["used_platform"] = used
    done = False
    # 1) Zenchef direct
    if f.get("zenchef"):
        rid = f["zenchef"][0]
    # 2) Formitable -> Zenchef or Formitable-native
    if not rid and f.get("formitable"):
        for uid in f["formitable"]:
            fr = ft_check(uid, date, pax); rec.setdefault("formitable", []).append(fr)
            if fr.get("zenchefId"): rid = fr["zenchefId"]; break
            if fr.get("live") and (fr.get("slots_all") is not None or fr.get("first")):
                slots = fr.get("slots_available", []); wl = fr.get("slots_waitlist", [])
                first = fr.get("first") or {}
                if slots: st = "AVAILABLE"
                elif wl: st = "WAITLIST_ONLY"
                elif first.get("time") and not str(first["time"]).startswith(date): st = "NOT_AVAILABLE"
                else: st = "NOT_AVAILABLE"
                finish(st, slots, wl, {"name": fr.get("name"), "address": fr.get("address"), "first_available": first}, "formitable"); done = True; break
    if rid:
        rec["zenchef_rid"] = rid
        zi = zc_info(rid); rec["zc_info"] = zi
        av = zc_avail(rid, date, pax); rec["availability"] = av
        slots = av.get("bookable_slots", [])
        wl = sorted({t for sh in av.get("shifts", []) for t in sh.get("waitlist_for_pax", [])})
        st = "AVAILABLE" if slots else ("CLOSED" if av.get("isOpen") is False else ("WAITLIST_ONLY" if wl else "FULL_OR_NOT_BOOKABLE"))
        if av.get("error"): st = "ZENCHEF_ERROR"
        finish(st, slots, wl, {"name": zi.get("name"), "address": f"{zi.get('address')}, {zi.get('city')}"}, "zenchef"); done = True
    # 3) Tebi
    if not done and f.get("tebi"):
        for tok in f["tebi"]:
            tr = tebi_check(tok, date, pax); rec.setdefault("tebi", []).append(tr)
            if tr.get("name"):
                slots = tr.get("slots_available", []); wl = tr.get("slots_waitlist", [])
                st = "AVAILABLE" if slots else ("WAITLIST_ONLY" if wl else ("NOT_AVAILABLE" if tr.get("day_availability") in (None, "Unavailable") else "FULL_OR_NOT_BOOKABLE"))
                if tr.get("maxDate") and date > tr["maxDate"]: st = "DATE_NOT_YET_BOOKABLE"
                finish(st, slots, wl, {"name": tr.get("name"), "address": tr.get("address"), "services": tr.get("services"), "by_service": tr.get("slots_by_service"), "day_availability": tr.get("day_availability")}, "tebi"); done = True; break
    # 4) Guestplan
    if not done and f.get("guestplan"):
        for key in f["guestplan"]:
            g = gp_check(key, date, pax); rec.setdefault("guestplan", []).append(g)
            rs = g.get("restaurants", [])
            if not rs: continue
            pick = None
            for x in rs:
                if x.get("name") and name.lower().split()[0] in x["name"].lower(): pick = x; break
            if pick is None: pick = rs[0]
            slots = pick.get("slots_available", []); wl = pick.get("slots_waitlist", []); day = pick.get("day") or {}
            st = "AVAILABLE" if slots else ("CLOSED" if day.get("isOpen") is False else ("WAITLIST_ONLY" if wl else "FULL_OR_NOT_BOOKABLE"))
            finish(st, slots, wl, {"name": pick.get("name"), "address": f"{pick.get('address')}, {pick.get('city')}", "services": pick.get("services"), "day": day, "other_restaurants": [x.get("name") for x in rs if x is not pick]}, "guestplan"); done = True; break
    # 5) SevenRooms
    if not done and f.get("sevenrooms"):
        best = None
        for v in [v for v in f["sevenrooms"] if v not in ("embed", "widget", "reservations", "explore")]:
            srr = sr_check(v, date, pax); rec.setdefault("sevenrooms", []).append(srr)
            if best is None or srr.get("bookable_slots"): best = srr
            if srr.get("bookable_slots"): break
        if best:
            slots = best.get("bookable_slots", [])
            st = "AVAILABLE" if slots else ("CLOSED" if best.get("is_closed") or not best.get("shifts") else "FULL_OR_NOT_BOOKABLE")
            if best.get("error"): st = "SEVENROOMS_ERROR"
            finish(st, slots, [], {"name": best.get("venue"), "shifts": best.get("shifts")}, "sevenrooms"); done = True
    if not done:
        other = {k: v for k, v in rec["platforms"].items() if k not in ("zenchef", "formitable", "tebi", "guestplan", "sevenrooms")}
        finish("UNSUPPORTED_PLATFORM" if other else "NO_BOOKING_SYSTEM_FOUND", [], [], {"other_platforms": other}, None)
    with open(RESULTS, "a") as fh: fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    info = rec.get("info") or {}
    print(f"{name} | {rec['status']} | via={rec.get('used_platform')} | name={info.get('name')} ({info.get('address')}) | slots={rec.get('slots')} | waitlist={rec.get('slots_waitlist')} | platforms={rec.get('platforms')}")
    if rec.get("availability", {}).get("shifts"):
        for sh in rec["availability"]["shifts"]:
            print(f"   zc shift {sh['name']} {sh['open']}-{sh['close']} full={sh['marked_as_full']} offer_req={sh['offer_required']} slots={sh['slots_for_pax']} waitlist={sh['waitlist_for_pax']} prepay={sh['prepayment']}")
    if info.get("shifts"):
        for sh in info["shifts"]: print(f"   sr shift {sh['name']} ({sh['category']}) closed={sh['is_closed']} book={sh['book_times']} other={sh['other_types']} desc={sh['descriptions']}")
    if info.get("services") and isinstance(info["services"], dict):
        for sid, sv in info["services"].items(): print(f"   gp service {sid}: {sv.get('title')} required={sv.get('isRequired')} pax {sv.get('min')}-{sv.get('max')}")
    if info.get("services") and isinstance(info["services"], list):
        for sv in info["services"]: print(f"   tebi service: {sv.get('name')} prepay_cents={sv.get('prepayment_cents')}")
    if info.get("by_service"):
        for k, v in info["by_service"].items(): print(f"   tebi by service {k}: avail={v['available']} waitlist={v['waitlist']}")
    if info.get("first_available"): print(f"   ft first available: {info['first_available']}")
    return rec


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "detect": print(json.dumps(detect(sys.argv[2:]), indent=1, ensure_ascii=False))
    elif cmd == "zc":
        rid = sys.argv[2]; date = sys.argv[3] if len(sys.argv) > 3 else DATE; pax = int(sys.argv[4]) if len(sys.argv) > 4 else PAX
        print(json.dumps({"info": zc_info(rid), "availability": zc_avail(rid, date, pax)}, indent=1, ensure_ascii=False))
    elif cmd == "ft": print(json.dumps(ft_to_zc(sys.argv[2]), indent=1))
    elif cmd == "sr": print(json.dumps(sr_check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else DATE, int(sys.argv[4]) if len(sys.argv) > 4 else PAX), indent=1, ensure_ascii=False))
    elif cmd == "tebi": print(json.dumps(tebi_check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else DATE, int(sys.argv[4]) if len(sys.argv) > 4 else PAX), indent=1, ensure_ascii=False))
    elif cmd == "ftav": print(json.dumps(ft_check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else DATE, int(sys.argv[4]) if len(sys.argv) > 4 else PAX), indent=1, ensure_ascii=False))
    elif cmd == "gp": print(json.dumps(gp_check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else DATE, int(sys.argv[4]) if len(sys.argv) > 4 else PAX), indent=1, ensure_ascii=False))
    elif cmd == "bing": print(json.dumps(bing(sys.argv[2]), indent=1, ensure_ascii=False))
    elif cmd == "check":
        date = sys.argv[4] if len(sys.argv) > 4 else DATE; pax = int(sys.argv[5]) if len(sys.argv) > 5 else PAX
        check(sys.argv[2], sys.argv[3], date, pax)
    else: print(__doc__)
