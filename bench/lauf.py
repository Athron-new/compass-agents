#!/usr/bin/env python3
"""Reality bench: run the cases in `faelle/` against a COMPASS instance.

ONLY against a throwaway instance: registering a check is a write.

    COMPASS_HOST_RO_ROOT=$PWD/bench/world   # set on the COMPASS core, then restart it
    python3 bench/lauf.py --base-url http://localhost:18080/api/v1 --key <read-write-key>

Each case brings its own command (`pruefweg_befehl`) and expectation (`erwartung`). The core runs
the command without a shell, with the working directory set to `COMPASS_HOST_RO_ROOT`, so the
relative paths in the cases resolve inside `bench/world/`.

Positive controls before the run: the instance must answer AND all five case files must be found.
During the run: a case that could not be measured (state `unbekannt`) is counted as a miss, never as a
hit -- the core flags an unmeasured check as a deviation, so a bench that only compared the flag would
"succeed" on an instance that measured nothing. One case is a CONTROL
(`erwartete_abweichung: false`): it must come back WITHOUT a deviation, otherwise the bench cannot
tell a check that detects drift from a check that always raises an alarm.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

KLIENT = "compass-bench/lauf"
FAELLE = pathlib.Path(__file__).parent / "faelle"
ERWARTETE_FAELLE = 5


def ruf(base: str, key: str, pfad: str, koerper: dict | None = None) -> dict:
    daten = json.dumps(koerper).encode() if koerper is not None else None
    req = urllib.request.Request(
        base.rstrip("/") + pfad,
        data=daten,
        method="POST" if koerper is not None or pfad.endswith("/run") else "GET",
        headers={"Content-Type": "application/json", "X-Compass-Key": key, "User-Agent": KLIENT},
    )
    with urllib.request.urlopen(req, timeout=60) as antwort:
        return json.loads(antwort.read() or b"{}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--base-url", required=True, help="e.g. http://localhost:18080/api/v1")
    p.add_argument("--key", required=True, help="read-write key of the THROWAWAY instance")
    args = p.parse_args()

    dateien = sorted(FAELLE.glob("*.json"))
    if len(dateien) != ERWARTETE_FAELLE:
        print(f"SETUP BROKEN: found {len(dateien)} case files, expected {ERWARTETE_FAELLE}. No result.")
        return 2
    try:
        ruf(args.base_url, args.key, "/pruefwege")
    except (urllib.error.URLError, OSError) as exc:
        print(f"SETUP BROKEN: the instance does not answer ({exc}). No result.")
        return 2

    treffer = 0
    for datei in dateien:
        fall = json.loads(datei.read_text(encoding="utf-8"))
        slug, befehl = fall["sache"], fall.get("pruefweg_befehl")
        if not befehl:
            print(f"{slug}: no pruefweg_befehl -- skipped, NOT counted as green")
            continue
        ruf(args.base_url, args.key, "/pruefwege", {
            "slug": slug, "titel": slug, "typ": "shell", "befehl": befehl,
            "erwartung": fall["erwartung"], "laufumgebung": fall.get("laufumgebung", "host-ro"),
        })
        erg = ruf(args.base_url, args.key, f"/pruefwege/{slug}/run")
        ist, soll = erg.get("abweichung"), fall["erwartete_abweichung"]
        # `abweichung` is also true when nothing could be measured (unknown counts as a deviation). The state of the check
        # says which it was: only `wahr`/`falsch` is a measurement.
        stand = next((x for x in ruf(args.base_url, args.key, "/pruefwege") if x.get("slug") == slug), {})
        gemessen = stand.get("erfuellt") in ("wahr", "falsch")
        passt = gemessen and ist == soll
        treffer += passt
        print(f"{slug}: measured={gemessen} deviation={ist} expected={soll} -> {'hit' if passt else 'MISS'}")
        print(f"    {erg.get('ergebnis', '').strip().splitlines()[:3]}")

    print(f"\n{treffer} of {len(dateien)} cases come back as expected.")
    return 0 if treffer == len(dateien) else 1


if __name__ == "__main__":
    sys.exit(main())
