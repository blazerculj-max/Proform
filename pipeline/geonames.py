"""Prenese podatke GeoNames (poštne številke in kraji), če jih še ni v data/geo_dl/. Licenca CC BY 4.0."""
import os, subprocess, zipfile
G = "data/geo_dl"
COUNTRIES = "SI HR AT CH HU CZ SK IT DE PL FR NL BE DK MC".split()
os.makedirs(G, exist_ok=True)
def get(url, zpath, outdir):
    if os.path.isdir(outdir) and os.listdir(outdir): return
    subprocess.run(["curl", "-s", "-L", "-m", "300", "-o", zpath, url], check=True)
    zipfile.ZipFile(zpath).extractall(outdir); os.remove(zpath)
for c in COUNTRIES:
    get(f"https://download.geonames.org/export/zip/{c}.zip", f"{G}/{c}.zip", f"{G}/{c}")
get("https://download.geonames.org/export/dump/cities1000.zip", f"{G}/cities1000.zip", f"{G}/cities1000")
print("GeoNames pripravljen")
