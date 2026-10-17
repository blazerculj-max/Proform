# Proform3D radar kupcev

Seznam podjetij v krogu 1000 km od Jesenic, ki potrebujejo modele, kalupe in rezkanje velikih kosov: izdelovalci plovil iz stekloplastike in kompozitov, kompozitni podizvajalci, projektanti, livarne, termoforming, vozila in letalstvo.

**Stran:** [GitHub Pages](https://blazerculj-max.github.io/Proform/) (samo za branje).
Sledenje statusa, opombe in nakupna skupina delujejo v različici na claude.ai, kjer se shranjujejo za vse z dostopom.

## Kaj je na strani

- Podjetja na zemljevidu z zračno razdaljo od Jesenic (azimutna projekcija, krogi 150/400/700/1000 km)
- **Prednost** po pregledu spletnih strani: P1 (takoj), P2 (kasneje), P3 (ni primerno), konkurent ali partner – z velikostjo, razlogom in predlogom pristopa
- **Ali res proizvajajo?** – samodejno preverjanje spletnih strani s citati (laminiranje, vetroresina, GFK, kalupi … proti charterju, trgovini, servisu); prepozna tudi prevzete in parkirane domene
- **Novosti** – vsak teden: nov model na strani, oglas za proizvodne delavce, stran ne deluje / spet deluje, sprememba ocene
- Projektanti in posredniki (J&J Design, Kiska, Felci, Polli …) s povezavo na ladjedelnice, za katere delajo
- Kontakti, ki jih podjetja objavijo na svojih straneh, in predloge prvega sporočila v SL/HR/IT/DE/EN
- Razstavljavci na sejmih (boot Düsseldorf, Salone Nautico Genova): oznaka »sejem«, hala ali kategorija, filter po sejmu
- Filtri po državah (več hkrati), razdalji, panogi, prednosti, preverjanju in statusu

## Tedenska osvežitev (GitHub Actions)

Delovni tok [`.github/workflows/weekly.yml`](.github/workflows/weekly.yml) teče vsak ponedeljek ob 4:00 UTC (ali ročno: zavihek *Actions* → *Tedenska osvežitev podatkov* → *Run workflow*):

1. preveri vse spletne strani in ponovno oceni proizvodnjo,
2. prebere strani kandidatov (P1, P2, konkurenti, potrjeni proizvajalci, podjetja brez lokacije),
3. izlušči znake (novi modeli, oglasi za delo, velikost), splošne kontakte in naslove,
4. po želji dopolni manjkajoče z Google Places,
5. primerja s prejšnjim tednom, zgradi `docs/` in shrani spremembe v repozitorij,
6. odpre **issue z novostmi** – GitHub ti pošlje e-pošto.

### Google Places (neobvezno)

Za dopolnitev manjkajočih spletnih strani in lokacij dodaj ključ Google Maps Platform (vklopljen *Places API (New)*):
*Settings → Secrets and variables → Actions → New repository secret*, ime `GOOGLE_MAPS_API_KEY`.
Vsako podjetje se poizve le enkrat (shranjeno v `data/places.json`), največ 200 na zagon (`PLACES_MAX`).
Okvirni strošek: nekaj centov na podjetje, za vse manjkajoče skupaj okoli 20 $.

## Struktura

```
web/page.html   vir strani (ista datoteka kot na claude.ai)
docs/           stran za GitHub Pages (index.html se zgradi iz web/page.html)
pipeline/       skripte; run.py požene vse korake
data/           ročno vzdrževani podatki, vmesni rezultati in zgodovina novosti
```

| Datoteka v `data/` | Vsebina |
|---|---|
| `curated.py` | ročno dodana podjetja, projektanti, popravki imenika |
| `contacts.py`, `contacts_spec.py` | kontakti s spletnih strani podjetij |
| `manual_verify.py` | ročna potrditev proizvodnje |
| `qual.py` | prednost, velikost, razlog, pristop |
| `pn/geo.json`, `pn/websites.json` | imenik izdelovalcev z lokacijami in spletnimi naslovi |
| `verify_out.json`, `signals.json`, `autocontacts.json` | rezultati preverjanja in branja strani |
| `addr_fixes.json`, `places.json` | lokacije s spletnih strani in iz Google Places |
| `web_manual.json`, `web_found.json` | ročno znane in najdene spletne strani (preverjene) |
| `web_rejected.json`, `web_notes.json` | zavrnjeni napačni zadetki in ugotovitve iskanja (stečaj, prodajalec …) |
| `snapshots.json`, `changes.json` | stanje za primerjavo in zgodovina novosti |
| `fairs/boot2026.json`, `fairs/genova2026.json` | razstavljavci sejmov (javna seznama) |
| `fairs/cand.json`, `fairs/verify_out.json` | izdelovalci plovil s sejmov v polmeru 1000 km in preverjanje njihovih strani |

## Lokalni zagon

```bash
python3 pipeline/run.py --refresh
```

Iskanje spletnih strani za podjetja brez strani (ročno znane + očitne domene, s preverjanjem vsebine):

```bash
python3 pipeline/find_websites.py --guess
```

OpenStreetMap (Nominatim) za iskanje lokacij in strani je bil preizkušen in zavrnjen: na 40 znanih podjetjih je našel 10, od tega 5 s pravilno lokacijo in nobene pravilne spletne strani.

Razstavljavci na sejmih (enkrat na leto, ko sejem objavi seznam; nato `run.py`):

```bash
python3 pipeline/fairs.py boot genova pick
```

`pick` izbere hale in kategorije s plovili, poišče lokacijo, izloči vse nad 1000 km in preveri spletne strani.
Podjetje, ki je že v bazi, dobi oznako sejma; novo se doda samo, če njegova stran kaže lastno proizvodnjo.
Preizkušeni, a neuporabni: METSTRADE in JEC (seznam se zgradi šele v brskalniku), Interboot, Biograd Boat Show, Seatec in Boot Tulln (javnega seznama ni).

Ponovno zbiranje virov (redko – imenik, register, OpenStreetMap):

```bash
python3 pipeline/scrape_pn.py si,hr,at,ch,hu,cz,sk,ba,rs,me,it,de,pl,fr,nl,be,dk,lu,li,mc data/pn/all.json
python3 pipeline/scrape_pn_ids.py si,hr,at,ch,hu,cz,sk,it,de,pl data/pn/websites.json
python3 pipeline/geocode.py data/pn/all.json data/pn/geo.json
```

Ko se podatki spremenijo, je treba stran na claude.ai objaviti znova iz `web/page.html` in datotek v `docs/`.

Viri: imenik profinautic, Poslovni register (SKD 30.120), OpenStreetMap, seznami razstavljavcev (boot Düsseldorf, Salone Nautico Genova), GeoNames (CC BY 4.0), world-atlas (Natural Earth), spletne strani podjetij, po želji Google Places.
