import re, json, time, sys, html, subprocess
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
def get(u): return subprocess.run(["curl","-s","-m","60","-A",UA,u],capture_output=True).stdout.decode("utf-8","ignore")
def head(u):
    r=subprocess.run(["curl","-s","-m","30","-A",UA,"-o","/dev/null","-w","%{http_code} %{redirect_url}",u],capture_output=True).stdout.decode()
    p=r.split(" ",1); return p[1].strip() if len(p)>1 and p[0].startswith("30") else ""
out={}
for ct in sys.argv[1].split(","):
    pg=1
    while True:
        h=get(f"https://www.profinautic.com/en/manufacturers/boats/?ct={ct}"+(f"&pg={pg}" if pg>1 else ""))
        for e in h.split('<div class="entry">')[1:]:
            n=re.search(r'<h3>(?:<a[^>]*>)?([^<]+)',e); m=re.search(r'id="entry_en_(\d+)_(\d+)_1"',e)
            if n and m: out[ct+"|"+html.unescape(n.group(1).strip())]=(m.group(1),m.group(2))
        if f"pg={pg+1}" not in h: break
        pg+=1; time.sleep(1.2)
    time.sleep(1.2)
print("ids",len(out),file=sys.stderr)
res={}
for k,(cid,wid) in out.items():
    res[k]=head(f"https://www.profinautic.com/en/jumps/?kind=entry&cid={cid}&wid={wid}")
    time.sleep(0.8)
json.dump(res,open(sys.argv[2],"w"),ensure_ascii=False,indent=0)
print("resolved",sum(1 for v in res.values() if v),"of",len(res),file=sys.stderr)
