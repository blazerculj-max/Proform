"""Splošni kontakti (e-pošta, telefon), objavljeni na prebranih straneh podjetja."""
import json, re, os, urllib.parse
GENERIC = re.compile(r"^(info|office|sales|commerciale|vendite|kontakt|contact|mail|post|nabava|prodaja|uffici?o|amministrazione|service|tecnico|ufficiotecnico|welcome|hello|boote|werft|yachts?|cantiere|segreteria)\b", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+|00)(?:39|43|49|41|385|386|36|420|421|48)[\s./-]?\(?0?\)?[\s./-]?\d[\d\s./-]{6,14}\d")
CODES = {"it": "39", "at": "43", "de": "49", "ch": "41", "hr": "385", "si": "386", "hu": "36", "cz": "420", "sk": "421", "pl": "48"}
def contacts(c):
    t = " ".join(p[1] for p in c["pages"])
    host = urllib.parse.urlparse(c["url"]).netloc.replace("www.", "")
    root = ".".join(host.split(".")[-2:])
    ems = []
    for e in EMAIL.findall(t):
        e = e.strip(".").lower()
        if re.search(r"\.(png|jpe?g|gif|webp|svg)$", e) or "example" in e or "sentry" in e or "wixpress" in e: continue
        if e not in ems: ems.append(e)
    own = [e for e in ems if e.split("@")[1].endswith(root)]
    pick = [e for e in own if GENERIC.match(e.split("@")[0])][:2] or own[:1]
    code = CODES.get(c.get("cc", ""), "")
    pages = sorted(c["pages"], key=lambda p: 0 if re.search(r"contat|contact|kontakt|impressum|imprint", p[0], re.I) else 1)
    ph = []
    for pg in pages:
        for p in PHONE.findall(pg[1]):
            p = re.sub(r"\s+", " ", p).strip()
            digits = re.sub(r"\D", "", p)
            if not (9 <= len(digits) <= 14): continue
            if code and not re.sub(r"^00", "+", p).startswith("+" + code): continue
            if p not in ph: ph.append(p)
        if ph: break
    return pick, ph[:1]
if __name__ == "__main__":
    out = {}
    cc = {o["id"]: o["cc"] for o in json.load(open("docs/leads.json"))}
    for f in os.listdir("data/crawl"):
        c = json.load(open("data/crawl/" + f)); c["cc"] = cc.get(c["id"], ""); e, p = contacts(c)
        if e or p: out[c["id"]] = dict(w=c["url"], e=e, p=p, d=os.environ.get("RUN_DATE") or __import__("datetime").date.today().isoformat())
    json.dump(out, open("data/autocontacts.json", "w"), ensure_ascii=False, indent=0)
    print(len(out))
