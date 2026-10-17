"""Po tedenskem zagonu odpre GitHub issue s seznamom novosti (dobiš e-poštno obvestilo GitHuba)."""
import json, os, subprocess
ev = json.load(open("data/run_events.json")) if os.path.exists("data/run_events.json") else []
ev = [e for e in ev if e.get("t") in ("1", "2", "K")]   # obvestilo samo za P1, P2 in konkurente
meta = json.load(open("docs/meta.json")) if os.path.exists("docs/meta.json") else {}
if not ev:
    print("Ni novosti – issue ne odpiram."); raise SystemExit(0)
TY = {"model": "Nov model", "jobs": "Oglas za delo", "down": "Stran ne deluje", "up": "Stran spet deluje", "verdict": "Sprememba ocene", "web": "Nova spletna stran"}
order = {"1": 0, "2": 1, "K": 2, "": 3, "3": 4}
ev.sort(key=lambda e: (order.get(e.get("t", ""), 3), e["km"] if e.get("km") is not None else 9999))
lines = [f"Osvežitev {meta.get('built_sl', '')}: {len(ev)} novosti. Stran: https://blazerculj-max.github.io/Proform/", ""]
for e in ev[:80]:
    t = {"1": "P1", "2": "P2", "K": "K", "3": "P3"}.get(e.get("t", ""), "–")
    km = f"{e['km']} km" if e.get("km") is not None else "?"
    lines.append(f"- **{e['n']}** ({t}, {km}) – {TY.get(e['ty'], e['ty'])}: {e['tx']}")
if len(ev) > 80: lines.append(f"\n… in še {len(ev) - 80}.")
title = f"Novosti {meta.get('built_sl', '')}: {len(ev)} sprememb"
subprocess.run(["gh", "issue", "create", "--title", title, "--body", "\n".join(lines)], check=True)
print("Issue odprt:", title)
