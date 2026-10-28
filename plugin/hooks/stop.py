#!/usr/bin/env python3
"""Stop-Hook des COMPASS-Plugins — die Klingel am Postfach.

DAS PROBLEM, GEMESSEN: `compass_nachrichten` ist ein ABHOLFACH. Eine Sitzung
erfaehrt von Post nur, wenn sie `nachrichten_abholen` ruft -- und dazu muss
sie schon einen Zug machen. Genau in dem Moment, in dem eine Sitzung fertig
wird und untaetig zu werden droht, macht sie keinen mehr. Ein Auftrag, der
dann eintrifft, liegt, bis ein Mensch das Fenster anspricht.

DER STOP-HOOK TRIFFT GENAU DIESEN MOMENT. Er laeuft, wenn die Sitzung ihre
Runde beendet -- also an der Kante zwischen "arbeitet" und "untaetig". Ist
das Postfach leer, kostet er nichts weiter als einen HTTP-Abruf und schweigt
(Exit 0, keine Ausgabe). Liegt etwas, bittet er die Sitzung, weiterzumachen,
und nennt die Zahlen.

WAS ER NICHT IST: ein Wecker. Eine Sitzung, die schon untaetig war, als die
Post kam, bekommt kein Stop-Ereignis mehr -- fuer die bleibt der Postbote
zustaendig (Klopfen von aussen). Der Hook ersetzt ihn nicht, er macht die
meisten seiner Schlaege ueberfluessig: wer gerade gearbeitet hat, merkt es
selbst.

WARUM NICHT EIN TAKT INNERHALB DER SITZUNG: gemessen laedt ein
Tick in einer laufenden Sitzung den ganzen Kontext neu (mehrere Hunderttausend
Token je Tick). Ein 5-Minuten-Takt waere Millionen Token pro Stunde, nur
um ein leeres Postfach festzustellen. Dieser Hook laeuft ausserhalb des
Modells und kostet beim leeren Postfach null Token.

KEINE ENDLOSSCHLEIFE: Claude Code setzt `stop_hook_active`, wenn die Runde
bereits durch einen Stop-Hook fortgesetzt wurde. Dann schweigt dieser Hook --
sonst haette eine Nachricht, die niemand liest, die Sitzung fuer immer in
Bewegung gehalten.

OHNE VOLLSTAENDIGE KONFIGURATION SCHWEIGT ER: Exit 0, keine Ausgabe -- wie
der SessionStart-Hook daneben. Der Schluessel steht in keiner
Ausgabe, auch in keiner Fehlermeldung.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# dieser Klient sagt, wer er ist.
# Ohne die Kopfzeile stand in der Lesespur `Python-urllib/3.12` -- eine
# Bibliothek, kein Programm; wer die Lesespur auswertet, verliert daran
# unnoetig Zeit. Der Name ist absichtlich sprechend und STABIL (kein Versionsteil):
# er gruppiert in `GET /statistik/nutzung` -> `abfragen_je_klient`, und ein
# Name, der sich mit jeder Version aendert, waere dort kein Klient, sondern
# viele.
KLIENT = "compass-hook/stop"

TIMEOUT_SEKUNDEN = 3


def hole_postfach_stand(basis: str, schluessel: str, persona: str, timeout: int = TIMEOUT_SEKUNDEN) -> dict:
    """`GET {basis}/agents/{persona}/postfach` -> `{ungelesen, auftraege_offen, …}`.

    Bewusst dieser Weg und nicht `nachrichten_abholen`: der stempelt die
    Nachrichten als zugestellt. Eine Klingel, die den Briefkasten leert, ist
    keine Klingel. Und bewusst nicht der Herzschlag: der schreibt.
    """
    ziel = f"{basis}/agents/{urllib.parse.quote(persona, safe='')}/postfach"
    anfrage = urllib.request.Request(
        ziel, headers={"X-Compass-Key": schluessel, "User-Agent": KLIENT}
    )
    with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
        return json.loads(antwort.read().decode("utf-8"))


def satz(stand: dict) -> str:
    """Der Text, den die Sitzung zu sehen bekommt. Nur gemessene Zahlen.

    DAS PROJEKT STEHT DABEI: derselbe Persona-Slug
    kann in zwei Projekten liegen. Eine Klingel ohne Projektnamen laedt genau
    die Verwechslung ein, aus der dieses Ticket entstand -- eine Sitzung las
    `0` und schloss daraus, es liege nichts an, waehrend im Nachbarprojekt
    unter demselben Namen 45 Nachrichten lagen.
    """
    teile = []
    ungelesen = stand.get("ungelesen") or 0
    offen = stand.get("auftraege_offen") or 0
    if ungelesen:
        teile.append(f"{ungelesen} ungelesene Nachricht" + ("en" if ungelesen != 1 else ""))
    if offen:
        teile.append(f"{offen} offene(r) Auftrag" if offen == 1 else f"{offen} offene Auftraege")
    kern = " und ".join(teile)
    hinweis = (
        f"Im Postfach liegt Post: {kern}. "
        "Hol sie mit `nachrichten_abholen` ab und markiere Gelesenes mit `nachricht_gelesen`. "
        "Liegt nichts fuer dich an, sag genau das und hoer auf."
    )
    projekt = stand.get("projekt")
    if projekt:
        hinweis += f" Projekt: {projekt}."
    aeltestes = stand.get("aeltestes_ungelesen_am")
    if aeltestes:
        hinweis += f" Das aelteste Ungelesene ist vom {aeltestes}."
    return hinweis


def verabschiedet_satz(stand: dict, persona: str) -> str:
    """Was eine verabschiedete Stelle statt der Klingel zu sehen bekommt.

    WARUM NICHT EINFACH SCHWEIGEN: dieser Hook laeuft am Ende
    jeder Runde und ist damit die einzige Stelle, an der eine laufende
    Sitzung ueberhaupt erfaehrt, dass etwas nicht stimmt. Schweigen hiesse,
    dass sie bis zum naechsten Neustart weiter unter einer Identitaet
    arbeitet, die es in diesem Projekt nicht mehr gibt -- und genau das ist
    im gemeldeten Fall passiert.

    Der Text sagt deshalb zwei Dinge, die nirgends sonst zusammenkommen: HIER
    bist du verabschiedet, und DORT kann derselbe Slug noch aktiv sein.
    """
    projekt = stand.get("projekt") or "diesem Projekt"
    seit = stand.get("verabschiedet_am")
    nachfolger = stand.get("nachfolger_slug")
    text = f"ACHTUNG: '{persona}' ist im Projekt '{projekt}' VERABSCHIEDET"
    if seit:
        text += f" (seit {seit})"
    text += ". Arbeite hier nicht unter diesem Namen."
    if nachfolger:
        text += f" Nachfolger ist '{nachfolger}'."
    text += (
        " Ein Herzschlag auf diese Stelle wird abgewiesen (409). Falls es denselben Slug"
        " in einem ANDEREN Projekt gibt, liegt die Post dort und nicht hier -- pruefe die"
        " Verbindung, statt die Sitzung umzubenennen."
    )
    return text


def main() -> int:
    basis = os.environ.get("COMPASS_URL", "").strip().rstrip("/")
    schluessel = os.environ.get("COMPASS_KEY", "").strip()
    persona = os.environ.get("COMPASS_PERSONA", "").strip()
    if not basis or not schluessel or not persona:
        return 0  # Ohne vollstaendige Konfiguration: schweigen.

    # Claude Code reicht das Hook-Ereignis auf stdin herein. `stop_hook_active`
    # heisst: diese Runde laeuft bereits, WEIL ein Stop-Hook sie fortgesetzt
    # hat. Ein zweites Mal fortsetzen waere eine Schleife.
    try:
        ereignis = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        ereignis = {}
    if ereignis.get("stop_hook_active"):
        return 0

    try:
        stand = hole_postfach_stand(basis, schluessel, persona)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        # Kern nicht erreichbar, Persona unbekannt (404), Schluessel abgelehnt:
        # eine stumme Klingel ist besser als eine Sitzung, die nicht enden
        # kann. Der Schluessel steht in keiner dieser Fehlerarten.
        return 0

    if not isinstance(stand, dict):
        return 0

    # EINE VERABSCHIEDETE STELLE WIRD NICHT ZUM WEITERARBEITEN AUFGEFORDERT
    #. Das geht VOR der Postfach-Pruefung, und zwar bewusst:
    # bei leerem Postfach wuerde der Hook sonst schweigen -- und Schweigen
    # ist hier die falsche Antwort, weil die Sitzung dann gar nicht erfaehrt,
    # dass sie unter einer verabschiedeten Identitaet laeuft.
    #
    # `is False` und nicht `not stand.get("aktiv")`: ein aelterer Kern ohne
    # dieses Feld liefert `None`, und das heisst "weiss ich nicht", nicht
    # "verabschiedet". Der Hook laeuft gegen Installationen, die aelter sein
    # koennen als er selbst.
    if stand.get("aktiv") is False:
        print(json.dumps({"decision": "block", "reason": verabschiedet_satz(stand, persona)}, ensure_ascii=False))
        return 0

    if not (stand.get("ungelesen") or stand.get("auftraege_offen")):
        return 0  # Leeres Postfach: schweigen, die Runde endet normal.

    print(json.dumps({"decision": "block", "reason": satz(stand)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
