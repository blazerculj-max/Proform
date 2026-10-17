"""Iz shranjenih besedil spletnih strani izlušči znake za oceno potenciala (velikost, dolžine, novi modeli, orodjarna …)."""
import json, re, os, sys

def snip(text, m, a=70, b=110):
    s = max(0, m.start() - a); e = min(len(text), m.end() + b)
    return re.sub(r"\s+", " ", text[s:e]).strip()

EMP = re.compile(r"(?<![\d.,])(\d{1,4})\s*(?:\+\s*)?(?:dipendenti|addetti|collaboratori|persone|employees|people|staff|mitarbeiter(?:innen)?|beschäftigte|zaposlenih|zaposlenika|djelatnika|zaposleni|workers|lavoratori)\b", re.I)
AREA = re.compile(r"(?<![\d])(\d{1,3}(?:[.,\s]\d{3})+|\d{3,6})\s*(?:m²|m2|mq|metri quadrati|quadratmeter|qm|square met)", re.I)
SINCE = re.compile(r"(?:dal|since|seit|od leta|founded in|fondat[ao] nel|gegründet|established in|osnovan[ao]? )\s*(?:l'anno\s*|im jahr\s*|leta\s*)?(18\d\d|19\d\d|20[0-2]\d)", re.I)
LEN_M = re.compile(r"(?<![\d.,])(\d{1,2}(?:[.,]\d{1,2})?)\s?(?:m|mt|metri|meter|metrov|metara)\b", re.I)
LEN_FT = re.compile(r"(?<![\d])(\d{2,3})\s?(?:ft|piedi|feet|fuß|fuss|')(?![a-z])", re.I)
NEW = re.compile(r"[^.!?]{0,120}\b(nuov[oa]|new|neu(?:e|es|er)?|novi|nova|novo|premiere|anteprima|launch|lancio|varo|präsentiert|presented|debut)\b[^.!?]{0,120}\b(2025|2026|2027)\b[^.!?]{0,60}|[^.!?]{0,120}\b(2025|2026|2027)\b[^.!?]{0,120}\b(nuov[oa]|new|neu(?:e|es|er)?|novi|nova|premiere|anteprima|launch|lancio|varo|debut)\b[^.!?]{0,60}", re.I)
TOOL = re.compile(r"modelleria|reparto stampi|stampi (?:interni|in casa|propri)|in[- ]house (?:tool|mou?ld|plug)|own (?:mou?lds|tooling)|eigene[nr]?\s+formenbau|formenbau|5[- ]?(?:assi|achs|axis|osni|osi)|centro di lavoro|fresatrice|fräsmaschine|cnc[- ]?(?:fräs|milling|router|machining|5)|robot", re.I)
CUSTOM = re.compile(r"su misura|custom[- ]built|one[- ]off|einzelanfertigung|nach maß|po meri|po narudžbi|individuell|fuoriserie", re.I)
CONTRACT = re.compile(r"conto terzi|subfornitur|lohnfertigung|für andere werften|per (?:altri|conto di) cantieri|for other (?:ship)?yards|za druge ladjedelnice|za druga brodogradilišta|oem", re.I)
GROUP = re.compile(r"\bs\.?p\.?a\.?\b|\bgroup\b|\bgruppo\b|\bgruppe\b|\bholding\b|quotata|börsennotiert|listed on", re.I)
ALU = re.compile(r"allumini|aluminium|aluminum|aluminij|alu-?boot", re.I)
WOOD = re.compile(r"\blegno\b|\bholz(?:boot|bau)?\b|\bles(?:en|ena|eni)\b|\bdrv(?:o|ena|eni)\b|\bwooden\b|\bmahogany\b|mogano|mahagoni", re.I)
RIB = re.compile(r"gommon|\brib\b|schlauchboot|gumenjak|inflatable", re.I)
SAIL = re.compile(r"\bvela\b|sailing|segel|jadrnic|jedrilic|sailboat", re.I)
CAT = re.compile(r"catamar|katamar", re.I)
HIRING = re.compile(r"\((?:m/w/d|w/m/d|m/f/d|m/ž)\)|wir suchen|stellenangebot(?:e)? (?:für|als)|we are hiring|we're hiring|job opening|"
                    r"cerchiamo|ricerchiamo|offerta di lavoro|posizione aperta|zaposlimo|iščemo (?:sodelavc|delavc)|zapošljavamo|tražimo (?:radnik|djelatnik)", re.I)
PRODJOB = re.compile(r"laminat|laminier|bootsbau|gfk|plastific|vetroresina|produzione|produktion|proizvodnj|fibreglass|composit|kompozit|tischler|falegnam", re.I)
class _Jobs:
    """Oglas za delo: izrecna zaposlitev + delo v proizvodnji v bližini (±250 znakov)."""
    def search(self, t):
        for m in HIRING.finditer(t):
            if PRODJOB.search(t[max(0, m.start() - 250): m.end() + 250]): return m
        return None
JOBS = _Jobs()
GRP = re.compile(r"vetroresina|gfk|grp|fibreglass|fiberglass|stakloplastik|stekloplastik|composit|kompozit|laminat|infusion|infusione", re.I)

def lengths(t):
    vals = []
    for m in LEN_M.finditer(t):
        v = float(m.group(1).replace(",", "."))
        if 3 <= v <= 60: vals.append(v)
    for m in LEN_FT.finditer(t):
        v = int(m.group(1)) * 0.3048
        if 4 <= v <= 60: vals.append(round(v, 1))
    if len(vals) < 2: return ""
    vals.sort(); lo = vals[len(vals) // 10]; hi = vals[-1 - len(vals) // 10]
    return f"{lo:g}–{hi:g} m"

def summarize(c):
    t = " \n ".join(p[1] for p in c["pages"])
    first = lambda rx: (lambda m: snip(t, m) if m else "")(rx.search(t))
    emp = sorted({int(m.group(1)) for m in EMP.finditer(t) if 2 <= int(m.group(1)) <= 5000})
    area = sorted({int(re.sub(r"[.,\s]", "", m.group(1))) for m in AREA.finditer(t) if 200 <= int(re.sub(r"[.,\s]", "", m.group(1))) <= 500000})
    since = sorted({int(m.group(1)) for m in SINCE.finditer(t)})
    newm = [re.sub(r"\s+", " ", m.group(0)).strip()[:200] for m in NEW.finditer(t)][:2]
    return dict(
        title=c.get("title", ""), desc=c.get("desc", "") or re.sub(r"\s+", " ", c["pages"][0][1][:220]),
        chars=len(t), npages=len(c["pages"]), url=c["url"],
        len=lengths(t), emp=emp[:4], area=area[-3:], since=since[:1],
        new=newm, tool=first(TOOL), custom=bool(CUSTOM.search(t)), contract=first(CONTRACT),
        group=bool(GROUP.search(t)), grp=len(GRP.findall(t)), alu=len(ALU.findall(t)), wood=len(WOOD.findall(t)),
        rib=len(RIB.findall(t)), sail=len(SAIL.findall(t)), cat=len(CAT.findall(t)), jobs=first(JOBS))

if __name__ == "__main__":
    leads = {o["id"]: o for o in json.load(open("docs/leads.json"))}
    out = {}
    for f in os.listdir("data/crawl"):
        c = json.load(open("data/crawl/" + f))
        if c["id"] in leads: out[c["id"]] = summarize(c)
    json.dump(out, open("data/signals.json", "w"), ensure_ascii=False, indent=0)
    rows = sorted(out.items(), key=lambda kv: (leads[kv[0]]["km"] if leads[kv[0]]["km"] is not None else 9999))
    with open("data/signals.txt", "w") as fh:
        for i, (k, s) in enumerate(rows):
            l = leads[k]; v = (l.get("vf") or {}).get("v", "-")
            fh.write(f"[{i}] {k} | {l['n']} | {l['km']} km {l['cc']} | {v} | {s['title'][:70]} | {s['desc'][:200]}\n"
                     f"    len {s['len'] or '?'} | emp {s['emp'] or '?'} | m² {s['area'] or '?'} | od {s['since'] or '?'} | grp{s['grp']} alu{s['alu']} wood{s['wood']} rib{s['rib']} sail{s['sail']} cat{s['cat']}"
                     f"{' | PO MERI' if s['custom'] else ''}{' | SKUPINA' if s['group'] else ''} | {s['chars']}zn/{s['npages']}str\n")
            if s["new"]: fh.write(f"    NOVO: {' || '.join(s['new'])}\n")
            if s["tool"]: fh.write(f"    ORODJA: {s['tool'][:200]}\n")
            if s["contract"]: fh.write(f"    ZA DRUGE: {s['contract'][:200]}\n")
    print(len(out))
