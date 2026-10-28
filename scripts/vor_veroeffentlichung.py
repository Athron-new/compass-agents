#!/usr/bin/env python3
"""Pre-publication guard: nothing internal and no secret leaves with this repository.

    python3 scripts/vor_veroeffentlichung.py            # strict: placeholders count as findings
    python3 scripts/vor_veroeffentlichung.py --erlaube-platzhalter   # CI: placeholders allowed

Scans every text file in the tree (not `.git`) for: internal ticket and decision references, names of
people and customers, internal paths, IP addresses, e-mail addresses, and secret-shaped strings. Exit 0 =
no finding, 1 = findings (every one printed with file and line; values of secret-shaped strings are
NEVER printed, only their length), 2 = the scan itself could not run (no files found).

A scan that finds nothing in an empty tree says nothing: zero files is an error, not a clean result.
`scripts/tests/test_vor_veroeffentlichung.py` plants one violation per rule and proves each is found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]

# (rule, regex, secret?) -- secret=True: the matched text is never printed.
REGELN: list[tuple[str, re.Pattern[str], bool]] = [
    ("ticket", re.compile(r"\b(?:COMPASS|ATH)-\d+\b"), False),
    ("aussage", re.compile(r"\bAussage \d+\b|\bZ\.\d{2,}\b|\bFrage \d{3}\b"), False),
    ("person", re.compile(r"carsten|urbanski", re.I), False),
    ("persona", re.compile(r"\b(?:trinity|kiel|werft|morpheus|aurora|dozer|tank)\b|\bneo\b|design-cc", re.I), False),
    ("kunde", re.compile(r"athron|athlet|nordwind", re.I), False),
    ("pfad", re.compile(r"/home/[a-z]+|/opt/(?:compass|athron)|/Users/[A-Za-z]+"), False),
    ("ip", re.compile(r"\b(?!127\.0\.0\.1\b|0\.0\.0\.0\b)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), False),
    ("mail", re.compile(r"\b[A-Za-z0-9._%+-]+@(?!x\.test\b|example\.)[A-Za-z0-9.-]+\.[a-z]{2,}\b"), False),
    ("geheimnis", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:ghp|gho|ghs|xox[bap])[-_][A-Za-z0-9]{20,}|\bsk-[A-Za-z0-9]{20,}"), True),
    ("schluessel-kopfzeile", re.compile(r"X-Compass-Key['\"]?\s*[:=]\s*['\"]?(?![<$]|\{)[A-Za-z0-9_\-]{20,}"), True),
]
PLATZHALTER = re.compile(r"<ORG>|<REPO>|«[^»]*»")
# The publisher's own names are not internal data: the company, the product host, the repository.
ERLAUBT = ("Athron-new/compass-agents", "athron.io", "Athron.io GmbH", "ATHRON")
AUSGESCHLOSSEN_VERZEICHNISSE = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}
# This file and its test name the patterns on purpose.
SELBST = {Path("scripts/vor_veroeffentlichung.py"), Path("scripts/tests/test_vor_veroeffentlichung.py")}


def dateien(wurzel: Path):
    for pfad in sorted(wurzel.rglob("*")):
        if not pfad.is_file() or AUSGESCHLOSSEN_VERZEICHNISSE & set(pfad.relative_to(wurzel).parts):
            continue
        yield pfad


def pruefen(wurzel: Path, erlaube_platzhalter: bool) -> tuple[list[str], int]:
    """Returns (findings, files scanned)."""
    funde: list[str] = []
    gelesen = 0
    for pfad in dateien(wurzel):
        rel = pfad.relative_to(wurzel)
        if rel in SELBST:
            continue
        try:
            text = pfad.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary: nothing to match here
        gelesen += 1
        for nr, zeile in enumerate(text.splitlines(), 1):
            geprueft = zeile
            for erlaubt in ERLAUBT:
                geprueft = geprueft.replace(erlaubt, "")
            for name, muster, geheim in REGELN:
                for treffer in muster.finditer(geprueft):
                    wert = f"(secret-shaped, {len(treffer.group(0))} characters)" if geheim else repr(treffer.group(0))
                    funde.append(f"{rel}:{nr}: [{name}] {wert}")
            if not erlaube_platzhalter and PLATZHALTER.search(zeile):
                funde.append(f"{rel}:{nr}: [platzhalter] a placeholder is not filled yet")
    return funde, gelesen


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--erlaube-platzhalter", action="store_true", help="CI: <ORG>/<REPO> placeholders are not a finding")
    p.add_argument("--wurzel", type=Path, default=WURZEL)
    args = p.parse_args(argv)
    funde, gelesen = pruefen(args.wurzel, args.erlaube_platzhalter)
    if gelesen == 0:
        print("SCAN BROKEN: no text file was read. No result.")
        return 2
    for f in funde:
        print(f)
    print(f"\n{len(funde)} finding(s) in {gelesen} text files.")
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
