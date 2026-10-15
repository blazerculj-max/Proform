import json, re, math, sys, csv, unicodedata, collections
G="data/geo_dl"
LAT0, LON0 = 46.4367, 14.0526
def hav(a,b,c,d):
    p=math.radians; x=math.sin(p(c-a)/2)**2+math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2
    return 2*6371*math.asin(math.sqrt(x))
def norm(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z ]+"," ",s).strip()
post=collections.defaultdict(dict)
for cc in "SI HR AT CH HU CZ SK IT DE PL FR NL BE DK MC".split():
    for row in csv.reader(open(f"{G}/{cc}/{cc}.txt",encoding="utf-8"),delimiter="\t"):
        k=row[1].replace(" ","").replace("-","")
        try: post[cc.lower()].setdefault(k,(float(row[9]),float(row[10]),row[2]))
        except: pass
city=collections.defaultdict(dict)
for row in csv.reader(open(f"{G}/cities1000/cities1000.txt",encoding="utf-8"),delimiter="\t",quoting=csv.QUOTE_NONE):
    cc=row[8].lower(); pop=int(row[14] or 0)
    names={norm(row[1]),norm(row[2])}|{norm(a) for a in row[3].split(",") if a}
    for n in names:
        if n and (n not in city[cc] or city[cc][n][3]<pop): city[cc][n]=(float(row[4]),float(row[5]),row[1],pop)
def geocode(ct,addr):
    a=addr.replace("\t"," ")
    parts=[p.strip() for p in a.split(",")]
    # postal candidates
    for m in re.finditer(r"(?:\b[A-Z]{1,2}\s?-\s?)?(\d{2,3}[\s-]?\d{2,3}|\d{4,5})(?:\s?[A-Z]{2}\b)?",a):
        k=re.sub(r"[\s-]","",m.group(1))
        if k in post.get(ct,{}): la,lo,nm=post[ct][k]; return la,lo,"postal:"+nm
    for p in parts[::-1]:
        n=norm(re.sub(r"\d","",p))
        for cand in (n, n.split(" ")[-1] if n else "", n.split(" ")[0] if n else ""):
            if cand and cand in city.get(ct,{}) and len(cand)>2:
                la,lo,nm,_=city[ct][cand]; return la,lo,"city:"+nm
    return None
if __name__=="__main__":
    d=json.load(open(sys.argv[1]))
    ok=0
    for r in d:
        g=geocode(r["ct"],r["addr"]) if r["addr"] else None
        if g: r["lat"],r["lon"],r["geo"]=g; r["km"]=round(hav(LAT0,LON0,g[0],g[1])); ok+=1
        else: r["lat"]=r["lon"]=r["km"]=None; r["geo"]=""
    json.dump(d,open(sys.argv[2],"w"),ensure_ascii=False,indent=0)
    print("geocoded",ok,"of",len(d))
    for r in d:
        if r["ct"] in ("si","hr","at") : print(r["km"],r["name"],"|",r["addr"],"|",r["geo"])
