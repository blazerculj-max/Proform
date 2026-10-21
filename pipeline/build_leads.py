import json, re, math, unicodedata, hashlib, collections
exec(open("pipeline/geocode.py").read().split("if __name__")[0])
exec(open("pipeline/build_map.py").read().split("topo=json.load")[0].replace("import json, math, sys", ""))
exec(open("data/curated.py").read())
LAT0_DEG, LON0_DEG = 46.4367, 14.0526
exec(open("data/contacts.py").read())
exec(open("data/contacts_spec.py").read())
exec(open("data/manual_verify.py").read())
exec(open("data/qual.py").read())
exec(open("data/fair_review.py").read())
import os
SIG = json.load(open("data/signals.json")) if os.path.exists("data/signals.json") else {}
WEBS = json.load(open("data/pn/websites.json")) if os.path.exists("data/pn/websites.json") else {}
VRES = {r["id"]: r for r in json.load(open("data/verify_out.json"))} if os.path.exists("data/verify_out.json") else {}
def _load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default
ADDR = _load("data/addr_fixes.json", {})      # naslovi, prebrani s spletnih strani
PLACES = _load("data/places.json", {})        # Google Places (če je ključ)
WEBF = _load("data/web_found.json", {})       # ročno najdene in preverjene spletne strani
WNOTES = _load("data/web_notes.json", {})     # ugotovitve iskanja (ne obstaja več, prodajalec …)
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

# 5) razstavljavci na sejmih (pipeline/fairs.py pick): obstoječim doda sejem, novo podjetje le, če stran kaže proizvodnjo
FAIR_TAG = {}
for c in _load("data/fairs/cand.json", []):
    if c["n"] in FAIR_DROP: continue
    if c["n"] in FAIR_ALIAS:
        FAIR_TAG.setdefault(FAIR_ALIAS[c["n"]], []).append(c["fair"] + (" · " + c["where"] if c["where"] else "")); continue
    br = ", ".join(b for b in c.get("brands", []) if norm(b) not in norm(c["n"]))
    add(n=c["n"], cc=c["cc"], addr=c["city"], lat=c["lat"], lon=c["lon"], seg="boats", role="kupec", fit="A" if c.get("v") == "M" else "B", top=False, tok=True,
        note=f"Na sejmu predstavlja znamke: {br}." if br else "",
        types="", models="", src=[c["src"]], web=c.get("u") or c["web"], fairs=[c["fair"] + (" · " + c["where"] if c["where"] else "")],
        fkeep=c.get("v") in ("M", "m"), fct=(c["email"], c.get("phone", ""), c["fair"]) if c.get("email") else None)  # samo splošni naslovi (fairs.py)

# 6) poslovni registri in imeniki (pipeline/registers.py): obstoječim doda število zaposlenih,
#    novo podjetje doda le, če ima do 49 zaposlenih ali je velikost neznana (naročnik išče podjetja z 10–50 zaposlenimi)
import glob
REG_SKIP = set(_load("data/reg_review.json", {}).get("drop", []))
REG_ALIAS = _load("data/reg_review.json", {}).get("alias", {})
REV_SIZE = {"0-1 milioni": "mikro", "1-2 milioni": "majhno", "2-5 milioni": "majhno", "5-10 milioni": "majhno", "10-25 milioni": "srednje",
            "25-50 milioni": "srednje", "50-100 milioni": "veliko", "100-500 milioni": "veliko", ">500 milioni": "veliko"}
def pretty_reg(n):
    n = re.sub(r"\s+", " ", n).strip()
    if not n.isupper(): return n
    n = n.title()
    for a, b in ((" S.R.L.", " S.r.l."), (" Srl", " S.r.l."), (" S.P.A.", " S.p.A."), (" Spa", " S.p.A."), (" S.N.C.", " S.n.c."), (" Snc", " S.n.c."),
                 (" S.A.S.", " S.a.s."), (" Sas", " SAS"), (" Sarl", " SARL"), (" S.R.O.", " s.r.o."), (" D.O.O.", " d.o.o."), (" Gmbh", " GmbH"), (" Di ", " di "),
                 (" E ", " e "), (" Del ", " del "), (" Della ", " della "), (" De ", " de "), (" Des ", " des "), (" Et ", " et ")):
        n = n.replace(a, b)
    return n
for f in sorted(glob.glob("data/reg/*.json")):
    for r in json.load(open(f)):
        if r["src"].startswith("Register podjetij") and r.get("empr") in ("", "0"): continue  # brez zaposlenih: samostojni, holdingi, mirujoča
        if r.get("emp") is not None and r["emp"] < 1: continue
        if r.get("prevail") and not str(r["prevail"]).startswith("30"): continue  # ARES: prevladujoča dejavnost ni proizvodnja plovil/letal
        if r["src"].startswith("CompanyWall") and r.get("emp") is None and re.search(r"\bs\.\s?p\.|\bobrt\b", r["n"], re.I): continue  # samostojni podjetniki brez zaposlenih
        nm = pretty_reg(r["n"])
        if nm in REG_SKIP: continue
        if re.search(r"liquidaz|liquidation|stečaj|stecaj|insolven|in konkurs|v likvidaci|u likvidaciji", nm, re.I): continue  # v likvidaciji ali stečaju
        if nm in REG_ALIAS: nm, r = REG_ALIAS[nm], dict(r, lat=None, lon=None)  # isto podjetje kot obstoječe (drugačno ime ali sedež)
        seg = r.get("seg") or ("aero" if re.match(r"30\.?30", r.get("nace", "")) else "boats")
        if seg == "aero" and re.search(r"DRONE|UAS\b|INFORMAT|SOFTWARE|SYSTEM|ELECTRONI|ADDITIVE|TURBO|SPATIAL|SATELL|ROBOT|MAINTENANCE|\bIT\b", nm.upper()):
            continue  # letalstvo: samo izdelovalci letal in delov, ne droni, programska oprema, elektronika
        if r.get("rev"): r = dict(r, rev=r["rev"].replace("\xa0", " ").strip())
        if r["sz"] == "?" and r.get("rev") in REV_SIZE:  # Italija brez podatka o zaposlenih: ocena po prometu iz istega registra
            r = dict(r, sz=REV_SIZE[r["rev"]], empr="", src_sz=r["src"] + ", ocena po prometu " + r["rev"].replace("milioni", "mio €"))
        size = dict(c=r["sz"], t=r.get("empr", ""), s=r.get("src_sz", r["src"]), u=r.get("url", "")) if r["sz"] != "?" else None
        note = f"Registrirana dejavnost: {r['act']}." + (" Učni obrat (Lehrbetrieb) – ima zaposlene." if r.get("lehr") else "")
        add(n=nm, cc=r["cc"], addr=r.get("city", ""), lat=r.get("lat"), lon=r.get("lon"), seg=seg, role="kupec", fit="B", top=False, note=note,
            types="", models="", src=[r["src"]], web=r.get("web", "").strip(), tok=True, size=size, regnew=r["sz"] in ("mikro", "majhno", "?"),
            rphone=(r.get("phone", ""), r["src"]) if r.get("phone") else None, su={r["src"]: r["url"]} if r.get("url") else {})

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
leads.sort(key=lambda l: PRI.get(l["src"][0], 4))
SZ_RANK = {"mikro": 1, "majhno": 2, "srednje": 3, "veliko": 4}
FSTOP = STOP | {"del", "della", "delle", "dei", "der", "die", "und", "and", "van", "yachtbau", "bootswerft", "bootsbau", "shipyard", "srls", "spa", "bv", "sas"}
def toks(n): return {x for x in norm(n).split() if x not in FSTOP and len(x) > 2}
def same(fair, a, b):
    if not fair: return key(a) == key(b)
    ov = toks(a) & toks(b)  # razstavljavci: vsaj dve skupni besedi (ali vse, če jih ima ime manj)
    return bool(ov) and len(ov) >= min(2, len(toks(a)), len(toks(b)))
merged = []
for l in leads:
    k = key(l["n"]); tok = l.get("tok")
    for m in merged:
        if same(tok or m.get("tok"), l["n"], m["n"]) and dist(m, l) < (60 if l.get("size") is not None or l.get("regnew") is not None else 30):
            for s in l["src"]:
                if s not in m["src"]: m["src"].append(s)
            if m["lat"] is None and l["lat"] is not None: m["lat"], m["lon"] = l["lat"], l["lon"]
            if not m.get("web") and l.get("web"): m["web"] = l["web"]
            if not m["types"] and l["types"]: m["types"] = l["types"]
            if l.get("fairs"): m["fairs"] = m.get("fairs", []) + [f for f in l["fairs"] if f not in m.get("fairs", [])]
            if l.get("fkeep"): m["fkeep"] = True
            if l.get("fct") and not m.get("fct"): m["fct"] = l["fct"]
            if l.get("size") and (not m.get("size") or SZ_RANK[l["size"]["c"]] > SZ_RANK[m["size"]["c"]]):
                m["size"] = l["size"]  # več vpisov z istim imenom (npr. mirujoča družba in delujoča): velja večji
            if l.get("regnew"): m["regnew"] = True
            if l.get("rphone") and not m.get("rphone"): m["rphone"] = l["rphone"]
            if l.get("su"): m["su"] = {**l["su"], **m.get("su", {})}  # povezava na vpis v registru ali imeniku
            break
    else:
        merged.append(l)

REG_SRC = ("Registro Imprese", "Register podjetij", "WKO Firmen", "Gelbe Seiten", "CompanyWall", "Schweizerischer Bootbauer")
merged = [l for l in merged if not l["src"][0].startswith("Sejem ") or l.get("fkeep")]
merged = [l for l in merged if not l["src"][0].startswith(REG_SRC) or l.get("regnew")]
def fair_labels(lst):  # en zapis na sejem: »Genova 2026 · Motor boats, Inflatable Boats«
    g = {}
    for f in lst:
        name, _, where = f.partition(" · ")
        w = g.setdefault(name, [])
        for x in re.split(r",\s*", where):
            if x.strip() and x.strip() not in w: w.append(x.strip())
    return [n + (" · " + ", ".join(w) if w else "") for n, w in g.items()]
for l in merged:
    if l["n"] in FAIR_TAG: l["fairs"] = l.get("fairs", []) + FAIR_TAG[l["n"]]
    if l.get("fairs"):
        l["fairs"] = fair_labels(l["fairs"])
        sl = {f.split(" · ")[0].split()[0] for f in l["fairs"]}
        for lab, src in (("boot", "Sejem boot Düsseldorf"), ("Genova", "Sejem Salone Nautico Genova")):
            if lab in sl and src not in l["src"]: l["src"] = l["src"] + [src]
_ids = set()
for l in merged:  # id = ime + prvi vir; pri enakem imenu iz istega vira (npr. dve podružnici) še kraj
    lid = hashlib.md5((l["n"] + "|" + l["src"][0]).encode()).hexdigest()[:10]
    if lid in _ids: lid = hashlib.md5((l["n"] + "|" + l["src"][0] + "|" + (l.get("addr") or "")).encode()).hexdigest()[:10]
    _ids.add(lid); l["lid"] = lid
for l in merged:
    if l["n"] in LOC_FIX:
        cc, pc, town = LOC_FIX[l["n"]]; g = loc_geo(cc, pc)
        if g: l["lat"], l["lon"], l["addr"] = g[0], g[1], town
        else: print("NO GEO locfix", l["n"])
for l in merged:
    lid = l["lid"]
    a = ADDR.get(lid)
    if l["lat"] is None and a:
        l["lat"], l["lon"], l["addr"] = a["lat"], a["lon"], a["town"]
        l["src"] = l["src"] + ["Naslov s spletne strani"]
    if not l.get("web") and lid in WEBF: l["web"] = WEBF[lid]["url"]
    p = PLACES.get(lid)
    if p and p.get("ok"):
        if l["lat"] is None and p.get("lat") is not None:
            l["lat"], l["lon"], l["addr"] = p["lat"], p["lon"], p.get("addr", "")
            l["src"] = l["src"] + ["Google Places"]
        if not l.get("web") and p.get("web"): l["web"] = p["web"]
FCT, RPH = {}, {}
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
    lid = l["lid"]
    out.append(dict(id=lid, n=l["n"], cc=l["cc"], a=l["addr"], km=km, r=ring,
                    x=None if x is None else round(x, 1), y=None if y is None else round(y, 1),
                    s=l["seg"], ro=l["role"], f=l["fit"], t=1 if l["top"] else 0, no=l["note"], ty=l["types"], mo=l["models"][:120],
                    w=l.get("web", ""), src=l["src"], sc=round(sc, 2)))
    if l.get("fairs"): out[-1]["fa"] = l["fairs"]
    if l.get("fct"): FCT[lid] = l["fct"]
    if l.get("size"): out[-1]["zp"] = l["size"]
    if l.get("rphone"): RPH[lid] = l["rphone"]
    if l.get("su"): out[-1]["su"] = l["su"]
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
BIG_SIZES = ("srednje", "veliko")
SIZE_SCORE = {"majhno": 1.0, "mikro": 0.4, "srednje": -0.3, "veliko": -1.0}
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
    if not o.get("q") and o["src"][0].startswith(REG_SRC) and (o.get("zp") or {}).get("c") == "majhno" and not o.get("vf") and (o["km"] or 0) <= 700:
        z = o["zp"]  # mala podjetja iz registra brez spletne strani: ciljna velikost, a dejavnosti ni mogoče preveriti na spletu
        o["q"] = dict(t="2", sz="majhno", auto=1, why=f"Iz registra: {o['no'].replace('Registrirana dejavnost: ', '').rstrip('.')}, zaposleni {z.get('t') or '10–49'}. Spletne strani nismo našli – dejavnost še ni preverjena (lahko je tudi servis ali najem).",
                      ap="Pokliči (telefon iz imenika) ali poglej na Google Zemljevidih, ali res gradijo plovila.")
    # velikost: register (natančno ali razred) > ročna ocena > številke s spletne strani
    if not o.get("zp"):
        qs = (o.get("q") or {}).get("sz")
        if qs and qs != "?": o["zp"] = dict(c=qs, t="", s="ocena po pregledu")
        elif (SIG.get(o["id"]) or {}).get("emp"):
            e = max(SIG[o["id"]]["emp"]); o["zp"] = dict(c="mikro" if e < 10 else "majhno" if e < 50 else "srednje" if e < 250 else "veliko", t=str(e), s="spletna stran podjetja")
    zc = (o.get("zp") or {}).get("c")
    if o.get("q") and o["q"]["t"] == "1" and zc in BIG_SIZES:  # naročnik: prevelika podjetja ostanejo, a niso več prva prednost
        o["q"] = dict(o["q"], t="2", big=1, why=o["q"]["why"] + " Za zdaj prevelik: naročnik išče podjetja z 10–50 zaposlenimi.")
    o["sc"] = round(o["sc"] + SIZE_SCORE.get(zc, 0), 2)
    if o.get("q"):
        o["sc"] = round(o["sc"] + TIER_SCORE[o["q"]["t"]], 2)
for o in out:  # telefon iz javnega imenika za mala podjetja brez drugih kontaktov (pogosto nimajo spletne strani)
    ph = RPH.get(o["id"])
    if ph and not o.get("ct") and (o.get("zp") or {}).get("c") not in BIG_SIZES and (o.get("q") or {}).get("t") != "3":
        o["ct"] = dict(w=o.get("w", ""), e=[], p=[ph[0]], d=sl_date(RUN_DATE), n=f"Telefon iz javnega imenika ({ph[1]}).")
AC = json.load(open("data/autocontacts.json")) if os.path.exists("data/autocontacts.json") else {}
for o in out:
    if o.get("ct") or (o.get("q") or {}).get("t") not in ("1", "2", "K"): continue
    a = AC.get(o["id"])
    if a: o["ct"] = dict(w=a["w"], e=a["e"], p=a["p"], d=sl_date(a.get("d", RUN_DATE)), n="Splošni kontakt s spletne strani podjetja (samodejno). Imena oseb poišči v nakupni skupini.")
for o in out:  # splošni kontakt s seznama razstavljavcev, če ga na strani ni
    f = FCT.get(o["id"])
    if f and not o.get("ct") and (o.get("q") or {}).get("t") in ("1", "2", "K"):
        o["ct"] = dict(w=o.get("w", ""), e=[f[0]], p=[f[1]] if f[1] else [], d=sl_date(RUN_DATE), n=f"Splošni kontakt s seznama razstavljavcev ({f[2]}). Imena oseb poišči v nakupni skupini.")
for o in out:
    p = PLACES.get(o["id"])
    if p and p.get("ok"):
        if p.get("status") == "CLOSED_PERMANENTLY":
            o["q"] = dict(t="3", sz=(o.get("q") or {}).get("sz", "?"), why="Google Places: podjetje je trajno zaprto.", ap="")
        if not o.get("ct") and (p.get("phone") or p.get("web")) and (o.get("q") or {}).get("t") in ("1", "2", "K"):
            o["ct"] = dict(w=p.get("web", ""), e=[], p=[p["phone"]] if p.get("phone") else [], d=sl_date(p.get("d", RUN_DATE)), n="Kontakt iz Google Places.")
    if o["id"] in CHG: o["ch"] = CHG[o["id"]]
    wn = WNOTES.get(o["n"])
    if wn:
        o["no"] = (o["no"] + " " if o["no"] else "") + wn["note"]
        if wn.get("t"):
            o["q"] = dict(t=wn["t"], sz=(o.get("q") or {}).get("sz", "?"), why=wn["note"], ap="")
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
# Priložnosti: konkretni povodi za stik, vsak z virom (docs/opps.json)
CC3 = {"si": "Slovenija", "hr": "Hrvaška", "it": "Italija", "at": "Avstrija", "de": "Nemčija", "hu": "Madžarska", "cz": "Češka", "sk": "Slovaška",
       "pl": "Poljska", "fr": "Francija", "ba": "BiH", "rs": "Srbija", "me": "Črna gora", "ch": "Švica"}
by_cc = {}
for o in out: by_cc.setdefault(o["cc"], []).append(o)
GENERIC_T = {"yachting", "service", "services", "servis", "nautic", "nautik", "nautique", "nautisme", "technik", "technology", "sport", "sports",
             "boote", "bateaux", "barche", "charter", "trade", "handel", "sailing", "werft", "shipyard", "composites", "industries"}
def find_lead(name, cc):
    """Zmagovalec razpisa -> podjetje v bazi: najprej v državi naročnika, nato drugod (le ob nedvoumnem imenu)."""
    for pool, strict in ((by_cc.get(cc, []), False), (out, True)):
        best, bo = 0, None
        for o in pool:
            if o["s"] == "spec": continue
            a, b = toks(name), toks(o["n"]); ov = a & b
            if not ov or len(ov) < min(2, len(a), len(b)) or not (ov - GENERIC_T): continue
            if strict and not (len(ov) >= 2 or max(len(x) for x in ov) >= 6): continue
            if len(ov) > best: best, bo = len(ov), o
        if bo: return bo
    return None
opps = []
BOATNAME = re.compile(r"werft|boot|boat|yacht|jacht|nautic|nautik|marine|cantier|brod|łodz|lodz|stocz|bateau|naval|chantier|shipyard|composit|ribs?\b|plovil|čoln|coln|hajó", re.I)
for t in _load("data/tenders.json", []):
    where = CC3.get(t["cc"], t["cc"])
    if t["t"] == "oddan":
        for w in t["win"]:
            o = find_lead(w, t["cc"])
            if o: o.setdefault("tn", []).append([t["d"], t["title"], t["buyer"], t["url"]])
            elif not BOATNAME.search(w): continue  # sklopi z motorji, prikolicami … – le zmagovalci, ki so videti kot ladjedelnice
            opps.append(dict(ty="narocilo", d=t["d"], id=o["id"] if o else None, n=o["n"] if o else pretty_reg(w), cc=t["cc"], km=o["km"] if o else None,
                             tx=f"{t['title']} – naročnik {t['buyer']} ({where}).", src="TED – javna naročila EU", u=t["url"]))
    elif not t["dl"] or t["dl"] >= RUN_DATE:
        opps.append(dict(ty="razpis", d=t["d"], id=None, n=t["buyer"], cc=t["cc"], km=None,
                         tx=f"{t['title']}" + (f". Rok za ponudbe {sl_date(t['dl'])}" if t["dl"] else "") + f" ({where}).",
                         src="TED – javna naročila EU", u=t["url"]))
DEV = re.compile(r"prototip|iščejo partnerja|startup|zagonsk|nov model|nova linija|novi modeli|v razvoju|premiera|razvoj novih|nov T40|nov trup", re.I)
for o in out:
    q = o.get("q") or {}
    if q and not q.get("auto") and q["t"] in ("1", "2") and DEV.search(q["why"] + " " + q.get("ap", "")):
        opps.append(dict(ty="razvoj", d="", id=o["id"], n=o["n"], cc=o["cc"], km=o["km"], tx=q["why"], src="ročni pregled spletne strani", u=o.get("w", "")))
    g = SIG.get(o["id"]) or {}
    if g.get("jobs") and q.get("t") in ("1", "2", "K"):
        opps.append(dict(ty="zaposlujejo", d="", id=o["id"], n=o["n"], cc=o["cc"], km=o["km"], tx="Iščejo ljudi v proizvodnji: »" + g["jobs"][:160].strip() + " …«",
                         src="spletna stran podjetja", u=o.get("w", "")))
for c in _load("docs/changes.json", []):
    if c.get("ty") == "model" and c["d"] >= (datetime.date.fromisoformat(RUN_DATE) - datetime.timedelta(days=120)).isoformat():
        opps.append(dict(ty="model", d=c["d"], id=c["id"], n=c["n"], cc="", km=c.get("km"), tx=c["tx"], src="tedenska primerjava spletne strani", u=""))
OPRI = {"razvoj": 0, "narocilo": 1, "model": 2, "zaposlujejo": 3, "razpis": 4}
SZO = {"majhno": 0, "mikro": 1, "?": 2, "srednje": 3, "veliko": 4}
zid = {o["id"]: (o.get("zp") or {}).get("c", "?") for o in out}
for x in opps: x["z"] = zid.get(x["id"], "?") if x["id"] else "?"
opps.sort(key=lambda x: (OPRI[x["ty"]], 0 if x["id"] else 1, -(int(x["d"].replace("-", "")) if x["d"] else 0), SZO[x["z"]] if x["ty"] in ("razvoj", "zaposlujejo") else 0,
                         x["km"] if x["km"] is not None else 9999))
json.dump(opps, open("docs/opps.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("priložnosti", collections.Counter(x["ty"] for x in opps), "naročila povezana s podjetji:", sum(1 for x in opps if x["ty"] == "narocilo" and x["id"]))

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
