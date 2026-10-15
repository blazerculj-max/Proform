import json, sys, re, os, html, concurrent.futures as cf
exec(open("pipeline/verify.py").read().split('if __name__')[0])
SUB2 = re.compile(SUBPAGE.pattern + r"|model|range|gamma|flotta|boote|yacht|barche|boats|plovila|brodovi|news|novita|aktuell|novosti|novice|kontakt|contact|contatti|impressum", re.I)
def links2(h, base):
    host = urllib.parse.urlparse(base).netloc.replace("www.", "")
    seen, pri, sec = set(), [], []
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', h, re.I | re.S):
        u = urllib.parse.urljoin(base, m.group(1)); p = urllib.parse.urlparse(u)
        if p.scheme not in ("http","https") or p.netloc.replace("www.","") != host or u in seen: continue
        if re.search(r"\.(pdf|jpe?g|png|zip|docx?)$", p.path, re.I): continue
        lab = re.sub(r"<[^>]+>", " ", m.group(2))
        if SUBPAGE.search(p.path) or SUBPAGE.search(lab): seen.add(u); pri.append(u)
        elif SUB2.search(p.path) or SUB2.search(lab): seen.add(u); sec.append(u)
    return (pri[:4] + sec[:3])[:7]
def meta(h):
    t = re.search(r"(?is)<title[^>]*>(.*?)</title>", h); d = re.search(r'(?is)<meta[^>]+name="description"[^>]+content="([^"]*)"', h)
    return (html.unescape(t.group(1)).strip()[:150] if t else ""), (html.unescape(d.group(1)).strip()[:300] if d else "")
def crawl(item):
    path = f"data/crawl/{item['id']}.json"
    if os.path.exists(path): return
    h, final = fetch(item["url"]); title, desc = meta(h)
    pages = [[final, text_of(h)[:20000]]]
    for u in links2(h, final):
        hh, ff = fetch(u); pages.append([ff, text_of(hh)[:15000]])
    json.dump(dict(id=item["id"], url=final, title=title, desc=desc, pages=pages), open(path, "w"), ensure_ascii=False)
todo = json.load(open(sys.argv[1]))
with cf.ThreadPoolExecutor(8) as ex:
    for i, _ in enumerate(ex.map(crawl, todo)):
        if i % 25 == 0: print(i, flush=True)
print("done")
