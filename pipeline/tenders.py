"""Javna naročila za plovila (TED, uradni portal EU): kdo kupuje čolne in kdo je dobil naročilo.
Podjetje z novim javnim naročilom pogosto potrebuje nov trup ali prilagojen model – priložnost za modele in kalupe.
Odprt razpis pa pomeni, da bodo mala podjetja oddajala ponudbe in iskala podizvajalce.
    python3 pipeline/tenders.py      # zadnjih 18 mesecev; rezultat data/tenders.json
"""
import json, subprocess, datetime, re, sys

# CPV: čolni in manjša plovila (3452…), reševalna in delovna plovila
CPV = ["34520000", "34521000", "34521100", "34521200", "34521300", "34521400", "34522000", "34522100", "34522150", "34522200",
       "34522250", "34522300", "34522350", "34522400", "34522450", "34522500", "34522550", "34522600", "34522700"]
COUNTRIES = ["SVN", "HRV", "ITA", "AUT", "DEU", "HUN", "CZE", "SVK", "POL", "FRA", "BIH", "SRB", "MNE"]
CC = {"SVN": "si", "HRV": "hr", "ITA": "it", "AUT": "at", "DEU": "de", "HUN": "hu", "CZE": "cz", "SVK": "sk", "POL": "pl", "FRA": "fr",
      "BIH": "ba", "SRB": "rs", "MNE": "me"}
LANG = {"si": "slv", "hr": "hrv", "it": "ita", "at": "deu", "de": "deu", "hu": "hun", "cz": "ces", "sk": "slk", "pl": "pol", "fr": "fra"}
TYPE = {"cn-standard": "odprt", "cn-social": "odprt", "pin-only": "napoved", "can-standard": "oddan", "can-modif": "oddan", "can-social": "oddan"}

def search(query, page):
    body = dict(query=query, page=page, limit=100, fields=["publication-number", "notice-title", "buyer-name", "buyer-country", "publication-date",
                "notice-type", "winner-name", "classification-cpv", "deadline-receipt-tender-date-lot", "total-value", "place-of-performance"])
    out = subprocess.run(["curl", "-s", "-m", "60", "-X", "POST", "https://api.ted.europa.eu/v3/notices/search", "-H", "Content-Type: application/json",
                          "-d", json.dumps(body)], capture_output=True).stdout
    return json.loads(out or b"{}")

def pick(v, lang):
    """Večjezična polja: najprej jezik države, nato angleščina, nato karkoli."""
    if isinstance(v, dict):
        for k in (lang, "eng"):
            if v.get(k): return v[k]
        return next(iter(v.values()), "")
    return v

if __name__ == "__main__":
    since = (datetime.date.today() - datetime.timedelta(days=548)).strftime("%Y%m%d")
    q = f"classification-cpv IN ({' '.join(CPV)}) AND buyer-country IN ({' '.join(COUNTRIES)}) AND publication-date>={since}"
    rows, page = [], 1
    while True:
        d = search(q, page)
        for n in d.get("notices", []):
            cc = CC.get((n.get("buyer-country") or [""])[0], "")
            lang = LANG.get(cc, "eng")
            title = pick(n.get("notice-title"), lang)
            title = re.sub(r"^[^–]+– [^–]+– ", "", title if isinstance(title, str) else str(title)).strip()
            buyer = pick(n.get("buyer-name"), lang); buyer = buyer[0] if isinstance(buyer, list) and buyer else buyer
            win = pick(n.get("winner-name"), lang) or []
            dl = n.get("deadline-receipt-tender-date-lot") or []
            rows.append(dict(id=n["publication-number"], d=n["publication-date"][:10], t=TYPE.get(n.get("notice-type"), n.get("notice-type")), cc=cc,
                             buyer=buyer or "", title=title[:220], win=sorted(set(win if isinstance(win, list) else [win])),
                             dl=(dl[0] if isinstance(dl, list) and dl else dl or "")[:10],
                             url=f"https://ted.europa.eu/sl/notice/{n['publication-number']}/html"))
        if page * 100 >= d.get("totalNoticeCount", 0): break
        page += 1
    rows.sort(key=lambda r: r["d"], reverse=True)
    json.dump(rows, open("data/tenders.json", "w"), ensure_ascii=False, indent=0)
    import collections
    print("javna naročila:", len(rows), dict(collections.Counter(r["t"] for r in rows)), dict(collections.Counter(r["cc"] for r in rows)), file=sys.stderr)
