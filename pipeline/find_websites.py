"""Poišče spletne strani za podjetja brez strani: najprej ročno znani naslovi (data/web_manual.json),
nato očitne domene (ime podjetja + končnica države). Stran sprejme samo, če se odpre, ni parkirana
in omenja ime podjetja ter dejavnost. Rezultat: data/web_found.json (id -> url, način, datum)."""
import json, os, re, sys, unicodedata, datetime, concurrent.futures as cf
exec(open("pipeline/verify.py").read().split('\nif __name__ == "__main__":')[0])

RUN_DATE = os.environ.get("RUN_DATE") or datetime.date.today().isoformat()
LEGAL = {"srl", "spa", "doo", "dd", "gmbh", "ag", "kg", "co", "sp", "snc", "sas", "kft", "sro", "bv", "sa", "sarl", "ltd", "llc",
         "inh", "eg", "zoo", "z", "o", "d", "s", "r", "l", "e", "di", "de", "der", "und", "and", "the", "&", "c", "a"}
GENERIC = {"cantiere", "cantieri", "navale", "navali", "nautico", "nautica", "bootswerft", "werft", "bootsbau", "yachts", "yacht",
           "boats", "boat", "boote", "marine", "brodogradiliste", "proizvodnja", "plovil", "stocznia", "jachty", "jachtowa",
           "yachtbau", "shipyard", "group", "international", "italia", "italy"}
TLD = {"it": ["it", "com"], "de": ["de", "com"], "at": ["at", "com"], "ch": ["ch", "com"], "si": ["si", "com"], "hr": ["hr", "com"],
       "pl": ["pl", "com"], "cz": ["cz", "com"], "sk": ["sk", "com"], "hu": ["hu", "com"], "nl": ["nl", "com"], "fr": ["fr", "com"],
       "be": ["be", "com"], "ba": ["ba", "com"]}
ACTIVITY = re.compile(r"barc|boat|yacht|boot|čoln|coln|brod|plovil|vetroresin|gfk|grp|cantier|werft|nautic|jacht|łód|lodz|hajó|lod|"
                      r"kompozit|composit|livar|foundr|gieß|aircraft|flugzeug|letal|caravan|wohnmobil|kajak|kanu|segel|vela|jadr", re.I)

def words(name):
    s = unicodedata.normalize("NFKD", re.sub(r"\(.*?\)", " ", name)).encode("ascii", "ignore").decode().lower()
    return [w for w in re.findall(r"[a-z0-9]+", s) if w not in LEGAL]

def candidates(o):
    w = words(o["n"]); dist = [x for x in w if x not in GENERIC and len(x) > 2]
    if not dist: return []
    stems = []
    for s in ["".join(w), "-".join(w), "".join(dist), "-".join(dist), dist[0] + "yachts", dist[0] + "boats", dist[0] + "marine",
              "cantiere" + dist[0], "cantieri" + dist[0], dist[0] + "-yachts", dist[0]]:
        if 3 < len(s) <= 40 and s not in stems: stems.append(s)
    out = []
    for s in stems[:9]:
        for t in TLD.get(o["cc"], ["com"]):
            out.append(f"https://www.{s}.{t}/")
    return out

REJECTED = json.load(open("data/web_rejected.json")) if os.path.exists("data/web_rejected.json") else {}
def accept(o, url):
    if REJECTED.get(o["id"], "").rstrip("/") == url.rstrip("/"): return None
    h, final = fetch(url)
    if re.search(r"dynadot|forsale|sedo\.com|afternic|hugedomains", final, re.I): return None
    if REJECTED.get(o["id"], "").split("//")[-1].split("/")[0] == final.split("//")[-1].split("/")[0]: return None
    t = text_of(h)
    if len(t) < 300 or parked(t): return None
    low = unicodedata.normalize("NFKD", t[:20000]).encode("ascii", "ignore").decode().lower()
    dist = [x for x in words(o["n"]) if x not in GENERIC and len(x) > 2]
    if not dist or not all(x in low for x in dist[:2]): return None
    if not ACTIVITY.search(t[:20000]): return None
    return final

def search(o):
    for u in candidates(o):
        r = accept(o, u)
        if r: return r
    return None

if __name__ == "__main__":
    leads = json.load(open("docs/leads.json"))
    found = json.load(open("data/web_found.json")) if os.path.exists("data/web_found.json") else {}
    manual = json.load(open("data/web_manual.json")) if os.path.exists("data/web_manual.json") else {}
    web = lambda o: (o.get("vf") or {}).get("u") or (o.get("ct") or {}).get("w") or o.get("w")
    miss = [o for o in leads if not web(o) and o["id"] not in found and o["s"] != "spec"]
    for o in miss:                                   # 1) ročno znani naslovi (preverjeni)
        u = manual.get(o["n"])
        if u:
            r = accept(o, u) or (u if "--trust" in sys.argv else None)
            if r: found[o["id"]] = dict(url=r, how="ročno", d=RUN_DATE)
    rest = [o for o in miss if o["id"] not in found and "--guess" in sys.argv]
    with cf.ThreadPoolExecutor(8) as ex:             # 2) očitne domene
        for o, r in zip(rest, ex.map(search, rest)):
            if r: found[o["id"]] = dict(url=r, how="domena", d=RUN_DATE)
    json.dump(found, open("data/web_found.json", "w"), ensure_ascii=False, indent=0)
    still = [o for o in leads if not web(o) and o["id"] not in found and o["s"] != "spec"]
    json.dump([dict(id=o["id"], n=o["n"], a=o["a"], cc=o["cc"], km=o["km"], src=o["src"][0]) for o in still],
              open("data/web_missing.json", "w"), ensure_ascii=False, indent=0)
    print(f"najdenih skupaj {len(found)}, še brez strani {len(still)}")
