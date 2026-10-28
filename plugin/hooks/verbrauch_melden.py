#!/usr/bin/env python3
"""Stop-Hook des COMPASS-Plugins: meldet den Verbrauch dieser Sitzung.

Die echten Token-Zahlen stehen im Sitzungsprotokoll, also liest sie ein Hook und meldet
sie per `POST /agents/verbrauch`. **Keine Schaetzung, kein Agent muss etwas tun.**

WARUM ES DIESEN HOOK GIBT: `usage_report` verlangt Token-Zahlen, die ein Agent als Modell
nicht kennt. Auf der Platte stehen sie trotzdem. Eine Pflicht, die niemand erfuellen kann,
erzeugt keine Daten, sondern eine leere Spalte mit einem Vorwurf daneben.

WARUM `Stop`: er feuert je ABGESCHLOSSENEM Zug -- das reicht, damit eine lange Sitzung
zwischendurch meldet, und ist selten genug, dass das Lesen des Protokolls nicht auffaellt.
`PostToolUse` waere um ein Vielfaches haeufiger und damit Verschwendung ohne Gewinn.

WARUM KUMULIERTE SUMMEN UND KEIN DELTA: `POST /agents/verbrauch` **ersetzt**
die Zeile je (Tag, Persona, Modell, Anbieter, Sitzung) -- so ist eine
wiederholte Meldung nach einem Abbruch keine Verdopplung. Ein
Delta in eine Ersetzen-Semantik zu schreiben, ueberschriebe die vorherige
Summe mit dem letzten Zuwachs: nach drei Meldungen à 1.000 Token stuende 1.000
statt 3.000. Kumuliert braucht dieser Hook deshalb KEINEN Zustand -- keinen
Cursor, keine letzte uuid, nichts, was auseinanderlaufen kann. Er liest das
ganze Protokoll und meldet; beliebig oft, immer dasselbe Ergebnis.

WARUM JE TAG UND MODELL, und das ist kein Feinschliff: eine
Sitzung kann ueber mehrere Tage laufen. Eine
Gesamtsumme unter dem heutigen Datum haette mehrere Tage zu einem gemacht --
und weil der Kern je (Tag, ...) ersetzt, waere die Zeile von gestern mit ihrem
alten Wert stehen geblieben: dieselben Token zweimal gezaehlt. Deshalb je
(Tag, Modell) ein Aufruf, mit dem `timestamp` der Zeilen dieses Tages.

WAS ER AUSLAESST UND ZAEHLT: Zeilen mit `model = "<synthetic>"` sind keine
echten Modellaufrufe (ein kleiner Teil). Ihre Token einem Modell
zuzuschlagen, das es nicht gibt, ergaebe eine Zeile ohne Preis -- also eine
Luecke, die wie ein fehlender Preis aussieht. Sie werden uebersprungen und
**gezaehlt**; die Zahl steht in der Ausgabe, nicht im Schweigen.

ER SCHWEIGT BEI FEHLENDER KONFIGURATION (Exit 0, keine Ausgabe) und haelt die
Sitzung niemals auf -- dieselbe Politik wie die beiden anderen Hooks. Und er
gibt nie den Schluessel aus (Grundregel „Kein Secret in Ausgabe, Protokoll
oder Bericht").
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

# dieser Klient sagt, wer er ist.
# Ohne die Kopfzeile stand in der Lesespur `Python-urllib/3.12` -- eine
# Bibliothek, kein Programm; wer die Lesespur auswertet, verliert daran
# unnoetig Zeit. Der Name ist absichtlich sprechend und STABIL (kein Versionsteil):
# er gruppiert in `GET /statistik/nutzung` -> `abfragen_je_klient`, und ein
# Name, der sich mit jeder Version aendert, waere dort kein Klient, sondern
# viele.
KLIENT = "compass-hook/verbrauch_melden"

TIMEOUT_SEKUNDEN = 5

# Die vier Token-Arten im Sitzungsprotokoll (`message.usage`) und ihre Namen im
# Kern. Alle vier stehen in jeder Zeile eines Modellaufrufs.
FELDER = {
    "input_tokens": "token_ein",
    "output_tokens": "token_aus",
    "cache_read_input_tokens": "token_cache_gelesen",
    "cache_creation_input_tokens": "token_cache_geschrieben",
}

# Kein echter Modellaufruf -- Claude Code schreibt so u.a. Abbrueche und
# eigene Hinweise.
SYNTHETISCH = "<synthetic>"

# Anbieter aus dem Modellnamen. Eine KURZE, ausdrueckliche Tabelle statt einer
# Ableitung: `anbieter` ist im Kern eine freie Zeichenkette, und ein geratener
# Anbieter waere eine erfundene Zuordnung. Was hier nicht steht, wird
# `unbekannt` -- dann findet der Kern keinen Preis und sagt das (`kein_preis`),
# statt einen falschen zu nehmen. `COMPASS_ANBIETER` ueberschreibt alles.
ANBIETER_NACH_PRAEFIX = (
    ("claude", "anthropic"),
    ("gpt", "openai"),
    ("o1", "openai"),
    ("deepseek", "deepseek"),
    ("gemini", "google"),
)


def anbieter_fuer(modell: str) -> str:
    vorgabe = os.environ.get("COMPASS_ANBIETER", "").strip()
    if vorgabe:
        return vorgabe
    klein = modell.lower()
    for praefix, anbieter in ANBIETER_NACH_PRAEFIX:
        if klein.startswith(praefix):
            return anbieter
    return "unbekannt"


def summiere(protokoll: Path) -> tuple[dict[tuple[str, str], dict[str, Any]], int, int]:
    """Summiert `message.usage` je (Tag, Modell).

    Zurueck: (summen, uebersprungen_synthetisch, unlesbare_zeilen).

    Eine unlesbare Zeile wird gezaehlt und uebersprungen, nicht als Fehler
    behandelt: das Protokoll wird waehrend des Lesens weitergeschrieben, und
    eine halb geschriebene letzte Zeile ist normal. Sie STILL zu verschlucken
    waere es nicht -- die Zahl steht in der Ausgabe.
    """
    summen: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"token_ein": 0, "token_aus": 0, "token_cache_gelesen": 0,
                 "token_cache_geschrieben": 0, "aufrufe": 0, "zeitpunkt": ""}
    )
    synthetisch = 0
    unlesbar = 0

    with protokoll.open(encoding="utf-8", errors="replace") as datei:
        for zeile in datei:
            zeile = zeile.strip()
            if not zeile:
                continue
            try:
                eintrag = json.loads(zeile)
            except ValueError:
                unlesbar += 1
                continue
            nachricht = eintrag.get("message")
            if not isinstance(nachricht, dict):
                continue
            usage = nachricht.get("usage")
            if not isinstance(usage, dict):
                continue
            modell = (nachricht.get("model") or "").strip()
            if not modell:
                unlesbar += 1
                continue
            if modell == SYNTHETISCH:
                synthetisch += 1
                continue
            zeitpunkt = (eintrag.get("timestamp") or "").strip()
            tag = zeitpunkt[:10]
            if len(tag) != 10:
                # Ohne Datum laesst sich die Zeile keinem Tag zuordnen, und ein
                # geratenes Datum waere die Verdopplung, gegen die die
                # Tagesgruppierung gebaut ist.
                unlesbar += 1
                continue
            eimer = summen[(tag, modell)]
            for quelle, ziel in FELDER.items():
                wert = usage.get(quelle)
                if isinstance(wert, int) and wert >= 0:
                    eimer[ziel] += wert
            eimer["aufrufe"] += 1
            # Der SPAETESTE Zeitpunkt des Tages: er liegt sicher an diesem Tag
            # und ist damit der richtige `zeitpunkt` fuer die Meldung.
            if zeitpunkt > eimer["zeitpunkt"]:
                eimer["zeitpunkt"] = zeitpunkt
    return summen, synthetisch, unlesbar


def melde(basis: str, schluessel: str, nutzlast: dict[str, Any], timeout: int = TIMEOUT_SEKUNDEN) -> None:
    anfrage = urllib.request.Request(
        f"{basis}/agents/verbrauch",
        data=json.dumps(nutzlast).encode("utf-8"),
        headers={
            "X-Compass-Key": schluessel,
            "Content-Type": "application/json",
            "User-Agent": KLIENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
        antwort.read()


def protokoll_aus_eingabe(roh: str) -> Path | None:
    """Der Pfad des Sitzungsprotokolls aus der Hook-Eingabe (`transcript_path`).

    Er steht in KEINER Umgebungsvariable, und ihn aus der Sitzungskennung zu
    bauen waere geraten -- die COMPASS-Sitzung und die Protokoll-UUID sind
    zwei verschiedene Kennungen. `None`, wenn die Eingabe ihn nicht traegt
    oder die Datei nicht da ist.
    """
    try:
        eingabe = json.loads(roh or "{}")
    except ValueError:
        return None
    pfad = (eingabe.get("transcript_path") or "").strip()
    if not pfad:
        return None
    protokoll = Path(pfad).expanduser()
    return protokoll if protokoll.is_file() else None


def melde_protokoll(basis: str, schluessel: str, persona: str, sitzung: str,
                    protokoll: Path) -> tuple[int, int, int, int, int]:
    """Summiert das Protokoll und meldet jede (Tag, Modell)-Gruppe.

    Zurueck: (gemeldet, gruppen, gescheitert, synthetisch, unlesbar).

    DIE EINE MELDELOGIK, zwei moegliche Einstiege: `main()` hier ist der
    Plugin-Vertrag (alles aus der Umgebung, Schweigen ohne Konfiguration);
    wer den Hook in ein eigenes Programm einbettet, ruft diese Funktion und
    entscheidet selbst, wie ein Fehlschlag gemeldet wird. Was gemeldet wird,
    steht nur hier.
    """
    summen, synthetisch, unlesbar = summiere(protokoll)
    gemeldet = 0
    gescheitert = 0
    for (tag, modell), werte in sorted(summen.items()):
        nutzlast = {
            "persona_slug": persona,
            "sitzung": sitzung,
            "anbieter": anbieter_fuer(modell),
            "modell": modell,
            "token_ein": werte["token_ein"],
            "token_aus": werte["token_aus"],
            "token_cache_gelesen": werte["token_cache_gelesen"],
            "token_cache_geschrieben": werte["token_cache_geschrieben"],
            "aufrufe": werte["aufrufe"],
            "zeitpunkt": werte["zeitpunkt"],
        }
        try:
            melde(basis, schluessel, nutzlast)
            gemeldet += 1
        except (urllib.error.URLError, OSError, ValueError):
            # Ein nicht erreichbarer Kern darf den Zug nicht aufhalten, und der
            # naechste `Stop` meldet ohnehin dieselben kumulierten Summen --
            # nichts geht verloren. Der Grund wird NICHT ausgegeben: er
            # koennte die URL und damit den Host tragen, und diese Ausgabe
            # landet im Sitzungsverlauf.
            gescheitert += 1
    return gemeldet, len(summen), gescheitert, synthetisch, unlesbar


def bericht(gemeldet: int, gruppen: int, gescheitert: int, synthetisch: int, unlesbar: int) -> str:
    """Die eine Zeile -- oder "", wenn es nichts zu melden gibt.

    Im Normalfall schweigt der Hook: er laeuft mitten in der Arbeit. Ein
    Fehlschlag oder eine unlesbare Zeile sind kein Normalfall, und sie STILL
    zu verschlucken waere die Art Schweigen, gegen die dieser Hook gebaut ist.

    SYNTHETISCHE ZEILEN LOESEN DIE AUSGABE NICHT MEHR AUS:
    sie stehen in JEDEM Protokoll, in einem kleinen Teil der Zeilen. Als
    Ausloeser hiess das eine Zeile nach jedem Zug, also Laerm bei
    vollstaendigem Erfolg. Sie stehen weiterhin IM Text, wenn ohnehin etwas zu
    melden ist: uebersprungen und gezaehlt, aber kein Befund.
    """
    if not (gescheitert or unlesbar):
        return ""
    return (
        f"COMPASS-Verbrauch: {gemeldet} von {gruppen} Tag/Modell-Gruppen gemeldet"
        + (f", {gescheitert} fehlgeschlagen" if gescheitert else "")
        + (f", {synthetisch} synthetische Zeilen uebersprungen" if synthetisch else "")
        + (f", {unlesbar} Zeilen unlesbar" if unlesbar else "")
    )


def main() -> int:
    persona = os.environ.get("COMPASS_PERSONA", "").strip()
    schluessel = os.environ.get("COMPASS_KEY", "").strip()
    basis = os.environ.get("COMPASS_URL", "").strip().rstrip("/")
    sitzung = (
        os.environ.get("COMPASS_SITZUNG", "").strip()
        or os.environ.get("CLAUDE_SESSION_NAME", "").strip()
    )
    if not (persona and schluessel and basis and sitzung):
        return 0

    protokoll = protokoll_aus_eingabe(sys.stdin.read())
    if protokoll is None:
        return 0

    zeile = bericht(*melde_protokoll(basis, schluessel, persona, sitzung, protokoll))
    if zeile:
        print(zeile, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
