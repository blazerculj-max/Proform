# Proform3D radar kupcev

Seznam podjetij v krogu 1000 km od Jesenic, ki potrebujejo modele, kalupe in rezkanje velikih kosov: izdelovalci plovil iz stekloplastike in kompozitov, kompozitni podizvajalci, projektanti, livarne, termoforming, vozila in letalstvo.

**Stran:** [GitHub Pages](https://blazerculj-max.github.io/Proform/) (samo za branje).
Sledenje statusa, opombe in nakupna skupina delujejo v različici na claude.ai, kjer se shranjujejo za vse z dostopom.

## Kaj je na strani

- 927 podjetij na zemljevidu z zračno razdaljo od Jesenic (azimutna projekcija, krogi 150/400/700/1000 km)
- **Prednost** po pregledu spletnih strani: P1 (takoj), P2 (kasneje), P3 (ni primerno), konkurent ali partner – z velikostjo, razlogom in predlogom pristopa
- **Ali res proizvajajo?** – samodejno preverjanje spletnih strani s citati (laminiranje, vetroresina, GFK, kalupi … proti charterju, trgovini, servisu)
- Projektanti in posredniki (J&J Design, Kiska, Felci, Polli …) s povezavo na ladjedelnice, za katere delajo
- Kontakti, ki jih podjetja objavijo na svojih straneh, in predloge prvega sporočila v SL/HR/IT/DE/EN

## Struktura

```
docs/        stran za GitHub Pages (index.html, leads.json, map.json)
pipeline/    skripte za zbiranje in obdelavo podatkov
data/        ročno preverjeni podatki in vmesni rezultati
```

Ročno vzdrževane datoteke v `data/`:

| Datoteka | Vsebina |
|---|---|
| `curated.py` | ročno dodana podjetja, projektanti, popravki imenika |
| `contacts.py`, `contacts_spec.py` | kontakti s spletnih strani podjetij |
| `manual_verify.py` | ročna potrditev proizvodnje |
| `qual.py` | prednost, velikost, razlog, pristop |

## Ponovna izdelava

Zaženi iz korena repozitorija (Python 3, curl):

```bash
# 1. imenik izdelovalcev (profinautic) in spletni naslovi
python3 pipeline/scrape_pn.py si,hr,at,ch,hu,cz,sk,ba,rs,me,it,de,pl,fr,nl,be,dk,lu,li,mc data/pn/all.json
python3 pipeline/scrape_pn_ids.py si,hr,at,ch,hu,cz,sk,it,de,pl data/pn/websites.json

# 2. koordinate (GeoNames poštne številke in kraji v data/geo_dl/) in zemljevid
python3 pipeline/geocode.py data/pn/all.json data/pn/geo.json
python3 pipeline/build_map.py data/map_dl/countries-50m.json docs/map.json

# 3. baza, preverjanje spletnih strani, ponovna baza
python3 pipeline/build_leads.py
python3 pipeline/make_todo.py
python3 pipeline/verify.py data/verify_todo.json data/verify_out.json
python3 pipeline/build_leads.py && python3 pipeline/make_todo.py
python3 pipeline/crawl2.py data/crawl_todo.json && python3 pipeline/extract.py && python3 pipeline/autocontact.py
python3 pipeline/build_leads.py
```

Viri: imenik profinautic, Poslovni register (SKD 30.120), OpenStreetMap, GeoNames, world-atlas (Natural Earth), spletne strani podjetij. Stanje: oktober 2026.
