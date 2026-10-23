"""Preveri, ali podjetje res proizvaja (kompozitna plovila, kalupe) ali je charter, trgovina ali servis.
Bere javne spletne strani podjetij (domača stran + do 4 podstrani) in išče dokaze v SL/HR/IT/DE/EN."""
import json, re, sys, html, subprocess, concurrent.futures as cf, urllib.parse, time

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"

STRONG = {  # dokazi o lastni proizvodnji, kompozitih in kalupih
 "vetroresina": "vetroresina", "fibra di vetro": "vetroresina", "laminazion": "laminiranje", "laminat": "laminiranje", "laminier": "laminiranje",
 "laminira": "laminiranje", "infusion": "infuzija", "infusione": "infuzija", "infuzij": "infuzija", "sottovuoto": "vakuum", "vakuum": "vakuum",
 "gfk": "GFK", "grp": "GRP", "fibreglass": "steklena vlakna", "fiberglass": "steklena vlakna", "glasfaser": "steklena vlakna",
 "stakloplastik": "stakloplastika", "stekloplastik": "stekloplastika", "vinylester": "vinilester", "vinilester": "vinilester",
 "epoxy": "epoksi", "epossidic": "epoksi", "epoksi": "epoksi", "gelcoat": "gelcoat", "composit": "kompoziti", "kompozit": "kompoziti",
 "verbundwerkstoff": "kompoziti", "faserverbund": "kompoziti", "kohlefaser": "karbon", "fibra di carbonio": "karbon", "carbon fibre": "karbon", "carbon fiber": "karbon",
 "stampi": "kalupi", "stampo": "kalupi", "modelleria": "kalupi", "formenbau": "kalupi", "urmodell": "kalupi", "kalup": "kalupi",
 "mould": "kalupi", "mold ": "kalupi", "molds": "kalupi", "tooling": "kalupi",
 "produzione": "proizvodnja", "produktion": "proizvodnja", "proizvodnj": "proizvodnja", "fertigung": "proizvodnja", "manufactur": "proizvodnja",
 "stabilimento": "obrat", "factory": "obrat", "production plant": "obrat", "production facility": "obrat", "produktionshalle": "obrat", "werkhalle": "obrat", "pogon": "obrat",
 "costruiamo": "gradimo", "we build": "gradimo", "wir bauen": "gradimo", "gradimo": "gradimo", "izdelujemo": "gradimo", "izrađujemo": "gradimo", "proizvodimo": "gradimo",
 "poliester": "poliester", "polyester": "poliester", "odlitk": "odlitki", "smole": "smole", "resine": "smole", "harz": "smole",
 "steklen vlakn": "steklena vlakna", "staklen vlakn": "steklena vlakna", "laminiranj": "laminiranje",
 "manufaktur": "proizvodnja", "hergestellt": "proizvodnja", "gefertigt": "proizvodnja", "in eigener": "proizvodnja", "realizziamo": "gradimo", "costruite": "gradimo",
 "izdelava plovil": "gradnja čolnov", "gradnja plovil": "gradnja čolnov", "izdelava čoln": "gradnja čolnov", "izgradnj": "gradnja čolnov",
 "boatbuilding": "gradnja čolnov", "boat building": "gradnja čolnov", "bootsbau": "gradnja čolnov", "brodogradnj": "gradnja čolnov", "costruzione di imbarcazioni": "gradnja čolnov",
}
MED = {
 "cantiere": "ladjedelnica", "shipyard": "ladjedelnica", "werft": "ladjedelnica", "brodogradili": "ladjedelnica", "ladjedelnic": "ladjedelnica",
 "naval architect": "projektant", "progettista": "projektant", "konstrukteur": "projektant", "design by": "projektant",
 "lunghezza fuori tutto": "specifikacije", "länge über alles": "specifikacije", "loa": "specifikacije", "categoria ce": "specifikacije", "ce category": "specifikacije", "ce-kategorie": "specifikacije",
 "nuovo modello": "nov model", "new model": "nov model", "neues modell": "nov model", "novi model": "nov model", "novo plovilo": "nov model",
 "world premiere": "premiera", "anteprima": "premiera", "weltpremiere": "premiera", "premiere": "premiera",
 "prototip": "prototip", "prototyp": "prototip", "ricerca e sviluppo": "razvoj", "r&d": "razvoj", "entwicklung": "razvoj", "razvoj": "razvoj",
 "sandwich": "sendvič", "carbon": "karbon",
}
TOURISM = {
 "charter": "charter", "noleggio": "najem", "rent a boat": "najem", "boat rental": "najem", "bootsverleih": "najem", "vermietung": "najem",
 "verleih": "najem", "najem": "najem", "iznajmljivanj": "najem", "najam": "najem", "escursion": "izleti", "excursion": "izleti", "ausflug": "izleti",
 "izlet": "izleti", "boat trip": "izleti", "boat tour": "izleti", "gita in barca": "izleti", "sailing school": "šola jadranja", "scuola vela": "šola jadranja",
 "segelschule": "šola jadranja", "šola jadranja": "šola jadranja", "škola jedrenja": "šola jadranja", "hotel": "turizem", "apartma": "turizem", "booking": "turizem",
}
TRADE = {
 "concessionario": "trgovec", "dealer for": "trgovec", "authorized dealer": "trgovec", "vertragshändler": "trgovec", "generalvertretung": "trgovec",
 "brokerage": "posrednik", "yacht broker": "posrednik", "usato": "rabljeni", "used boats": "rabljeni", "gebrauchtboot": "rabljeni", "rabljen": "rabljeni",
 "rimessaggio": "zimovanje", "winterlager": "zimovanje", "manutenzione": "servis", "assistenza tecnica": "servis", "reparatur": "servis", "repair": "servis",
 "servis": "servis", "posto barca": "privez", "liegeplatz": "privez", "ormeggi": "privez",
}
# Dokazi, pomembni za Proform: kalupi in modeli, laminiranje, stekloplastika in kompoziti.
# Iščemo v jeziku strani; pri vsakem izrazu je slovenski prevod. Vrstni red: najbolj povedni izrazi najprej.
PF = {
 "kalupi": [("formenbau", "izdelava kalupov"), ("urmodell", "glavni model"), ("negativform", "kalup"), ("modellbau", "izdelava modelov"),
            ("modelli e stampi", "modeli in kalupi"), (r"\b(?:contro)?stampi\b", "kalupi"), (r"\b(?:contro)?stampo\b", "kalup"), ("modelleria", "izdelava modelov"),
            ("moules", "kalupi"), ("moule", "kalup"), ("moulds", "kalupi"), ("mould", "kalup"), ("molds", "kalupi"), ("mold", "kalup"),
            ("kalup", "kalup"), ("forma laminac", "kalup"), ("rumpfform", "kalup trupa"), ("gfk-form", "kalup"), ("tooling", "orodja (kalupi)"),
            ("stampaggio", "oblikovanje v kalupu"), ("moulage", "oblikovanje v kalupu")],
 "laminiranje": [("laminiertechnik", "laminiranje"), ("handlaminat", "ročno laminiranje"), ("vakuuminfusion", "vakuumska infuzija"),
            ("laminier", "laminiranje"), ("laminazion", "laminiranje"), ("laminiranj", "laminiranje"), ("laminira", "laminiranje"),
            ("laminowani", "laminiranje"), ("laminován", "laminiranje"), ("laminovan", "laminiranje"), ("stratification", "laminiranje"),
            ("stratifi", "laminiranje"), ("infusione", "infuzija"), ("infusion", "infuzija"), ("infuzij", "infuzija"), ("sottovuoto", "vakuum"),
            ("vacuum bag", "vakuum"), ("vakuum", "vakuum"), ("rtm", "RTM (injekcija smole)"), ("lamination", "laminiranje"), ("laminating", "laminiranje")],
 "stekloplastika": [("gfk", "stekloplastika"), ("grp", "stekloplastika"), ("frp", "stekloplastika"), ("vetroresina", "stekloplastika"),
            ("glasfaser", "steklena vlakna"), ("fibra di vetro", "steklena vlakna"), ("fibre de verre", "steklena vlakna"), ("fibreglass", "steklena vlakna"),
            ("fiberglass", "steklena vlakna"), ("stakloplastik", "stekloplastika"), ("stekloplastik", "stekloplastika"), ("steklen vlakn", "steklena vlakna"),
            ("staklen vlakn", "steklena vlakna"), ("sklolamin", "stekloplastika"), ("üvegszál", "steklena vlakna"), ("laminat poliestrowo", "stekloplastika"),
            ("faserverbund", "kompoziti"), ("verbundwerkstoff", "kompoziti"), (r"\bcompositi\b", "kompoziti"), ("composite", "kompoziti"), ("kompozit", "kompoziti"),
            ("kohlefaser", "karbon"), ("fibra di carbonio", "karbon"), ("fibre de carbone", "karbon"), ("carbon fibre", "karbon"), ("carbon fiber", "karbon"),
            ("vinylester", "vinilester"), ("vinilester", "vinilester"), ("epoxy", "epoksi"), ("epossidic", "epoksi"), ("epoksi", "epoksi"),
            ("gelcoat", "gelcoat"), ("polyester", "poliester"), ("poliester", "poliester")],
}
PRODUCTION = {"proizvodnja", "obrat", "gradimo", "gradnja čolnov"}

def pf_hits(text):
    """Najdeni izrazi po skupinah (v jeziku strani, s prevodom) in do dva citata, v katerih so izrazi označeni.
    Bližnji zadetki gredo v isti citat, da se besedilo ne ponavlja."""
    t = re.sub(r"\s+", " ", text)
    groups, first = {}, []
    for grp, terms in PF.items():
        words, pos = [], None
        for k, sl in terms:
            pat = k if k.startswith("\\b") else (r"\b" + re.escape(k) + r"\b") if len(k) <= 4 else re.escape(k)
            m = re.search(pat, t, re.I)
            if not m: continue
            w = re.search(r"[\w-]*" + pat + r"[\w-]*", t[max(0, m.start() - 30):m.end() + 30], re.I)
            word = (w.group(0) if w else m.group(0)).strip("-")
            if any(word.lower() in x[0].lower() for x in words): continue  # že vsebovano (»stampi« v »modelli e stampi«)
            words.append([word, sl])
            if pos is None:  # označi celo besedo
                a0, b0 = m.start(), m.end()
                while a0 > 0 and (t[a0 - 1].isalnum() or t[a0 - 1] == "-"): a0 -= 1
                while b0 < len(t) and (t[b0].isalnum() or t[b0] == "-"): b0 += 1
                pos = (a0, b0)
            if len(words) >= 4: break
        if words: groups[grp] = words; first.append((pos[0], pos[1], grp))
    quotes = []
    for a, b, grp in sorted(first):
        if quotes and a < quotes[-1]["e"] + 40 and b - quotes[-1]["s"] < 340:  # dovolj blizu: isti citat
            q = quotes[-1]; q["e"] = max(q["e"], b + 60); q["h"].append([a, b, grp]); continue
        if len(quotes) >= 2: break
        quotes.append(dict(s=max(0, a - 80), e=min(len(t), b + 110), h=[[a, b, grp]]))
    out = []
    for q in quotes:
        s0, e0 = q["s"], min(len(t), q["e"])
        out.append(dict(t=("…" if s0 else "") + t[s0:e0] + ("…" if e0 < len(t) else ""), h=[[x - s0 + (1 if s0 else 0), y - s0 + (1 if s0 else 0), g] for x, y, g in q["h"]]))
    return dict(g=groups, q=out) if groups else {}

SUBPAGE = re.compile(r"manufaktur|storitve|usluge|dejavnost|activit|product|prodott|produkt|proizvodi|izdelk|metod|method|plant|yard|cantieri|sedi|werk|about|chi-?siamo|azienda|company|unternehmen|ueber|%c3%bcber|über|o-?nas|o-?nama|werft|cantiere|shipyard|produzion|production|produktion|proizvod|factory|stabiliment|technolog|tecnolog|costruzion|construction|bootsbau|history|storia|geschichte|zgodovina|povijest|quality|qualita|manufactur", re.I)

FETCH_TIMEOUT = 15
def fetch(url):
    try:
        r = subprocess.run(["curl", "-s", "-L", "--max-redirs", "5", "-m", str(FETCH_TIMEOUT), "--max-filesize", "2500000", "-A", UA,
                            "-w", "\n__FINAL__%{url_effective}", url], capture_output=True, timeout=FETCH_TIMEOUT + 15)
        out = r.stdout.decode("utf-8", "ignore")
        body, _, final = out.rpartition("\n__FINAL__")
        return body, final.strip() or url
    except Exception:
        return "", url

def text_of(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?s)<!--.*?-->", " ", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"\s+", " ", t).strip()

def links_of(h, base):
    host = urllib.parse.urlparse(base).netloc.replace("www.", "")
    seen, out = set(), []
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', h, re.I | re.S):
        href, label = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        u = urllib.parse.urljoin(base, href)
        p = urllib.parse.urlparse(u)
        if p.scheme not in ("http", "https") or p.netloc.replace("www.", "") != host: continue
        if re.search(r"\.(pdf|jpe?g|png|zip|docx?)$", p.path, re.I): continue
        if (SUBPAGE.search(p.path) or SUBPAGE.search(label)) and u not in seen:
            seen.add(u); out.append(u)
    return out[:5]

def hits(text, kw):
    low = text.lower(); found = {}
    for k, label in kw.items():
        pat = r"\b" + re.escape(k) if len(k) <= 4 else re.escape(k)
        m = re.search(pat, low)
        if m and label not in found:
            s = max(0, m.start() - 70); e = min(len(text), m.end() + 90)
            found[label] = "…" + text[s:e].strip() + "…"
    return found

# prevzete ali parkirane domene (prodaja domene, igre na srečo, tuj jezik, prazna predloga)
PARKED = re.compile(r"domain (?:is |may be )?for sale|this domain (?:is|may be) for sale|hugedomains|buy this domain|domain parking|parked domain|"
                    r"dominio (?:è|e) già registrato|this domain is already taken|online casino|casino online|slot gacor|togel|judi online|samurai99|"
                    r"link to database cannot be established|active domain connection", re.I)
PLACEHOLDER = re.compile(r"launching soon|under construction|lorem ipsum dolor sit amet", re.I)
def parked(text):
    head = text[:4000]
    if PARKED.search(head) and len(text) < 6000: return True
    if PLACEHOLDER.search(text[:400]) and len(text) < 1200: return True
    cjk = sum(1 for ch in head if "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff")
    return len(head) > 200 and cjk / len(head) > 0.15

def check(lead):
    url = lead["url"]
    h, final = fetch(url)
    pages, texts = [final], [text_of(h)]
    for u in links_of(h, final):
        hh, ff = fetch(u); pages.append(ff); texts.append(text_of(hh)); time.sleep(0.3)
    full = " \n ".join(texts)
    if parked(texts[0]):
        return dict(id=lead["id"], v="D", u=final, n=len(full), parked=1)
    if len(full) == 0:
        return dict(id=lead["id"], v="D", u=final, n=0)          # stran se ne odziva
    if len(full) < 400:
        return dict(id=lead["id"], v="X", u=final, n=len(full))  # se naloži šele v brskalniku
    st, md, tu, tr = hits(full, STRONG), hits(full, MED), hits(full, TOURISM), hits(full, TRADE)
    s, m, t, r = len(st), len(md), len(tu), len(tr)
    if s >= 3 and s > t: v = "M"
    elif s >= 1 and (s + m) >= 3 and s >= t: v = "m"
    elif s >= 3: v = "m"                                          # gradijo in imajo hkrati charter
    elif t >= 2 and s <= 1: v = "T"
    elif r >= 2 and s <= 1: v = "S"
    else: v = "N"
    order = ["kalupi", "laminiranje", "infuzija", "vetroresina", "stakloplastika", "stekloplastika", "GFK", "GRP", "steklena vlakna", "kompoziti", "vinilester", "epoksi", "gelcoat", "karbon", "vakuum", "obrat", "proizvodnja", "gradimo", "gradnja čolnov"]
    ev = [[k, st[k]] for k in order if k in st][:4]
    neg = [[k, x] for k, x in list(tu.items())[:3] + list(tr.items())[:2]]
    pr = sorted({x for x in st if x in PRODUCTION})
    return dict(id=lead["id"], v=v, u=final, s=s, m=m, t=t, r=r, ev=ev, neg=neg[:3], pages=len(pages), mix=1 if (v == "m" and s >= 3 and t >= s) else 0,
                pf=pf_hits(full), pr=pr)

if __name__ == "__main__":
    todo = json.load(open(sys.argv[1]))
    res = []
    with cf.ThreadPoolExecutor(10) as ex:
        for i, r in enumerate(ex.map(check, todo)):
            res.append(r)
            if i % 50 == 0: print(i, file=sys.stderr, flush=True)
    # ponovni poskus za strani, ki se niso odzvale ali so bile prazne (počasneje, z daljšim časom)
    idx = [i for i, r in enumerate(res) if r["v"] in ("D", "X") and not r.get("parked")]
    if idx:
        FETCH_TIMEOUT = 35
        with cf.ThreadPoolExecutor(4) as ex:
            for i, r in zip(idx, ex.map(check, [todo[i] for i in idx])):
                if r["v"] not in ("D", "X") or r.get("n", 0) > res[i].get("n", 0): res[i] = r
        print("ponovno preverjenih:", len(idx), file=sys.stderr)
    json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=0)
    from collections import Counter
    print(Counter(r["v"] for r in res), file=sys.stderr)
