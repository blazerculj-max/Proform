"""Primerja to osvežitev s prejšnjo in zapiše novosti: nov model, oglas za delo, stran ne deluje / spet deluje,
sprememba ocene. Datoteke: data/snapshots.json (stanje), data/changes.json (zgodovina), data/run_events.json (ta zagon),
data/lead_changes.json (zadnja novost po podjetju), docs/changes.json (za stran)."""
import json, os, re, datetime

RUN_DATE = os.environ.get("RUN_DATE") or datetime.date.today().isoformat()
MODEL = re.compile(r"\b([A-Z][A-Za-z]{0,12}[ -]?\d{2,3}(?!\d)(?:[ -]?[A-Z]{1,4}\b)?)")
NOTMODEL = re.compile(r"^(jan|feb|mar|apr|may|mai|jun|jul|aug|sep|set|okt|oct|nov|dec|dic|dez|gen|giu|lug|ago|ott|"
                      r"januar|februar|march|märz|april|june|july|juli|august|september|oktober|october|november|december|dezember|"
                      r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre|"
                      r"news|award|days|day|show|festival|saison|season|week|edition|collection|collections|customisation|angebote|produkte|"
                      r"kampagne|begins|release|boote|games|nel|mit|dal|from|since|seit|year|anno|jahr|pf|ai|pe|smm|page|step|top|vol|no|nr|"
                      r"scopri|discover|new|neu|nuovo|nuova|novi|die|der|das|the|suite|greece|italy|italia|read|leggi|mehr|more|view|a|il|la|le|un)\b", re.I)
YEAR = re.compile(r"\b(2025|2026|2027|2028)\b")
VERDICT = {"M": "potrjen proizvajalec", "m": "verjetno proizvaja", "N": "ni dokazov", "X": "strani ni mogoče prebrati",
           "D": "stran ne deluje", "T": "charter / turizem", "S": "trgovina / servis"}

def load(p, d):
    return json.load(open(p)) if os.path.exists(p) else d

def models(snips):
    out = set()
    for s in snips:
        if not YEAR.search(s): continue
        for m in MODEL.findall(s):
            m = m.strip()
            if NOTMODEL.match(m) or re.fullmatch(r"(?:19|20)\d\d", m): continue
            if re.fullmatch(r"[A-Z] \d{2,3}", m): continue          # »A 70« iz »A 70-foot«
            out.add(m)
    return out

if __name__ == "__main__":
    leads = {o["id"]: o for o in json.load(open("docs/leads.json"))}
    sig = load("data/signals.json", {})
    prev = load("data/snapshots.json", None)
    first_run = prev is None
    prev = prev or {}
    hist = load("data/changes.json", [])
    snap, events = {}, []
    def ev(i, ty, tx):
        o = leads[i]
        events.append(dict(d=RUN_DATE, id=i, n=o["n"], ty=ty, tx=tx, t=(o.get("q") or {}).get("t", ""), km=o["km"]))
    for i, o in leads.items():
        v = (o.get("vf") or {}).get("v")
        g = sig.get(i, {})
        cur = dict(v=v, mo=sorted(models(g.get("new", []))), jobs=g.get("jobs", ""),
                   web=(o.get("vf") or {}).get("u") or o.get("w") or "")
        if not (v or g): continue
        snap[i] = cur
        p = prev.get(i)
        if first_run or p is None:
            # prvi pregled: zabeleži samo močne znake (nov model z letnico, oglas za delo)
            q = o.get("q") or {}
            relevant = q.get("t") in ("1", "2") and not q.get("auto") and (o["km"] is None or o["km"] <= 700)
            if cur["mo"] and relevant:
                ev(i, "model", "Omenja nov model: " + ", ".join(cur["mo"][:3]))
            if cur["jobs"] and relevant:
                ev(i, "jobs", "Oglas za delo: «" + cur["jobs"][:140] + "»")
            continue
        newm = [m for m in cur["mo"] if m not in set(p.get("mo", []))]
        if newm: ev(i, "model", "Omenja nov model: " + ", ".join(newm[:3]))
        if cur["jobs"] and not p.get("jobs"): ev(i, "jobs", "Nov oglas za delo: «" + cur["jobs"][:140] + "»")
        if p.get("v") and v and p["v"] != v:
            if v == "D": ev(i, "down", "Spletna stran ne deluje več (prej: " + VERDICT.get(p["v"], p["v"]) + ").")
            elif p["v"] == "D": ev(i, "up", "Spletna stran spet deluje – " + VERDICT.get(v, v) + ".")
            else: ev(i, "verdict", "Ocena strani: " + VERDICT.get(p["v"], p["v"]) + " → " + VERDICT.get(v, v) + ".")
        if cur["web"] and not p.get("web"): ev(i, "web", "Najdena spletna stran: " + cur["web"])
    # združi z zgodovino brez podvajanja
    seen = {(e["d"], e["id"], e["ty"], e["tx"]) for e in hist}
    hist = [e for e in events if (e["d"], e["id"], e["ty"], e["tx"]) not in seen] + hist
    hist = hist[:600]
    latest = {}
    for e in hist:
        latest.setdefault(e["id"], dict(d=e["d"], ty=e["ty"], tx=e["tx"]))
    json.dump(snap, open("data/snapshots.json", "w"), ensure_ascii=False, indent=0)
    json.dump(hist, open("data/changes.json", "w"), ensure_ascii=False, indent=0)
    json.dump(events, open("data/run_events.json", "w"), ensure_ascii=False, indent=0)
    json.dump(latest, open("data/lead_changes.json", "w"), ensure_ascii=False, indent=0)
    json.dump(hist[:200], open("docs/changes.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print(("prvi pregled, " if first_run else "") + f"novosti v tem zagonu: {len(events)}, v zgodovini: {len(hist)}")
