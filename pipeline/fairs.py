"""Razstavljavci sejmov kot vir aktivnih podjetij.
    python3 pipeline/fairs.py boot     # boot Düsseldorf (javni imenik VIS, s profili: naslov, splet, hala)
    python3 pipeline/fairs.py genova   # Salone Nautico Genova (javni seznam: kraj, e-pošta, kategorija)
    python3 pipeline/fairs.py pick     # izbere izdelovalce plovil v polmeru 1000 km in preveri njihove strani
Rezultat: data/fairs/<sejem>.json in data/fairs/cand.json (vhod za build_leads). Poizvedbe so počasne (vljudnostni premori)."""
import json, os, re, sys, time, html, subprocess, string, concurrent.futures as cf

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
KEEP = {"SI", "HR", "IT", "AT", "DE", "CH", "HU", "CZ", "SK", "PL", "BA", "RS", "ME", "FR", "NL", "BE", "LI", "MC", "DK", "LU"}
os.makedirs("data/fairs", exist_ok=True)

def curl(url, headers=(), timeout=40):
    cmd = ["curl", "-s", "-L", "-m", str(timeout), "-A", UA]
    for h in headers: cmd += ["-H", h]
    return subprocess.run(cmd + [url], capture_output=True).stdout.decode("utf-8", "ignore")

# ---------- boot Düsseldorf ----------
BOOT = "https://www.boot.de/vis-api/vis/v1/en"
BH = ("X-Vis-Domain: https://www.boot.com", "Accept: */*")

def boot():
    year = os.environ.get("BOOT_YEAR", "2026")
    seen, rows, brands = set(), [], {}
    for letter in list(string.ascii_lowercase) + ["other"]:
        lst = []
        for _ in range(3):  # strežnik občasno vrne napako namesto seznama
            try: lst = json.loads(curl(f"{BOOT}/directory/{letter}", BH) or "[]")
            except Exception: lst = []
            if isinstance(lst, list): break
            lst = []; time.sleep(3)
        for e in lst:
            if not isinstance(e, dict): continue
            if e.get("type") == "trademark": brands.setdefault(e["exh"], []).append(e["name"])
            if e.get("type") != "profile" or e["exh"] in seen: continue
            seen.add(e["exh"]); rows.append(e)
        time.sleep(0.6)
    print("boot: razstavljavcev v imeniku", len(rows), file=sys.stderr)
    def prof(e):
        try: p = json.loads(curl(f"{BOOT}/exhibitors/{e['exh']}/slices/profile", BH) or "{}")
        except Exception: p = {}
        time.sleep(0.3)
        a = p.get("profileAddress") or {}
        links = [l.get("link", "") for l in p.get("links", []) if l.get("link")]
        return dict(fair=f"boot {year}", name=e["name"], cc=(a.get("countryCode") or "").upper(), country=a.get("country") or e.get("country", ""),
                    city=a.get("city") or e.get("city", ""), zip=a.get("zip", ""), street=" ".join(a.get("address") or []),
                    web=links[0] if links else "", email=p.get("email", ""), phone=(p.get("phone") or {}).get("phone", ""),
                    booth=e.get("location", ""), brands=sorted(set(brands.get(e["exh"], []))), hall=(e.get("location", "").split("/")[0].replace("Hall", "").strip()), id=e["exh"])
    # profile samo za države v polmeru (država je že v imeniku)
    cand = [e for e in rows if e.get("country") not in ("", None)]
    out = []
    with cf.ThreadPoolExecutor(4) as ex:
        for r in ex.map(prof, cand):
            if r["cc"] in KEEP: out.append(r)
    json.dump(out, open(f"data/fairs/boot{year}.json", "w"), ensure_ascii=False, indent=0)
    print("boot: v državah v polmeru", len(out), file=sys.stderr)

# ---------- Salone Nautico Genova ----------
CC3 = {"ita": "IT", "svn": "SI", "hrv": "HR", "aut": "AT", "deu": "DE", "ger": "DE", "che": "CH", "fra": "FR", "nld": "NL", "bel": "BE",
       "hun": "HU", "cze": "CZ", "svk": "SK", "pol": "PL", "mco": "MC", "dnk": "DK", "lux": "LU", "smr": "IT"}
def genova():
    year = os.environ.get("GENOVA_YEAR", "2026")
    out, page = [], 1
    while True:
        u = "https://www.salonenautico.com/en/exhibitor-list/" + (f"page/{page}/" if page > 1 else "")
        h = curl(u)
        t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
        L = [x.strip() for x in html.unescape(re.sub(r"<[^>]+>", "\n", t)).split("\n") if x.strip()]
        n = 0
        for i, x in enumerate(L):
            if x == "Headquarters and contacts" and i > 0:
                name, loc = L[i - 1], L[i + 1] if i + 1 < len(L) else ""
                email = L[i + 2] if i + 2 < len(L) and "@" in L[i + 2] else ""
                cat = ""
                for j in range(i + 2, min(i + 6, len(L))):
                    if L[j] == "Category" and j + 1 < len(L): cat = L[j + 1]; break
                m = re.match(r"(.+?)(?:\s*\(([A-Z]{2})\))?,\s*([A-Za-z]{3})$", loc)
                city, prov, c3 = (m.group(1), m.group(2) or "", m.group(3).lower()) if m else (loc, "", "")
                out.append(dict(fair=f"Genova {year}", name=name, city=city.title(), prov=prov, cc=CC3.get(c3, c3.upper()), email=email, cat=cat))
                n += 1
        if n == 0 or f"page/{page + 1}/" not in h: break
        page += 1; time.sleep(0.8)
    json.dump(out, open(f"data/fairs/genova{year}.json", "w"), ensure_ascii=False, indent=0)
    print("Genova: razstavljavcev", len(out), "strani", page, file=sys.stderr)

# ---------- izbor kandidatov ----------
# boot: hale s plovili (preverjeno na razstavljavcih 2026): 1–6 motorni čolni in jahte, 7a superjahte, 9 RIB in manjši čolni,
# 15–16 jadrnice; ostale so oprema (10, 11), potapljanje (12), charter (13), klubi (14), SUP in deske (17), umetnost (7)
BOOT_HALLS = {"1", "2", "3", "4", "5", "6", "7a", "9", "15", "16"}
GENOVA_CAT = re.compile(r"boats|gozzi|♡", re.I)  # ♡ = razstavljavec brez kategorije (pogosto velike ladjedelnice)
FREE = re.compile(r"@(gmail|googlemail|libero|hotmail|yahoo|outlook|tiscali|alice|virgilio|pec|legalmail|live|icloud|tin|email|fastwebnet|gmx|web|t-online|aol|bluewin|orange|free|wanadoo)\.", re.I)
LABEL = {"boot": "Sejem boot Düsseldorf", "Genova": "Sejem Salone Nautico Genova"}

def web_of(r):
    w = r.get("web", "").strip()
    if w: return w if w.startswith("http") else "http://" + w
    e = r.get("email", "").strip()
    if "@" in e and not FREE.search(e): return "http://www." + e.split("@")[1].strip().lower()
    return ""

# shrani samo splošne naslove podjetja (info@, sales@ …); osebnih naslovov in telefonov iz seznamov ne prenašamo
ROLE_MAIL = re.compile(r"^(info|sales|sale|office|marketing|contact|contacts|kontakt|commerciale|commerciali|vendite|vendita|amministrazione|hello|mail|export|service|yacht|yachts|boats|segreteria|ufficio|direzione|team|press|welcome)@[a-z0-9.-]+\.[a-z]{2,}$")
def contact(r):
    e = r.get("email", "").strip().lower()
    return dict(email=e, phone=r.get("phone", "").strip()) if ROLE_MAIL.match(e) else {}

def pretty(n):
    n = re.sub(r"\s+", " ", n.replace("\\", "")).strip()
    if n.isupper() or n.islower():
        n = n.title()
        for a, b in ((" Srl", " S.r.l."), (" S.R.L.", " S.r.l."), (" Spa", " S.p.A."), (" S.P.A.", " S.p.A."), (" Gmbh", " GmbH"), (" D.O.O.", " d.o.o."), (" Ag", " AG"), (" Sas", " SAS")):
            if n.endswith(a) or a + " " in n: n = n.replace(a, b)
    return n

def pick():
    exec(open("pipeline/geocode.py").read().split("if __name__")[0], g := {})
    post, city, norm, hav = g["post"], g["city"], g["norm"], g["hav"]
    pname, prov = {}, {}  # kraji iz poštnih seznamov; središča italijanskih pokrajin (za vnose brez kraja)
    for cc, d in post.items():
        for la, lo, nm in d.values(): pname.setdefault(cc, {}).setdefault(norm(nm), (la, lo))
    import csv
    for row in csv.reader(open("data/geo_dl/IT/IT.txt", encoding="utf-8"), delimiter="\t"):
        try: prov.setdefault(row[6], []).append((float(row[9]), float(row[10])))
        except (ValueError, IndexError): pass
    prov = {k: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v)) for k, v in prov.items()}
    def geo(cc, zp, town, pv=""):
        k = re.sub(r"[\s-]", "", zp or "")
        for kk in (k, (re.match(r"\d+", k) or [""])[0]):
            if kk and kk in post.get(cc, {}): return post[cc][kk][:2]
        t = re.sub(r"(?i)\bcedex\b|\(.*?\)|^\s*[a-z]{2}\s+-\s+", " ", town or "")
        for part in [t] + re.split(r"[/,]", t):
            n = norm(part)
            if not n: continue
            if n in city.get(cc, {}): return city[cc][n][:2]
            if n in pname.get(cc, {}): return pname[cc][n]
        if cc == "it" and pv in prov: return prov[pv]
        return None
    cand, nogeo = [], []
    for f in sorted(os.listdir("data/fairs")):
        m = re.match(r"(boot|genova)(\d{4})\.json$", f)
        if not m: continue
        for r in json.load(open("data/fairs/" + f)):
            cc = (r.get("cc") or "").lower()
            if cc.upper() not in KEEP: continue
            if m.group(1) == "boot":
                if r.get("hall") not in BOOT_HALLS: continue
                where = r.get("booth", "").replace("Hall", "hala")
            else:
                if not GENOVA_CAT.search(r.get("cat", "")): continue
                where = "" if r["cat"] == "♡" else r["cat"]
            ll = geo(cc, r.get("zip"), r.get("city"), r.get("prov", ""))
            if not ll: nogeo.append(r["name"] + " / " + r.get("city", "")); continue
            km = hav(46.4367, 14.0526, *ll)
            if km > 1000: continue
            fair = r["fair"]
            cand.append(dict(fid=hashlib.md5((fair + "|" + r["name"]).encode()).hexdigest()[:10], fair=fair, src=LABEL[fair.split()[0]],
                             n=pretty(r["name"]), cc=cc, city=r.get("city", "").title() if r.get("city", "").isupper() else r.get("city", ""),
                             lat=ll[0], lon=ll[1], km=round(km), web=web_of(r), where=where, brands=r.get("brands", []),
                             **contact(r)))
    print("kandidatov", len(cand), "brez lokacije", len(nogeo), file=sys.stderr)
    # preveri strani (rezultat ostane shranjen; ponovno samo novi kandidati)
    done = {r["id"]: r for r in json.load(open("data/fairs/verify_out.json"))} if os.path.exists("data/fairs/verify_out.json") else {}
    todo = [dict(id=c["fid"], url=c["web"]) for c in cand if c["web"] and c["fid"] not in done]
    if todo:
        json.dump(todo, open("data/fairs/verify_todo.json", "w"))
        subprocess.run([sys.executable, "pipeline/verify.py", "data/fairs/verify_todo.json", "data/fairs/verify_new.json"], check=True)
        for r in json.load(open("data/fairs/verify_new.json")): done[r["id"]] = r
        os.remove("data/fairs/verify_todo.json"); os.remove("data/fairs/verify_new.json")
        json.dump(list(done.values()), open("data/fairs/verify_out.json", "w"), ensure_ascii=False, indent=0)
    for c in cand:
        r = done.get(c["fid"])
        if r: c["v"] = r["v"]; c["u"] = r.get("u", "")
    json.dump(cand, open("data/fairs/cand.json", "w"), ensure_ascii=False, indent=0)
    import collections
    print("preverjanje", collections.Counter(c.get("v", "-") for c in cand), file=sys.stderr)

if __name__ == "__main__":
    import hashlib
    for a in sys.argv[1:]:
        {"boot": boot, "genova": genova, "pick": pick}[a]()
