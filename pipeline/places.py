"""Dopolnitev manjkajočih spletnih strani in lokacij z Google Places API (Text Search, New).
Teče samo, če je nastavljena spremenljivka GOOGLE_MAPS_API_KEY (v GitHub: Settings → Secrets → Actions).
Rezultati se hranijo v data/places.json, zato vsako podjetje poizvemo le enkrat.
Strošek: Text Search s spletno stranjo in telefonom je ~0,035 $ na poizvedbo (glej cenik Google Maps Platform)."""
import json, os, re, subprocess, sys, unicodedata, datetime

KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
MAX = int(os.environ.get("PLACES_MAX", "200"))
RUN_DATE = os.environ.get("RUN_DATE") or datetime.date.today().isoformat()
CC_NAME = {"si": "Slovenija", "hr": "Hrvatska", "it": "Italia", "at": "Österreich", "de": "Deutschland", "ch": "Schweiz",
           "hu": "Magyarország", "cz": "Česko", "sk": "Slovensko", "pl": "Polska", "ba": "Bosna i Hercegovina"}
FIELDS = "places.id,places.displayName,places.formattedAddress,places.location,places.websiteUri,places.internationalPhoneNumber,places.businessStatus,places.addressComponents"
STOP = {"srl", "s.r.l.", "spa", "d.o.o.", "doo", "gmbh", "ag", "kg", "co", "s.p.", "sp", "cantiere", "cantieri", "navale", "navali",
        "nautico", "bootswerft", "werft", "yachts", "yacht", "boats", "boat", "marine", "brodogradiliste", "proizvodnja", "plovil", "the", "&"}

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return [w for w in re.findall(r"[a-z0-9]+", s) if w not in STOP and len(w) > 1]

def similar(a, b):
    A, B = set(norm(a)), set(norm(b))
    if not A or not B: return 0
    return len(A & B) / min(len(A), len(B))

def search(o):
    q = " ".join(x for x in (o["n"], o.get("a", ""), CC_NAME.get(o["cc"], "")) if x)
    body = json.dumps({"textQuery": q, "regionCode": o["cc"].upper() if len(o["cc"]) == 2 else None, "maxResultCount": 3})
    r = subprocess.run(["curl", "-s", "-m", "30", "-X", "POST", "https://places.googleapis.com/v1/places:searchText",
                        "-H", "Content-Type: application/json", "-H", "X-Goog-Api-Key: " + KEY, "-H", "X-Goog-FieldMask: " + FIELDS,
                        "-d", body], capture_output=True)
    try: return q, json.loads(r.stdout.decode("utf-8", "ignore"))
    except Exception: return q, {}

def pick(o, res):
    for p in res.get("places", []):
        name = (p.get("displayName") or {}).get("text", "")
        ccs = [c.get("shortText", "").lower() for c in p.get("addressComponents", []) if "country" in c.get("types", [])]
        if ccs and o["cc"] and ccs[0] != o["cc"]: continue
        if similar(o["n"], name) >= 0.5:
            loc = p.get("location") or {}
            return dict(ok=1, name=name, addr=p.get("formattedAddress", ""), lat=loc.get("latitude"), lon=loc.get("longitude"),
                        web=p.get("websiteUri", ""), phone=p.get("internationalPhoneNumber", ""), status=p.get("businessStatus", ""),
                        pid=p.get("id", ""), d=RUN_DATE)
    return dict(ok=0, d=RUN_DATE)

if __name__ == "__main__":
    if not KEY:
        print("GOOGLE_MAPS_API_KEY ni nastavljen – preskakujem Google Places."); sys.exit(0)
    leads = json.load(open("docs/leads.json"))
    cache = json.load(open("data/places.json")) if os.path.exists("data/places.json") else {}
    def want(o):
        if o["id"] in cache or o["s"] == "spec": return False
        noweb = not (o.get("w") or (o.get("ct") or {}).get("w"))
        t = (o.get("q") or {}).get("t")
        if t == "3": return False
        return (noweb or o["km"] is None) and (t in ("1", "2", "K") or o["f"] in ("A", "B"))
    todo = sorted([o for o in leads if want(o)], key=lambda o: -o["sc"])[:MAX]
    for o in todo:
        q, res = search(o)
        if res.get("error"): print("NAPAKA:", res["error"].get("message", "")[:200]); break
        r = pick(o, res); r["q"] = q; cache[o["id"]] = r
    json.dump(cache, open("data/places.json", "w"), ensure_ascii=False, indent=0)
    print(f"Google Places: poizvedb {len(todo)}, ujemanj {sum(1 for o in todo if cache.get(o['id'], {}).get('ok'))}")
