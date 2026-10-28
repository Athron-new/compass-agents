#!/usr/bin/env python3
"""SessionStart-Hook des COMPASS-Plugins.

Ohne `COMPASS_URL`, `COMPASS_KEY` und `COMPASS_PERSONA` schweigt dieser Hook: Exit 0, keine
Ausgabe, kein Fehler -- fehlende Konfiguration schliesst, sie oeffnet nicht. Sind alle drei gesetzt, holt er den deterministischen Markdown-Brief der Persona
(`GET {COMPASS_URL}/personas/{COMPASS_PERSONA}/brief`) und gibt ihn als zusaetzlichen Kontext fuer die Sitzung aus.

`COMPASS_URL` ist die Basis der Core-REST-API (z.B. `https://<host>:18080/api/v1`) -- nicht
`COMPASS_MCP_URL` aus `.mcp.json`, das ist ein anderer Dienst auf einem anderen Port
(der MCP-Server und der Kern sind zwei Dienste).

Nie den Schluessel selbst ausgeben (Grundregel "Kein Secret in Ausgabe, Protokoll oder
Bericht"). Nur Python-Standardbibliothek (kein `requests`, kein `jq`) -- dieses Skript laeuft
ueberall, wo `claude` selbst laeuft, ohne eigene Installation. Zeitlimit 3 Sekunden: ein
langsamer oder nicht erreichbarer Kern darf den Sitzungsstart nicht verzoegern.

der eigentliche HTTP-Abruf (`hole_persona_brief`) ist als
eigenstaendige Funktion herausgezogen, damit ein anderes Programm denselben Weg zum Kern benutzen
kann, statt ihn ein zweites Mal zu schreiben. Aufrufer unterscheiden sich nur in der
Melde-Politik bei einem Fehlschlag: dieser Plugin-Hook schweigt bewusst (Kunden-Kontrakt, s.
Tests unten), ein anderer Aufrufer darf den Grund benennen. Verhalten
dieses Skripts bleibt dadurch unveraendert -- reiner Extract, keine Verhaltensaenderung.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# dieser Klient sagt, wer er ist.
# Ohne die Kopfzeile stand in der Lesespur `Python-urllib/3.12` -- eine
# Bibliothek, kein Programm; wer die Lesespur auswertet, verliert daran
# unnoetig Zeit. Der Name ist absichtlich sprechend und STABIL (kein Versionsteil):
# er gruppiert in `GET /statistik/nutzung` -> `abfragen_je_klient`, und ein
# Name, der sich mit jeder Version aendert, waere dort kein Klient, sondern
# viele.
KLIENT = "compass-hook/session_start"

TIMEOUT_SEKUNDEN = 3


def hole_persona_brief(
    basis: str,
    schluessel: str,
    persona: str,
    sitzung: str = "",
    timeout: int = TIMEOUT_SEKUNDEN,
    klient: str = KLIENT,
) -> str:
    """Ruft `GET {basis}/personas/{persona}/brief` ab und gibt den rohen Markdown-Body zurueck.

    `basis` ist bereits ohne trailing slash. Wirft bei jedem Fehlschlag (Netzwerk, Zeitlimit,
    Nicht-2xx-Status) die vom `urllib`-Aufruf selbst erzeugte Exception weiter -- dieser Helfer
    trifft keine Entscheidung, WIE ein Fehlschlag gemeldet wird (schweigen vs. benennen), das
    bleibt Sache des jeweiligen Aufrufers. `urllib.error.HTTPError` (Unterklasse von `URLError`)
    traegt den echten Status-Code in `.code` -- wer zwischen 404/5xx/anderem unterscheiden will,
    faengt sie zuerst ab.

    `klient` ist der Name, unter dem der Aufruf in der Lesespur
    des Kerns steht. Standard ist dieser Hook selbst -- ein anderes Programm, das
    diese Funktion importiert, uebergibt seinen eigenen Namen. Ohne den Parameter stuende sein Brief-Abruf in der
    Auskunft unter dem Namen des Plugin-Hooks, und die Frage "welches Programm
    war das" waere genau hier wieder unbeantwortet. Ein Parameter mit Standard
    statt einer zweiten Funktion: der gemeinsame Weg bleibt einer.
    """
    url = f"{basis}/personas/{persona}/brief"
    headers = {"X-Compass-Key": schluessel, "User-Agent": klient}
    if sitzung:
        headers["X-Compass-Sitzung"] = sitzung
    anfrage = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
        return antwort.read().decode("utf-8", errors="replace")


def main() -> int:
    basis = os.environ.get("COMPASS_URL", "").strip().rstrip("/")
    schluessel = os.environ.get("COMPASS_KEY", "").strip()
    persona = os.environ.get("COMPASS_PERSONA", "").strip()

    if not basis or not schluessel or not persona:
        return 0  # Ohne vollstaendige Konfiguration: schweigen, nicht scheitern.

    # die Sitzungskennung (z.B.
    # "agent-7ccc6f") -- optional, anders als die drei Variablen oben blockiert ihr Fehlen den
    # Hook nicht. Der Kern fuehrt sie nur als "erklaert", nie als Beweis. Kein erfundener
    # Rueckfall wie "unbekannt".
    sitzung = os.environ.get("COMPASS_SITZUNG", "").strip()

    try:
        brief = hole_persona_brief(basis, schluessel, persona, sitzung=sitzung)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        # Kern nicht erreichbar, Persona unbekannt (404) oder Schluessel abgelehnt (401/403):
        # der Hook meldet das nicht als Fehler -- ein fehlgeschlagener Brief darf die Sitzung
        # nicht blockieren. Der Schluessel selbst steht in keiner dieser Fehlerarten.
        return 0

    ausgabe = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": brief,
        }
    }
    print(json.dumps(ausgabe, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
