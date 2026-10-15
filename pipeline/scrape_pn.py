import re, json, time, sys, html, urllib.request
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
import subprocess
def get(u):
    return subprocess.run(["curl","-s","-m","60","-A",UA,u],capture_output=True,check=True).stdout.decode("utf-8","ignore")
out=[]
for ct in sys.argv[1].split(","):
    pg=1
    while True:
        u=f"https://www.profinautic.com/en/manufacturers/boats/?ct={ct}"+(f"&pg={pg}" if pg>1 else "")
        try: h=get(u)
        except Exception as e: print("ERR",ct,pg,e,file=sys.stderr); break
        ents=h.split('<div class="entry">')[1:]
        for e in ents:
            n=re.search(r'<h3>(?:<a[^>]*>)?([^<]+)',e); a=re.search(r'entryAddr">- ([^<]*)',e)
            m=re.search(r'Manufacturer of models: <b>([^<]*)',e); t=re.search(r'Boats/yachts: ([^<]*)',e)
            out.append(dict(ct=ct,name=html.unescape(n.group(1).strip()) if n else "",addr=html.unescape(a.group(1).strip()) if a else "",models=html.unescape(m.group(1).strip()) if m else "",types=t.group(1).strip() if t else ""))
        print(ct,pg,len(ents),file=sys.stderr)
        if f"pg={pg+1}" not in h: break
        pg+=1; time.sleep(1.5)
    time.sleep(1.5)
json.dump(out,open(sys.argv[2],"w"),ensure_ascii=False,indent=0)
print(len(out))
