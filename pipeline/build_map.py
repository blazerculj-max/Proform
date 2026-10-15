import json, math, sys
LAT0, LON0 = math.radians(46.4367), math.radians(14.0526)
R=6371
def proj(lon,lat):
    p=math.radians(lat); l=math.radians(lon)-LON0
    cc=math.sin(LAT0)*math.sin(p)+math.cos(LAT0)*math.cos(p)*math.cos(l)
    c=math.acos(max(-1,min(1,cc)))
    k=1 if c<1e-9 else c/math.sin(c)
    x=R*k*math.cos(p)*math.sin(l); y=R*k*(math.cos(LAT0)*math.sin(p)-math.sin(LAT0)*math.cos(p)*math.cos(l))
    return x,-y  # screen y down
topo=json.load(open(sys.argv[1]))
sc=topo["transform"]["scale"]; tr=topo["transform"]["translate"]
arcs=[]
for a in topo["arcs"]:
    x=y=0; pts=[]
    for dx,dy in a:
        x+=dx; y+=dy; pts.append((x*sc[0]+tr[0], y*sc[1]+tr[1]))
    arcs.append(pts)
def arc(i):
    return arcs[i] if i>=0 else arcs[~i][::-1]
def ring(idx):
    pts=[]
    for i in idx:
        a=arc(i); pts.extend(a if not pts else a[1:])
    return pts
def dp(pts,tol):
    if len(pts)<3: return pts
    a,b=pts[0],pts[-1]; dmax=0; ix=0
    ax,ay=a; bx,by=b; L=math.hypot(bx-ax,by-ay) or 1e-9
    for i in range(1,len(pts)-1):
        px,py=pts[i]; d=abs((bx-ax)*(ay-py)-(ax-px)*(by-ay))/L
        if d>dmax: dmax=d; ix=i
    if dmax>tol: return dp(pts[:ix+1],tol)[:-1]+dp(pts[ix:],tol)
    return [a,b]
out=[]
for g in topo["objects"]["countries"]["geometries"]:
    polys=[g["arcs"]] if g["type"]=="Polygon" else g.get("arcs",[]) if g["type"]=="MultiPolygon" else []
    rings=[]
    for poly in polys:
        for rg in poly:
            pts=ring(rg)
            if not any(30<la<64 and -12<lo<42 for lo,la in pts): continue
            xy=[proj(lo,la) for lo,la in pts]
            if min(math.hypot(x,y) for x,y in xy)>1700: continue
            h=len(xy)//2
            s=dp(xy[:h+1],1.6)[:-1]+dp(xy[h:],1.6)
            if len(s)<4: continue
            rings.append([[round(x),round(y)] for x,y in s])
    if rings: out.append({"n":g["properties"]["name"],"r":rings})
json.dump(out,open(sys.argv[2],"w"),separators=(",",":"))
import os; print(len(out),"countries", os.path.getsize(sys.argv[2])//1024,"KB")
print([c["n"] for c in out])
