#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

logs_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "logs" / "phase2"

for joint in [2, 4]:
    files = sorted(logs_dir.glob(f"*_deadband_j{joint}_trial*.csv"))
    if not files:
        print(f"j{joint}: no data found")
        continue

    landings = []
    for f in files:
        rows = list(csv.DictReader(open(f)))
        if rows:
            landings.append(float(rows[-1][f"s{joint}"]))

    spread = max(landings) - min(landings)
    verdict = "DEADBAND (consistent)" if spread < 0.3 else "FRICTION (variable)"

    print(f"\n  j{joint} landings at -10°:")
    for i, v in enumerate(landings, 1):
        print(f"    Trial {i}: {v:+.2f}°")
    print(f"  Spread : {spread:.2f}°")
    print(f"  Verdict: {verdict}")
