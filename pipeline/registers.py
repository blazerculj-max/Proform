"""Poslovni registri in imeniki z dejavnostjo in številom zaposlenih – za iskanje malih podjetij, tudi brez spletne strani.
    python3 pipeline/registers.py it fr cz at de hr si osm
    it  – Registro Imprese prek aziende.it: ATECO 30.12 (čolni) in 30.30 (letala), zaposleni s strani podjetja
    fr  – recherche-entreprises.api.gouv.fr (uradni register): NAF 30.12Z in 30.30Z, razred zaposlenih, koordinate
    frc – isti register: mala podjetja (6–49 zaposlenih) s kompoziti, poliestrom ali karbonom v imenu
    cz  – ARES (uradni register): CZ-NACE 30120 in 30300, kategorija zaposlenih
    at  – WKO Firmen A-Z: obrt »Bootbauer« (oznaka Lehrbetrieb = ima vajence, torej zaposlene)
    de  – Gelbe Seiten: panoga »Bootsbau« (z naslovom, telefonom in spletno stranjo)
    ch  – Schweizerischer Bootbauer-Verband: člani, ki gradijo nova plovila (Neubau)
    hr  – CompanyWall: NKD C30120, število zaposlenih s strani podjetja
    si  – CompanyWall: SKD 30.120, število zaposlenih s strani podjetja
    osm – OpenStreetMap: craft=boatbuilder v vseh državah v polmeru (prej le 300 km)
Rezultat: data/reg/<vir>.json. Poizvedbe so počasne (vljudnostni premori)."""
import json, os, re, sys, time, html, subprocess, csv, concurrent.futures as cf

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
os.makedirs("data/reg", exist_ok=True)
exec(open("pipeline/geocode.py").read().split("if __name__")[0])  # post, city, norm, hav
MAXKM = 1000

def curl(url, data=None, headers=(), timeout=40):
    cmd = ["curl", "-s", "-L", "-m", str(timeout), "-A", UA]
    for h in headers: cmd += ["-H", h]
    if data is not None: cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-d", json.dumps(data)]
    return subprocess.run(cmd + [url], capture_output=True).stdout.decode("utf-8", "ignore")

def text(h):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def size_of(n):
    if n is None: return "?"
    return "mikro" if n < 10 else "majhno" if n < 50 else "srednje" if n < 250 else "veliko"

pname = {}
for _cc, _d in post.items():
    for _la, _lo, _nm in _d.values(): pname.setdefault(_cc, {}).setdefault(norm(_nm), (_la, _lo))
def geo(cc, zp="", town=""):
    k = re.sub(r"[\s-]", "", zp or "")
    for kk in (k, (re.match(r"\d+", k) or [""])[0]):
        if kk and kk in post.get(cc, {}): return post[cc][kk][:2]
    t = re.sub(r"(?i)\bcedex\b|\(.*?\)", " ", town or "")
    for part in [t] + re.split(r"[/,-]", t):
        n = norm(part)
        if n and n in city.get(cc, {}): return city[cc][n][:2]
        if n and n in pname.get(cc, {}): return pname[cc][n]
    return None

def finish(rows, name):
    out = []
    for r in rows:
        if r.get("lat") is None:
            g = geo(r["cc"], r.get("zip", ""), r.get("city", ""))
            if g: r["lat"], r["lon"] = g
        if r.get("lat") is not None:
            r["km"] = round(hav(LAT0, LON0, r["lat"], r["lon"]))
            if r["km"] > MAXKM: continue
        out.append(r)
    json.dump(out, open(f"data/reg/{name}.json", "w"), ensure_ascii=False, indent=0)
    import collections
    print(name, len(rows), "->", len(out), "v polmeru;", dict(collections.Counter(r["sz"] for r in out)), file=sys.stderr)

# ---------- Italija: aziende.it (Registro Imprese) ----------
IT_ROW = re.compile(r'<a href="(/[^"]+)">([^<]+)</a>\s*</p>\s*</div>\s*<div[^>]*>\s*([^<]*?)\s*</div>\s*<div[^>]*>\s*([\d.]+)\s*</div>'
                    r'\s*<div[^>]*>\s*([^<]*?)\s*</div>\s*<div[^>]*>\s*([^<]*?)\s*</div>')
def it():
    rows = []
    for code, act in (("30.12", "Costruzione di imbarcazioni da diporto e sportive"), ("30.30", "Fabbricazione di aeromobili")):
        page, last = 1, 1
        while page <= last:
            for wait in (0, 30, 120):  # ponovi stran, ki ne odgovori
                time.sleep(wait)
                h = curl(f"https://www.aziende.it/30/{code}" + (f"?pag={page}" if page > 1 else ""))
                found = IT_ROW.findall(h)
                if found: break
            last = max([last] + [int(x) for x in re.findall(r"pag=(\d+)", h)])
            for path, name, rev, ateco, prov, comune in found:
                rows.append(dict(src="Registro Imprese (aziende.it)", n=html.unescape(name).strip(), cc="it", city=comune, prov=prov,
                                 nace=ateco, act=act, rev=rev.replace("\xa0", " ").strip(), url="https://www.aziende.it" + path, emp=None, empr="", sz="?"))
            page += 1; time.sleep(1.5)
    print("it: v seznamu", len(rows), file=sys.stderr)
    # podrobnosti počasi (stran ima zaščito pred preobremenitvijo); že prebrane ostanejo shranjene
    old = {}
    for f in ("data/reg/it.json", "data/reg/it_partial.json"):
        for x in (json.load(open(f)) if os.path.exists(f) else []):
            if x.get("zip") and (x["sz"] != "?" or f.endswith("partial.json")): old[x["url"]] = x
    done = [0]
    def det(r):
        if r["url"] in old: return dict(r, **{k: old[r["url"]][k] for k in ("empr", "emp", "sz", "street", "zip", "city") if k in old[r["url"]]})
        for wait in (0, 60, 180):  # ponovi samo, če stran ne odgovori (zaščita), ne če podatka ni
            time.sleep(wait + 2.5)
            out = subprocess.run(["curl", "-s", "-L", "-m", "40", "-A", UA, "-w", "\n%{http_code}", r["url"]], capture_output=True).stdout.decode("utf-8", "ignore")
            code = out.rsplit("\n", 1)[-1]; t = text(out)
            if code == "200" and len(t) > 2000: break
            if code == "404": return r
        else: return r
        done[0] += 1
        if done[0] % 25 == 0:
            print("it: prebranih", done[0], file=sys.stderr, flush=True)
            json.dump([x for x in rows if x.get("zip")], open("data/reg/it_partial.json", "w"), ensure_ascii=False)
        m = re.search(r"([\d.]+(?:\s*-\s*[\d.]+)?|oltre [\d.]+)(?:\s+dipendenti)?\s+Dipendenti\b", t)
        if m:
            r["empr"] = m.group(1).replace(" ", "")
            nums = [int(x.replace(".", "")) for x in re.findall(r"[\d.]+", r["empr"])]
            lo, hi = nums[0], nums[-1]
            r["emp"] = lo if lo == hi else None
            r["sz"] = size_of(lo) if lo >= 10 or lo == hi else size_of(hi)
        m = re.search(r"Sede legale: (.+?), (\d{5}) ([^()]+?) \((\w\w)\)", t)
        if m: r["street"], r["zip"], r["city"] = m.group(1), m.group(2), m.group(3).strip()
        return r
    BIG = (">500 milioni", "100-500 milioni", "50-100 milioni", "25-50 milioni")
    for i, r in enumerate(rows):  # pod 1 mio € prometa so mikro podjetja – zadošča ocena po prometu
        if r["rev"] not in BIG and r["rev"] != "0-1 milioni": rows[i] = det(r)
    for r in rows:
        if r["sz"] == "?" and r["rev"] in BIG: r["sz"] = "srednje" if r["rev"] == "25-50 milioni" else "veliko"; r["empr"] = ""
    finish(rows, "it")

# ---------- Francija: uradni register (recherche-entreprises) ----------
FR_TR = {"00": (0, "0"), "01": (1, "1–2"), "02": (4, "3–5"), "03": (7, "6–9"), "11": (15, "10–19"), "12": (35, "20–49"), "21": (75, "50–99"),
         "22": (150, "100–199"), "31": (225, "200–249"), "32": (375, "250–499"), "41": (750, "500–999"), "42": (1500, "1000–1999"),
         "51": (3500, "2000–4999"), "52": (7500, "5000–9999"), "53": (10000, "10000+")}
def fr():
    rows = []
    for naf, act in (("30.12Z", "Construction de bateaux de plaisance"), ("30.30Z", "Construction aéronautique et spatiale")):
        page = 1
        while True:
            u = f"https://recherche-entreprises.api.gouv.fr/search?activite_principale={naf}&etat_administratif=A&per_page=25&page={page}"
            try: d = json.loads(curl(u))
            except Exception: time.sleep(5); continue
            for e in d.get("results", []):
                est = [x for x in e.get("matching_etablissements", []) if x.get("activite_principale") == naf] or [e["siege"]]
                s = e["siege"] if e["siege"].get("activite_principale") == naf else est[0]
                tr = e.get("tranche_effectif_salarie") or "NN"
                emp, empr = FR_TR.get(tr, (None, ""))
                la, lo = s.get("latitude"), s.get("longitude")
                rows.append(dict(src="Register podjetij Francije (INSEE)", n=e.get("nom_complet", "").strip(), cc="fr", city=(s.get("libelle_commune") or "").title(),
                                 zip=s.get("code_postal") or "", street=s.get("adresse", ""), lat=num(la), lon=num(lo),
                                 nace=naf, act=act, emp=None, empr=empr, sz=size_of(emp) if emp is not None else "?", id=e["siren"],
                                 url=f"https://annuaire-entreprises.data.gouv.fr/entreprise/{e['siren']}"))
            if page >= d.get("total_pages", 1): break
            page += 1; time.sleep(0.25)
    finish(rows, "fr")

def frc():
    """Francija: mala podjetja s kompoziti v imenu (6–49 zaposlenih) – »druge panoge«, ki potrebujejo modele in kalupe."""
    rows, seen = [], set()
    for q in ("composite", "composites", "polyester", "stratifie", "stratifies", "resine", "fibre de verre"):
        page = 1
        while True:
            u = "https://recherche-entreprises.api.gouv.fr/search?q=" + q.replace(" ", "%20") + f"&etat_administratif=A&tranche_effectif_salarie=03,11,12&per_page=25&page={page}"
            try: d = json.loads(curl(u))
            except Exception: time.sleep(5); continue
            for e in d.get("results", []):
                nm = e.get("nom_complet", "")
                if e["siren"] in seen or not re.search(r"COMPOSI|POLYEST|STRATIF|RESINE|RÉSINE|FIBRE", nm.upper()): continue
                s = e["siege"]; naf = s.get("activite_principale") or ""
                # samo proizvodnja (NAF 13–33) ali inženiring s kompoziti; brez talnih oblog, trgovin, notarjev …
                if not (re.match(r"(1[3-9]|2\d|3[0-3])\.", naf) or (naf.startswith("71.12") and "COMPOSI" in nm.upper())): continue
                seen.add(e["siren"])
                emp, empr = FR_TR.get(e.get("tranche_effectif_salarie") or "NN", (None, ""))
                la, lo = s.get("latitude"), s.get("longitude")
                rows.append(dict(src="Register podjetij Francije (INSEE)", n=nm.strip(), cc="fr", city=(s.get("libelle_commune") or "").title(), zip=s.get("code_postal") or "",
                                 lat=num(la), lon=num(lo), nace=s.get("activite_principale", ""), seg="composite",
                                 act="Kompoziti (dejavnost " + (s.get("activite_principale") or "?") + ")", emp=None, empr=empr, sz=size_of(emp) if emp is not None else "?",
                                 id=e["siren"], url=f"https://annuaire-entreprises.data.gouv.fr/entreprise/{e['siren']}"))
            if page >= d.get("total_pages", 1) or page >= 20: break
            page += 1; time.sleep(0.25)
    finish(rows, "fr_comp")

# ---------- Češka: ARES ----------
CZ_KAT = {"110": (3, "1–5"), "120": (7, "6–9"), "130": (7, "6–9"), "210": (15, "10–19"), "220": (22, "20–24"), "230": (37, "25–49"),
          "240": (75, "50–99"), "310": (150, "100–199"), "320": (225, "200–249"), "330": (375, "250–499"), "340": (750, "500–999"),
          "410": (1500, "1000–1499"), "420": (1750, "1500–1999"), "430": (3000, "2000–3999"), "440": (5000, "4000–4999"), "000": (0, "0")}
def cz():
    rows = []
    for nace, act in (("30120", "Stavba rekreačních a sportovních člunů"), ("30300", "Výroba letadel a jejich motorů")):
        start = 0
        while True:
            d = json.loads(curl("https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat",
                                data={"czNace": [nace], "pocet": 100, "start": start}) or "{}")
            for e in d.get("ekonomickeSubjekty", []):
                s = e.get("sidlo", {})
                rows.append(dict(src="Register podjetij Češke (ARES)", n=e.get("obchodniJmeno", ""), cc="cz", city=s.get("nazevObce", ""),
                                 zip=str(s.get("psc", "")), street=s.get("textovaAdresa", ""), nace=nace, act=act, id=e["ico"], emp=None, empr="", sz="?",
                                 url=f"https://ares.gov.cz/ekonomicke-subjekty?ico={e['ico']}"))
            start += 100
            if start >= d.get("pocetCelkem", 0): break
            time.sleep(0.5)
    def det(r):
        try: d = json.loads(curl(f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty-res/{r['id']}"))
        except Exception: return r
        z = (d.get("zaznamy") or [{}])[0]
        k = (z.get("statistickeUdaje") or {}).get("kategoriePoctuPracovniku")
        if k in CZ_KAT: n, r["empr"] = CZ_KAT[k]; r["sz"] = size_of(n)
        r["prevail"] = z.get("czNacePrevazujici2008") or z.get("czNacePrevazujici", "")
        time.sleep(0.3); return r
    with cf.ThreadPoolExecutor(3) as ex: rows = list(ex.map(det, rows))
    finish(rows, "cz")

# ---------- Avstrija: WKO Firmen A-Z (obrt Bootbauer) ----------
def at():
    # seznam pokaže največ 10 zadetkov, listanje deluje le v brskalniku: zato po okrajih, pri več kot 10 po krajih
    from urllib.parse import quote
    def page(slug):
        h = curl("https://firmen.wko.at/bootbauer/" + quote(slug)); time.sleep(3.0)
        if "Unbekannter Fehler" not in h and len(h) < 5000: time.sleep(120); h = curl("https://firmen.wko.at/bootbauer/" + quote(slug))  # zaščita (403)
        m = re.search(r'content="(\d+)&#32;Unternehmen', h)
        if not m and "Keine Ergebnisse" not in h and "0 Treffer" not in h: return None, []  # neznano ime
        return (int(m.group(1)) if m else 0), h.split("<article class='search-result-article'>")[1:]
    bez = {}
    for row in csv.reader(open("data/geo_dl/AT/AT.txt", encoding="utf-8"), delimiter="\t"):
        bez.setdefault(row[5], set()).add(row[2])
    seen, rows = set(), []
    def take(arts):
        for a in arts:
            m = re.search(r'class="title-link" href="([^"]+)"><h3>([^<]+)</h3>', a)
            if not m: continue
            fid = re.search(r"firmaid=([0-9a-f-]+)", m.group(1)); fid = fid.group(1) if fid else m.group(1)
            if fid in seen: continue
            seen.add(fid)
            st = re.search(r'class="street"[^>]*>([^<]*)<', a); pl = re.search(r'class="place">\s*(\d{4})\s*(?:&nbsp;)?\s*([^<]+)<', a)
            rows.append(dict(src="WKO Firmen A-Z (Bootbauer)", n=html.unescape(m.group(2)).strip(), cc="at", street=html.unescape(st.group(1)).strip() if st else "",
                             zip=pl.group(1) if pl else "", city=html.unescape(pl.group(2)).strip() if pl else "", nace="Bootbauer", act="Obrt: Bootbauer",
                             emp=None, empr="", sz="?", lehr=1 if "Lehrbetrieb" in a else 0, id=fid,
                             url="https://firmen.wko.at" + html.unescape(m.group(1)).split("&suchbegriff")[0]))
    total, arts = page("")
    for b, places in sorted(bez.items()):
        nm = b.replace("Politischer Bezirk ", "")
        slug = (nm.replace(" Stadt", "") if nm.endswith(" Stadt") or not b.startswith("Politischer") else nm + " bezirk").lower().replace(" ", "_")
        n, arts = page(slug)
        take(arts)
        if n is None: print("at: neznan okraj", slug, file=sys.stderr, flush=True); continue
        if n > len(arts):  # več kot 10 zadetkov -> po krajih
            for pl in sorted(places):
                n2, arts2 = page(pl.lower().replace(" ", "_"))
                if n2: take(arts2)
        json.dump(rows, open("data/reg/at_partial.json", "w"), ensure_ascii=False)
    print("at: WKO navaja", total, "zbranih", len(rows), file=sys.stderr)
    finish(rows, "at")

# ---------- Nemčija: Gelbe Seiten, panoga »Bootsbau« (strani panog so dovoljene, iskanje ne) ----------
def de():
    import base64, urllib.parse
    h = curl("https://www.gelbeseiten.de/branchen/bootsbau/bundesweit")
    total = int((re.search(r'id="mod-TrefferlisteInfo">(\d+)<', h) or [0, 0])[1])
    parts = [h]; pos = 51
    while pos <= total:
        time.sleep(1.5)
        r = subprocess.run(["curl", "-s", "-m", "40", "-A", UA, "-X", "POST", "-d", urllib.parse.urlencode(dict(umkreis=-1, verwandt="false", WAS="bootsbau",
                            WO="bundesweit", position=pos, anzahl=10, sortierung="relevanz")), "https://www.gelbeseiten.de/ajaxsuche"], capture_output=True).stdout
        try: parts.append(json.loads(r)["html"])
        except Exception: break
        pos += 10
    rows, seen = [], set()
    for part in parts:
        for a in part.split('<article class="mod mod-Treffer"')[1:]:
            a = a.split("</article>")[0]
            rid = re.search(r'data-realid="([^"]+)"', a); nm = re.search(r'class="mod-Treffer__name"[^>]*>([^<]+)<', a)
            if not nm or (rid and rid.group(1) in seen): continue
            if rid: seen.add(rid.group(1))
            st = re.search(r'mod-AdresseKompakt__adress-text"[^>]*>\s*([^<]*?),?\s*<', a)
            ort = re.search(r'mod-AdresseKompakt__adress__ort"[^>]*>\s*(\d{5})\s+([^<]+)<', a)
            tel = re.search(r'mod-TelefonnummerKompakt__phoneNumber[^>]*>\s*([^<]+?)\s*<', a)
            web = re.search(r'data-webseiteLink="([^"]+)"', a, re.I)
            try: web = base64.b64decode(web.group(1) + "==").decode() if web else ""
            except Exception: web = ""
            br = re.search(r'mod-Treffer--besteBranche"[^>]*>([^<]+)<', a)
            rows.append(dict(src="Gelbe Seiten (Bootsbau)", n=html.unescape(nm.group(1)).strip(), cc="de", street=html.unescape(st.group(1)).strip() if st else "",
                             zip=ort.group(1) if ort else "", city=html.unescape(ort.group(2)).strip() if ort else "", nace="Bootsbau",
                             act=html.unescape(br.group(1)).strip() if br else "Bootsbau", emp=None, empr="", sz="?", web=web,
                             phone=tel.group(1).strip() if tel else "", id=rid.group(1) if rid else "",
                             url="https://www.gelbeseiten.de/gsbiz/" + (rid.group(1) if rid else "")))
    print("de: Gelbe Seiten navaja", total, "zbranih", len(rows), file=sys.stderr)
    finish(rows, "de")

# ---------- Švica: Schweizerischer Bootbauer-Verband, člani z »Neubau« (gradnja novih plovil) ----------
def ch():
    base = "https://www.bootbauer.ch/marken-typen/werftenfachbetriebe/"
    rows, start = [], 0
    while True:
        h = curl(base + "filterForm?Services%5BFlagNewConstructions%5D=FlagNewConstructions&action_applyFilter=Suchen" + (f"&start={start}" if start else ""))
        found = re.findall(r"location.href='(/marken-typen/werftenfachbetriebe/addressData/[^']+)'[^>]*>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>", h)
        for path, name, ort in found:
            rows.append(dict(src="Schweizerischer Bootbauer-Verband (Neubau)", n=html.unescape(name).strip(), cc="ch", city=html.unescape(ort).strip(),
                             nace="Neubau", act="Član zveze švicarskih ladjedelnic, gradnja novih plovil", emp=None, empr="", sz="?",
                             url="https://www.bootbauer.ch" + path))
        if not found or f"start={start + 50}" not in h: break
        start += 50; time.sleep(1.0)
    for r in rows:
        h = curl(r["url"]); time.sleep(1.0); t = text(h)
        m = re.search(r"\|?\s*([^|]{3,60}?) \| (\d{4}) ([^|]+?) \| Telefon ([+\d ]+)", re.sub(r"<[^>]+>", " | ", h).replace("\n", " "))
        m2 = re.search(r"(\d{4}) ([A-ZÄÖÜa-zäöüéèàç .'()-]+?) Telefon ([+\d ]{9,})", t)
        if m2: r["zip"], r["city"], r["phone"] = m2.group(1), m2.group(2).strip(), m2.group(3).strip()
        web = [u for u in re.findall(r'href="(https?://[^"]+)"', h) if not re.search(r"bootbauer\.ch|facebook|instagram|youtube|fonts\.|google|linkedin", u)]
        r["web"] = web[0] if web else ""
        if "Lehrbetrieb" in t and "Bootbauer" in t[t.find("Lehrbetrieb"):t.find("Lehrbetrieb") + 80]: r["lehr"] = 1
    finish(rows, "ch")

# ---------- Hrvaška in Slovenija: CompanyWall ----------
CW = {"hr": ("https://www.companywall.hr", "pretraga", "C30120", "/tvrtka/", "Gradnja čamaca za razonodu i sportskih čamaca"),
      "si": ("https://www.companywall.si", "iskanje", "30.120", "/podjetje/", "Gradnja čolnov za razvedrilo in šport")}
def slug_name(sl):  # »morski-vuk-doo« -> »Morski Vuk d.o.o.«
    w = sl.split("-"); tail = {"doo": "d.o.o.", "jdoo": "j.d.o.o.", "dd": "d.d.", "sp": "s.p."}.get(w[-1])
    return " ".join(x.capitalize() for x in (w[:-1] if tail else w)) + (" " + tail if tail else "")

def cw(cc):
    base, path, code, pref, act = CW[cc]
    # brez prijave pokaže največ 3 strani (60 zadetkov) na poizvedbo, zato po regijah (županijah)
    h0 = curl(f"{base}/{path}?at={code}&sbjact=t")
    i = h0.find('id="r"'); regs = [v for v, _ in re.findall(r'<option value="(\d+)">([^<]+)</option>', h0[i:i + 4000])] if i > 0 else []
    links = []
    for r in [""] + regs:
        for page in (1, 2, 3):
            h = h0 if (not r and page == 1) else curl(f"{base}/{path}?at={code}&sbjact=t" + (f"&r={r}" if r else "") + f"&p={page}")
            new = [l for l in dict.fromkeys(re.findall(r'href="(' + pref + r'[^"]+/MM[A-Za-z0-9]+)"', h)) if l not in links]
            links += new; time.sleep(1.0)
            if len(set(re.findall(r'href="(' + pref + r'[^"]+/MM[A-Za-z0-9]+)"', h))) < 20: break
    print(cc, "podjetij v seznamu", len(links), file=sys.stderr)
    old = {r["url"]: r for r in (json.load(open(f"data/reg/{cc}.json")) if os.path.exists(f"data/reg/{cc}.json") else [])}
    rows = []
    for l in links:
        if base + l in old: rows.append(old[base + l]); continue
        t = text(curl(base + l)); time.sleep(1.0)
        nm = re.search(r"(?:Naziv|Kratko ime|Ime podjetja|Kratki naziv)\s+(.+?)\s+(?:Kratko|Skraćeni|Naslov|Adresa|OIB|DŠ|Matična)", t)
        h1 = re.search(r"Koliko zaposlenih ima (?:podjetje|tvrtka) (.+?) \?", t) or re.search(r"Kakšen je naslov podjetja (.+?) \?|Koja je adresa tvrtke (.+?) \?", t)
        name = (h1.group(1) or h1.group(2)) if h1 and h1.lastindex else (nm.group(1) if nm else slug_name(l.split("/")[2]))
        emp = re.search(r"(?:zaposluje skupaj|zapošljava ukupno) ([\d.,]+) (?:delavcev|radnika)", t)
        n = float(emp.group(1).replace(".", "").replace(",", ".")) if emp else None
        adr = re.search(r"(?:Naslov podjetja je|Adresa tvrtke je) (.+?), (\d{4,5}),? ([^,]+?), (?:Slovenija|Hrvatska)", t)
        tel = re.search(r"(?:Kontakt podjetja je|Kontakt tvrtke je) ([\d +/()-]{6,})", t)
        sz = re.search(r"(?:Velikost podjetja|Veličina subjekta) (Mikro|Majhne|Male|Srednje|Velike|Mala|Srednja|Velika)", t)
        rows.append(dict(src="CompanyWall (" + ("Hrvaška" if cc == "hr" else "Slovenija") + ")", n=name.strip(), cc=cc, nace=code, act=act,
                         street=adr.group(1) if adr else "", zip=adr.group(2) if adr else "", city=adr.group(3).strip() if adr else "",
                         emp=round(n, 1) if n is not None else None, empr="" if n is None else str(round(n)), sz=size_of(n) if n is not None else "?",
                         cls=sz.group(1) if sz else "", phone=tel.group(1).strip() if tel else "", url=base + l))
    finish(rows, cc)

# ---------- OpenStreetMap: izdelovalci čolnov v vseh državah v polmeru ----------
def osm():
    rows = []
    for c in ["SI", "HR", "IT", "AT", "DE", "CH", "HU", "CZ", "SK", "PL", "FR", "BA", "RS", "ME", "LI"]:
        q = f'[out:json][timeout:180];area["ISO3166-1"="{c}"][admin_level=2]->.a;nwr["craft"="boatbuilder"](area.a);out center tags;'
        for _ in range(3):
            try: d = json.loads(subprocess.run(["curl", "-s", "-m", "200", "--data-urlencode", "data=" + q, "https://overpass-api.de/api/interpreter"],
                                               capture_output=True).stdout or b"{}"); break
            except Exception: time.sleep(20); d = {}
        for e in d.get("elements", []):
            t = e.get("tags", {}); nm = t.get("name")
            if not nm: continue
            la = e.get("lat") or e.get("center", {}).get("lat"); lo = e.get("lon") or e.get("center", {}).get("lon")
            rows.append(dict(src="OpenStreetMap", n=nm, cc=c.lower(), lat=la, lon=lo, city=t.get("addr:city", ""), zip=t.get("addr:postcode", ""),
                             street=" ".join(x for x in (t.get("addr:street", ""), t.get("addr:housenumber", "")) if x), nace="craft=boatbuilder",
                             act="Izdelovalec čolnov (OSM)", emp=None, empr="", sz="?", web=t.get("website") or t.get("contact:website") or "",
                             phone=t.get("phone") or t.get("contact:phone") or "", url=f"https://www.openstreetmap.org/{e['type']}/{e['id']}"))
        print("osm", c, len(d.get("elements", [])), file=sys.stderr); time.sleep(5)
    finish(rows, "osm")

if __name__ == "__main__":
    for a in sys.argv[1:]:
        {"it": it, "fr": fr, "frc": frc, "cz": cz, "at": at, "de": de, "ch": ch, "hr": lambda: cw("hr"), "si": lambda: cw("si"), "osm": osm}[a]()
