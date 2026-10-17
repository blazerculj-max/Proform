"""Za podjetja brez lokacije prebere naslov (poštna številka + kraj) s shranjenih spletnih strani
in ga preveri v GeoNames. Rezultat: data/addr_fixes.json (id -> lat, lon, kraj, vir)."""
import json, os, re, sys, unicodedata
exec(open("pipeline/geocode.py").read().split("if __name__")[0])

UP = "A-ZÀ-ÖØ-ÞČŠŽĆĐŁŚŻŹ"
TOWN = rf"([{UP}][\w'’ .-]{{1,38}}?)"
PAT = {
    "it": re.compile(rf"\b(\d{{5}})\s+{TOWN}(?=\s*(?:\([A-Z]{{2}}\)|[-,–|]|\s+(?:Italy|Italia|Tel|P\.|C\.F|Phone)|$))"),
    "de": re.compile(rf"\b(?:D-)?(\d{{5}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Deutschland|Germany|Tel|Fon|Telefon)|$))"),
    "at": re.compile(rf"\b(?:A-)?(\d{{4}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Österreich|Austria|Tel|Fon)|$))"),
    "ch": re.compile(rf"\b(?:CH-)?(\d{{4}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Schweiz|Switzerland|Tel)|$))"),
    "si": re.compile(rf"\b(?:SI-)?(\d{{4}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Slovenija|Slovenia|Tel)|$))"),
    "hr": re.compile(rf"\b(?:HR-)?(\d{{5}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Hrvatska|Croatia|Tel)|$))"),
    "hu": re.compile(rf"\b(?:H-)?(\d{{4}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Magyarország|Hungary|Tel)|$))"),
    "pl": re.compile(rf"\b(\d{{2}}-\d{{3}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Polska|Poland|Tel)|$))"),
    "cz": re.compile(rf"\b(\d{{3}}\s?\d{{2}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Česk|Czech|Tel)|$))"),
    "sk": re.compile(rf"\b(\d{{3}}\s?\d{{2}})\s+{TOWN}(?=\s*(?:[-,–|]|\s+(?:Slovensk|Slovakia|Tel)|$))"),
}
CONTACT = re.compile(r"contat|contact|kontakt|impressum|imprint|chi-?siamo|about|o-?nas|o-?nama|azienda|company", re.I)

def ok_town(cc, code, town):
    k = re.sub(r"[\s-]", "", code)
    if k not in post.get(cc, {}): return None
    la, lo, nm = post[cc][k]
    a, b = norm(town).split(), norm(nm).split()
    if not a or not b: return None
    # kraj se mora ujemati s krajem pri tej poštni številki (prvi del imena)
    if a[0][:4] == b[0][:4] or any(w[:5] == a[0][:5] for w in b):
        return la, lo, nm
    # ali s katerimkoli krajem v državi, ki je blizu kraja s poštno številko
    t = norm(town)
    if t in city.get(cc, {}):
        cla, clo, cnm, _ = city[cc][t]
        if hav(la, lo, cla, clo) < 25: return cla, clo, cnm
    return None

def find(c, cc):
    rx = PAT.get(cc)
    if not rx: return None
    pages = sorted(c["pages"], key=lambda p: 0 if CONTACT.search(p[0]) else 1)
    votes = {}
    for url, text in pages:
        for m in rx.finditer(text):
            code, town = m.group(1), m.group(2).strip(" .-")
            town = re.split(r"\s(?:www|http|tel|fax|e-?mail|phone|p\.\s?iva)\b|@", town, flags=re.I)[0].strip(" .-")
            g = ok_town(cc, code, town)
            if g:
                key = (round(g[0], 3), round(g[1], 3))
                v = votes.setdefault(key, dict(lat=g[0], lon=g[1], town=f"{town} ({code})", src=url, n=0))
                v["n"] += 2 if CONTACT.search(url) else 1
    if not votes: return None
    return max(votes.values(), key=lambda v: v["n"])

if __name__ == "__main__":
    leads = json.load(open("docs/leads.json"))
    old = json.load(open("data/addr_fixes.json")) if os.path.exists("data/addr_fixes.json") else {}
    found = 0
    for o in leads:
        if o["km"] is not None or o["id"] in old: continue
        f = f"data/crawl/{o['id']}.json"
        if not os.path.exists(f): continue
        r = find(json.load(open(f)), o["cc"])
        if r: old[o["id"]] = r; found += 1
    json.dump(old, open("data/addr_fixes.json", "w"), ensure_ascii=False, indent=0)
    print("najdenih naslovov:", found, "skupaj popravkov:", len(old))
