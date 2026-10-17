"""Tedenska osvežitev: preveri spletne strani, prebere kandidate, poišče naslove in kontakte,
(po želji) Google Places, zazna novosti in zgradi docs/. Zaženi iz korena repozitorija:

    python3 pipeline/run.py            # uporabi shranjeno besedilo strani, kjer obstaja
    python3 pipeline/run.py --refresh  # vse strani prebere na novo (tako teče GitHub Actions)
"""
import os, shutil, subprocess, sys, time, datetime

os.environ.setdefault("RUN_DATE", datetime.date.today().isoformat())
REFRESH = "--refresh" in sys.argv
PY = sys.executable

def step(title, *args):
    t = time.time(); print(f"\n== {title}", flush=True)
    subprocess.run([PY, *args], check=True)
    print(f"   ({time.time() - t:.0f} s)", flush=True)

step("GeoNames", "pipeline/geonames.py")
step("Gradnja baze", "pipeline/build_leads.py")
step("Ročno znane spletne strani", "pipeline/find_websites.py")
step("Gradnja baze", "pipeline/build_leads.py")
step("Seznami strani", "pipeline/make_todo.py")
step("Preverjanje proizvodnje (vse strani)", "pipeline/verify.py", "data/verify_todo.json", "data/verify_out.json")
step("Gradnja baze", "pipeline/build_leads.py")
step("Seznami strani", "pipeline/make_todo.py")
if REFRESH and os.path.isdir("data/crawl"): shutil.rmtree("data/crawl")
os.makedirs("data/crawl", exist_ok=True)
step("Branje strani kandidatov", "pipeline/crawl2.py", "data/crawl_todo.json")
step("Znaki (velikost, novi modeli, oglasi)", "pipeline/extract.py")
step("Splošni kontakti", "pipeline/autocontact.py")
step("Naslovi s spletnih strani", "pipeline/siteaddr.py")
step("Google Places (če je ključ)", "pipeline/places.py")
step("Gradnja baze", "pipeline/build_leads.py")
step("Novosti", "pipeline/changes.py")
step("Končna gradnja", "pipeline/build_leads.py")
step("Stran", "pipeline/wrap_page.py")
print("\nKončano.")
