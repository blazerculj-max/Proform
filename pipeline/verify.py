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
SUBPAGE = re.compile(r"manufaktur|storitve|usluge|dejavnost|activit|product|prodott|produkt|proizvodi|izdelk|metod|method|plant|yard|cantieri|sedi|werk|about|chi-?siamo|azienda|company|unternehmen|ueber|%c3%bcber|über|o-?nas|o-?nama|werft|cantiere|shipyard|produzion|production|produktion|proizvod|factory|stabiliment|technolog|tecnolog|costruzion|construction|bootsbau|history|storia|geschichte|zgodovina|povijest|quality|qualita|manufactur", re.I)

def fetch(url):
    try:
        r = subprocess.run(["curl", "-s", "-L", "--max-redirs", "5", "-m", "15", "--max-filesize", "2500000", "-A", UA,
                            "-w", "\n__FINAL__%{url_effective}", url], capture_output=True, timeout=25)
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

def check(lead):
    url = lead["url"]
    h, final = fetch(url)
    pages, texts = [final], [text_of(h)]
    for u in links_of(h, final):
        hh, ff = fetch(u); pages.append(ff); texts.append(text_of(hh)); time.sleep(0.3)
    full = " \n ".join(texts)
    if len(full) < 400:
        return dict(id=lead["id"], v="X", u=final, n=len(full))
    st, md, tu, tr = hits(full, STRONG), hits(full, MED), hits(full, TOURISM), hits(full, TRADE)
    s, m, t, r = len(st), len(md), len(tu), len(tr)
    if s >= 3 and s > t: v = "M"
    elif s >= 1 and (s + m) >= 3 and s >= t: v = "m"
    elif t >= 2 and s <= 1: v = "T"
    elif r >= 2 and s <= 1: v = "S"
    else: v = "N"
    order = ["kalupi", "laminiranje", "infuzija", "vetroresina", "stakloplastika", "stekloplastika", "GFK", "GRP", "steklena vlakna", "kompoziti", "vinilester", "epoksi", "gelcoat", "karbon", "vakuum", "obrat", "proizvodnja", "gradimo", "gradnja čolnov"]
    ev = [[k, st[k]] for k in order if k in st][:4]
    neg = [[k, x] for k, x in list(tu.items())[:3] + list(tr.items())[:2]]
    return dict(id=lead["id"], v=v, u=final, s=s, m=m, t=t, r=r, ev=ev, neg=neg[:3], pages=len(pages))

if __name__ == "__main__":
    todo = json.load(open(sys.argv[1]))
    res = []
    with cf.ThreadPoolExecutor(10) as ex:
        for i, r in enumerate(ex.map(check, todo)):
            res.append(r)
            if i % 25 == 0: print(i, file=sys.stderr, flush=True)
    json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=0)
    from collections import Counter
    print(Counter(r["v"] for r in res), file=sys.stderr)
