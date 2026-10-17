"""Pripravi sezname strani za preverjanje (verify) in poglobljeno branje (crawl2)."""
import json
d = json.load(open("docs/leads.json"))
web = lambda o: (o.get("vf") or {}).get("u") or (o.get("ct") or {}).get("w") or o.get("w")
fix = lambda w: w if w.startswith("http") else "http://" + w
def deep(o):
    v = (o.get("vf") or {}).get("v"); t = (o.get("q") or {}).get("t")
    return v in ("M", "m") or (v in ("N", "X") and o["r"] <= 1) or t in ("1", "2", "K") or o["km"] is None
verify = [{"id": o["id"], "url": fix(web(o))} for o in d if o["s"] != "spec" and web(o)]
crawl = [{"id": o["id"], "url": fix(web(o))} for o in d if o["s"] != "spec" and web(o) and deep(o)]
json.dump(verify, open("data/verify_todo.json", "w")); json.dump(crawl, open("data/crawl_todo.json", "w"))
print(len(verify), "za preverjanje,", len(crawl), "za branje")
