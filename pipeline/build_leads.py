import json, re, math, unicodedata, hashlib, collections
exec(open("pipeline/geocode.py").read().split("if __name__")[0])
exec(open("pipeline/build_map.py").read().split("topo=json.load")[0].replace("import json, math, sys", ""))
exec(open("data/curated.py").read())
LAT0_DEG, LON0_DEG = 46.4367, 14.0526
exec(open("data/contacts.py").read())
exec(open("data/contacts_spec.py").read())
exec(open("data/manual_verify.py").read())
exec(open("data/qual.py").read())
import os
SIG = json.load(open("data/signals.json")) if os.path.exists("data/signals.json") else {}
WEBS = json.load(open("data/pn/websites.json")) if os.path.exists("data/pn/websites.json") else {}
VRES = {r["id"]: r for r in json.load(open("data/verify_out.json"))} if os.path.exists("data/verify_out.json") else {}
def _load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default
ADDR = _load("data/addr_fixes.json", {})      # naslovi, prebrani s spletnih strani
PLACES = _load("data/places.json", {})        # Google Places (če je ključ)
CHG = _load("data/lead_changes.json", {})     # zadnja sprememba po podjetju
REVIEWED = set(_load("data/reviewed.json", {}).get("ids", []))  # ročno pregledani 15. 10. 2026 (neocenjeni = P3)
import datetime
RUN_DATE = os.environ.get("RUN_DATE") or datetime.date.today().isoformat()
def sl_date(iso):
    y, m, d = iso.split("-"); return f"{int(d)}. {int(m)}. {y}"

def loc_geo(cc, q):
    k = q.replace(" ", "")
    if k.isdigit() and k in post.get(cc, {}):
        la, lo, nm = post[cc][k]; return la, lo, nm
    n = norm(q)
    if n in city.get(cc, {}):
        la, lo, nm, _ = city[cc][n]; return la, lo, nm
    return None

TYPES_SL = {
 "sailboats": "jadrnice", "powerboats": "motorni čolni", "sailing yachts": "jadralne jahte",
 "motor yachts/cabin boats": "motorne jahte", "sports boats/day cruisers": "športni čolni",
 "inflatables": "gumenjaki", "RIBs": "RIB", "electro/solar boats": "električni čolni",
 "fishing boats": "ribiški čolni", "work boats": "delovni čolni", "aluminium boats": "aluminijasti čolni",
 "sailing dinghies": "dingiji", "canoes/kayaks": "kanuji/kajaki", "small boats": "manjši čolni",
 "rowing boats": "čolni na vesla", "houseboats": "hišni čolni", "pontoon boats": "pontonski čolni",
 "passenger ships": "potniške ladje", "motor mega yachts": "megajahte", "catamarans": "katamarani",
 "sailing catamarans": "jadralni katamarani", "motor catamarans": "motorni katamarani",
 "motor sailers": "motorne jadrnice", "sailing wooden boats": "lesene jadrnice",
 "motor wooden boats": "leseni čolni", "custom built sailboats": "jadrnice po meri",
 "custom built powerboats": "motorni čolni po meri", "trimarans": "trimarani",
}
CORE = {"sailboats","powerboats","sailing yachts","motor yachts/cabin boats","sports boats/day cruisers","RIBs",
        "electro/solar boats","fishing boats","sailing dinghies","canoes/kayaks","catamarans","sailing catamarans",
        "motor catamarans","motor sailers","custom built sailboats","custom built powerboats","trimarans","small boats"}
SERVICE_RE = re.compile(r"service|servis|rimessaggio|winterlager|charter|holzboot|zillen|schreinerei|möbelbau|alu|jachtservice|werft gmbh & co", re.I)

leads = []
def add(**kw): leads.append(kw)

# 1) imenik izdelovalcev (profinautic)
for r in json.load(open("data/pn/geo.json")):
    if r["name"] in PN_DROP: continue
    ov = PN_OVERRIDE.get(r["name"], {})
    la, lo, place = r.get("lat"), r.get("lon"), ""
    if "loc" in ov:
        g = loc_geo(*ov["loc"])
        if g: la, lo, place = g
        else: print("NO GEO override", r["name"], ov["loc"])
    types = [t.strip() for t in r["types"].split(",") if t.strip()]
    fit = "A" if any(t in CORE for t in types) else "C"
    if SERVICE_RE.search(r["name"]): fit = "C"
    if types and all(t in ("motor mega yachts","passenger ships","work boats","aluminium boats") for t in types): fit = "C"
    fit = ov.get("fit", fit)
    tsl = ", ".join(TYPES_SL.get(t, t) for t in types)
    note = ov.get("note") or ""
    addr = r["addr"] if any(ch.isdigit() for ch in r["addr"]) or "," in r["addr"] else (place or "")
    web = WEBS.get(r["ct"] + "|" + r["name"], "")
    add(web=web, n=ov.get("name", r["name"]), cc=r["ct"], addr=addr, lat=la, lon=lo, seg=ov.get("seg","boats"), role="kupec",
        fit=fit, top=ov.get("top", False), note=note, types=tsl, models=r["models"] if r["models"] != r["name"] else "",
        src=["Imenik izdelovalcev (profinautic)"])

# 2) slovenski register SKD 30.120
SKIP_SKD = re.compile(r"PROFORM3D|SEALINE|QUADROFOIL|SACS S\.R\.L|SVP |5STORMS|VSR LAB|VIZINTIN|GX-SUPER|EXO BOAT|PEGASUS|GLORIUS|DARTH|EJET|GENLOG|ROTO NAUTICA|ORKA|DIDAS|ŠTIRJE|TUNE NAUTIC|INTERADRIA|NAVALIA|ORIOLI|ENERGY NAVAL|SIPABOARDS|OPHION|ANTEROS|BLUMAR|SEASCAPE")
def pretty(s):
    s = s.title()
    for a, b in ((" D.O.O.", " d.o.o."), ("D.O.O.", "d.o.o."), (" S.P.", " s.p."), (" D.N.O.", " d.n.o."), ("Gmbh", "GmbH"), (" In ", " in "), (" Za ", " za "), (" Ter ", " ter "), (" Pri ", " pri ")):
        s = s.replace(a, b)
    return s
for t in json.load(open("data/skd/all.json")):
    if SKIP_SKD.search(t): continue
    parts = [p.strip() for p in t.split(",")]
    pc = parts[-1]; street = parts[-2]; name = ", ".join(parts[:-2])
    m = re.match(r"(\d{4,5})\s+(.*)", pc)
    cc = "si" if m and len(m.group(1)) == 4 and not re.search(r"KASTAV|RIJEKA|OBROVAC|GRADAČAC|ZELTWEG|SCHATTENDORF|ZUG", pc) else None
    if re.search(r"RIJEKA|KASTAV|OBROVAC", pc): cc = "hr"
    if re.search(r"ZELTWEG|SCHATTENDORF", pc): cc = "at"
    if re.search(r"GRADAČAC", pc): cc = "ba"
    g = loc_geo(cc, m.group(1)) if (cc and m) else None
    if not g and cc and m: g = loc_geo(cc, m.group(2).split(" - ")[0])
    la, lo = (g[0], g[1]) if g else (None, None)
    if cc == "ba": la, lo = 44.88, 18.53
    U = t.upper()
    fit, note = "B", "Registrirana dejavnost: proizvodnja čolnov (SKD 30.120)."
    if re.search(r"GUMENJAK|GUMIJAST", U): fit, note = "C", "Gumenjaki – trup redko iz GRP."
    elif re.search(r"STORITVE|VZDRŽEVANJE|SERVIS|TEKSTILNI|SVETOVANJE|POPRAVAK|TRADING", U): fit, note = "C", "Pretežno storitve ali trgovina."
    elif re.search(r"LADIJ|GRADBENA", U): fit, note = "C", "Samostojni podjetnik – verjetno delo na ladjedelnicah v tujini. Nizka verjetnost."
    elif "MIZARSTVO" in U: fit, note = "C", "Mizarstvo – lesena plovila."
    elif "S.P." in U and re.search(r"BLED|BOHINJ|GORJE|ŽIROVNICA|BEGUNJE|JESENICE|BREZJE", U):
        fit, note = "C", "Manjši obrtnik na Gorenjskem – pletne/leseni čolni ali podizvajalec ladjedelnic v Begunjah."
    add(n=pretty(name), cc=cc or "si", addr=pretty(street + ", " + pc), lat=la, lon=lo, seg="boats",
        role="podizvajalec" if "podizvajalec" in note else "kupec", fit=fit, top=False, note=note, types="", models="",
        src=["Poslovni register SKD 30.120"])

# 3) OpenStreetMap (polmer 300 km)
for e in json.load(open("data/osm/boat300.json"))["elements"]:
    t = e.get("tags", {}); nm = t.get("name")
    if not nm or nm in ("Marine Interiors",): continue
    la = e.get("lat") or e.get("center", {}).get("lat"); lo = e.get("lon") or e.get("center", {}).get("lon")
    kind = t.get("craft") or t.get("industrial")
    fit = "B" if kind == "boatbuilder" else "C"
    note = "Ladjedelnica (OSM) – pretežno jeklo ali servis." if kind == "shipyard" else "Izdelovalec čolnov (OSM)."
    if re.search(r"rimessaggio|winterlager|schreinerei|manutenzione", nm, re.I): fit, note = "C", "Servis, zimovanje ali mizarstvo."
    if "Flyer" in nm: fit, note = "A", "Katamarani, Söchtenau (Bavarska)."
    if "Ferretti" in nm: fit, note = "B", "Ferretti Group, obrat Ravenna."
    addr = ", ".join(x for x in (t.get("addr:street",""), t.get("addr:city","")) if x)
    add(n=nm, cc=(t.get("addr:country") or "").lower(), addr=addr, lat=la, lon=lo, seg="boats", role="kupec", fit=fit, top=False,
        note=note, types="", models="", src=["OpenStreetMap"], web=t.get("website") or t.get("contact:website") or "")

# 4) ročno izbrani
for c in CURATED + SPEC:
    g = loc_geo(*c["loc"])
    if not g: print("NO GEO curated", c["name"], c["loc"])
    la, lo, place = g if g else (None, None, "")
    add(n=c["name"], cc=c["loc"][0], addr=c.get("city") or place.split(" - ")[0].split("/")[0], lat=la, lon=lo, seg=c["seg"], role=c["role"], fit=c["fit"], top=c.get("top", False),
        note=c["note"], types="", models="", src=["Ročno preverjeno"], cl=c.get("cl", []), web=c.get("web", ""))

# OSM country fix by nearest country is not needed for display; fill missing cc from coordinates roughly
for l in leads:
    if not l["cc"] and l["lat"]:
        la, lo = l["lat"], l["lon"]
        l["cc"] = "hr" if (lo > 13.5 and la < 45.5) else "at" if la > 46.6 and lo > 12.2 else "de" if la > 47.4 else "si" if lo > 13.6 else "it"

# deduplikacija
STOP = {"cantiere","cantieri","navali","navale","nautico","nautica","bootswerft","bootsbau","brodogradiliste","yachts","yacht","boats","boat",
        "marine","doo","d","o","srl","s","r","l","gmbh","the","group","co","kg","spa","proizvodnja","plovil","boote","werft","sp"}
def key(n):
    w = [x for x in norm(n).split() if x not in STOP and len(x) > 2]
    return w[0] if w else norm(n)
PRI = {"Ročno preverjeno": 0, "Imenik izdelovalcev (profinautic)": 1, "Poslovni register SKD 30.120": 2, "OpenStreetMap": 3}
def dist(a, b):
    if a["lat"] is None or b["lat"] is None: return 0 if a["cc"] == b["cc"] else 9999
    return hav(a["lat"], a["lon"], b["lat"], b["lon"])
leads.sort(key=lambda l: PRI[l["src"][0]])
merged = []
for l in leads:
    k = key(l["n"])
    for m in merged:
        if key(m["n"]) == k and dist(m, l) < 30:
            for s in l["src"]:
                if s not in m["src"]: m["src"].append(s)
            if m["lat"] is None and l["lat"] is not None: m["lat"], m["lon"] = l["lat"], l["lon"]
            if not m.get("web") and l.get("web"): m["web"] = l["web"]
            if not m["types"] and l["types"]: m["types"] = l["types"]
            break
    else:
        merged.append(l)

for l in merged:
    if l["n"] in LOC_FIX:
        cc, pc, town = LOC_FIX[l["n"]]; g = loc_geo(cc, pc)
        if g: l["lat"], l["lon"], l["addr"] = g[0], g[1], town
        else: print("NO GEO locfix", l["n"])
for l in merged:
    lid = hashlib.md5((l["n"] + "|" + l["src"][0]).encode()).hexdigest()[:10]
    a = ADDR.get(lid)
    if l["lat"] is None and a:
        l["lat"], l["lon"], l["addr"] = a["lat"], a["lon"], a["town"]
        l["src"] = l["src"] + ["Naslov s spletne strani"]
    p = PLACES.get(lid)
    if p and p.get("ok"):
        if l["lat"] is None and p.get("lat") is not None:
            l["lat"], l["lon"], l["addr"] = p["lat"], p["lon"], p.get("addr", "")
            l["src"] = l["src"] + ["Google Places"]
        if not l.get("web") and p.get("web"): l["web"] = p["web"]
RINGS = [(150, 0), (400, 1), (700, 2), (1000, 3)]
FITW = {"A": 3, "B": 2, "C": 0.6}; RINGW = [1.0, 0.75, 0.5, 0.35, 0.3]
out = []
for l in merged:
    if l["lat"] is not None:
        km = round(hav(LAT0_DEG, LON0_DEG, l["lat"], l["lon"]))
        if km > 1000: continue
        ring = next(r for lim, r in RINGS if km <= lim)
        x, y = proj(l["lon"], l["lat"])
    else:
        if l["cc"] in ("fr","nl","be","dk","mc"): continue
        km, ring, x, y = None, 4, None, None
    sc = FITW[l["fit"]] * RINGW[ring] + (1.5 if l["top"] else 0)
    lid = hashlib.md5((l["n"] + "|" + l["src"][0]).encode()).hexdigest()[:10]
    out.append(dict(id=lid, n=l["n"], cc=l["cc"], a=l["addr"], km=km, r=ring,
                    x=None if x is None else round(x, 1), y=None if y is None else round(y, 1),
                    s=l["seg"], ro=l["role"], f=l["fit"], t=1 if l["top"] else 0, no=l["note"], ty=l["types"], mo=l["models"][:120],
                    w=l.get("web", ""), src=l["src"], sc=round(sc, 2)))
names = {o["n"] for o in out}
for k in list(CONTACTS) + list(NOTE_FIX):
    if k not in names: print("MISSING NAME", k)
for o in out:
    if o["n"] in NOTE_FIX:
        for a, b in NOTE_FIX[o["n"]].items(): o[a] = b
        o["sc"] = round(FITW[o["f"]] * RINGW[o["r"]] + (1.5 if o["t"] else 0), 2)
    if o["n"] in DESIGNERS: o["pr"] = DESIGNERS[o["n"]]
    if o["n"] in CONTACTS:
        c = dict(CONTACTS[o["n"]]); c.setdefault("d", D); o["ct"] = c
for o in out:
    r = VRES.get(o["id"]); mv = MANUAL_V.get(o["n"])
    vf = None
    if r: vf = dict(v=r["v"], u=r.get("u", ""), ev=r.get("ev", []), neg=r.get("neg", []), d="14. 10. 2026")
    if r and r.get("mix") and vf: vf["mix"] = 1
    if mv and (not vf or mv[2] or vf["v"] in ("N", "X", "D", "m")):
        vf = dict(v=mv[0], u=(vf or {}).get("u") or (o.get("ct") or {}).get("w", "") or o.get("w", ""), ev=[["ročno preverjeno", mv[1]]], neg=[], d="11.–14. 10. 2026", man=1)
    if vf:
        o["vf"] = vf
        if vf["v"] in ("T", "S") and not o["t"]: o["f"] = "C"
        bonus = {"M": 0.8, "m": 0.3}.get(vf["v"], 0)
        o["sc"] = round(FITW[o["f"]] * RINGW[o["r"]] + (1.5 if o["t"] else 0) + bonus, 2)
TL = {"1": "P1", "2": "P2", "3": "P3", "K": "K"}
for o in out:
    q = Q.get(o["n"])
    if q:
        o["q"] = dict(t=q[0], sz=q[1], why=q[2], ap=q[3])
    elif o["id"] in SIG:
        g = SIG[o["id"]]; v = (o.get("vf") or {}).get("v")
        if v in ("D", "X") or g["chars"] < 400: why = "Spletna stran ne deluje ali je prazna."
        elif g["wood"] > max(3, g["grp"]): why = "Pretežno lesena plovila."
        elif g["alu"] > max(3, g["grp"]): why = "Pretežno aluminijasta plovila."
        elif g["rib"] > max(5, g["grp"] * 2): why = "Pretežno gumenjaki."
        elif v in ("M", "m") and o["id"] not in REVIEWED:
            sz = "?"
            if g.get("emp"):
                e = max(g["emp"]); sz = "mikro" if e < 10 else "majhno" if e < 50 else "srednje" if e < 250 else "veliko"
            o["q"] = dict(t="2", sz=sz, why="Samodejno: na spletni strani so dokazi o proizvodnji" + (" (" + ", ".join(k for k, _ in (o.get("vf") or {}).get("ev", [])[:3]) + ")" if (o.get("vf") or {}).get("ev") else "") + ". Ročna ocena še manjka.", ap="Preglej stran in oceni ročno.", auto=1)
            why = None
        else: why = "Po pregledu strani: servis, trgovina, popravila ali velike jeklene ladje – ni primeren profil."
        if why: o["q"] = dict(t="3", sz="?", why=why, ap="", auto=1)
    if o.get("q"):
        o["sc"] = round(o["sc"] + TIER_SCORE[o["q"]["t"]], 2)
AC = json.load(open("data/autocontacts.json")) if os.path.exists("data/autocontacts.json") else {}
for o in out:
    if o.get("ct") or (o.get("q") or {}).get("t") not in ("1", "2", "K"): continue
    a = AC.get(o["id"])
    if a: o["ct"] = dict(w=a["w"], e=a["e"], p=a["p"], d=sl_date(a.get("d", RUN_DATE)), n="Splošni kontakt s spletne strani podjetja (samodejno). Imena oseb poišči v nakupni skupini.")
for o in out:
    p = PLACES.get(o["id"])
    if p and p.get("ok"):
        if p.get("status") == "CLOSED_PERMANENTLY":
            o["q"] = dict(t="3", sz=(o.get("q") or {}).get("sz", "?"), why="Google Places: podjetje je trajno zaprto.", ap="")
        if not o.get("ct") and (p.get("phone") or p.get("web")) and (o.get("q") or {}).get("t") in ("1", "2", "K"):
            o["ct"] = dict(w=p.get("web", ""), e=[], p=[p["phone"]] if p.get("phone") else [], d=sl_date(p.get("d", RUN_DATE)), n="Kontakt iz Google Places.")
    if o["id"] in CHG: o["ch"] = CHG[o["id"]]
missing = [k for k in Q if k not in names]
if missing: print("Q MISSING", missing)
rev = {}
for b, lst in DESIGNERS.items():
    for _, _, spec in lst:
        if spec and b in names: rev.setdefault(spec, []).append(b)
src_cl = {l["n"]: l.get("cl", []) for l in merged}
for o in out:
    if o["s"] == "spec":
        cl = sorted(set(rev.get(o["n"], [])))
        cl += [x for x in src_cl.get(o["n"], []) if x not in cl]
        if cl: o["cl"] = cl
        o["sc"] = round(o["sc"] + (1.0 if o["n"] in rev else 0), 2)
out.sort(key=lambda o: (-o["sc"], o["km"] if o["km"] is not None else 9999))
assert len({o["id"] for o in out}) == len(out)
json.dump(out, open("docs/leads.json", "w"), ensure_ascii=False, separators=(",", ":"))
_q = collections.Counter((o.get("q") or {}).get("t", "-") for o in out)
json.dump(dict(built=RUN_DATE, built_sl=sl_date(RUN_DATE), n=len(out), p1=_q["1"], p2=_q["2"], k=_q["K"],
               web=sum(1 for o in out if o.get("w") or (o.get("ct") or {}).get("w")), noloc=sum(1 for o in out if o["km"] is None)),
          open("docs/meta.json", "w"), ensure_ascii=False)
c = collections.Counter
print("skupaj", len(out))
print("po segmentu", c(o["s"] for o in out))
print("po krogu", sorted(c(o["r"] for o in out).items()))
print("po primernosti", c(o["f"] for o in out))
print("izbrani", sum(o["t"] for o in out))
from collections import Counter as _C
print("preverjanje", _C((o.get("vf") or {}).get("v","-") for o in out))
print("s spletno stranjo", sum(1 for o in out if o.get("w") or (o.get("ct") or {}).get("w")))
print("prednost", _C((o.get("q") or {}).get("t","-") for o in out))
print("s kontakti", sum(1 for o in out if o.get("ct")))
print("brez lokacije", sum(1 for o in out if o["km"] is None))
for o in out[:40]: print(o["sc"], o["km"], o["f"], o["s"], o["n"], "|", o["a"])
