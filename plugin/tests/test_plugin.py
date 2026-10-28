"""Tests für das COMPASS-Claude-Code-Plugin — nur Python-Standardbibliothek,
kein eigenes requirements.txt (Muster wie `pruefwege/`, siehe .github/workflows/tests.yml).

Deckt ab:
1. jede JSON-Datei des Plugins ist gültig und trägt die laut Claude-Code-Doku
   (code.claude.com/docs/en/plugins-reference, .../plugin-marketplaces) verlangten Pflichtfelder.
2. jedes in SKILL.md genannte MCP-Werkzeug existiert wirklich im MCP-Server.
3. der SessionStart-Hook schweigt ohne vollständige Konfiguration (Exit 0, leere Ausgabe) und
   antwortet mit dem Brief, wenn COMPASS_URL/COMPASS_KEY/COMPASS_PERSONA gesetzt sind — gegen
   einen lokalen Fake-Core (http.server in einem Thread) — ohne den Schlüssel in der Ausgabe.
4. kein Schlüssel- oder fremdes Domain-Literal liegt irgendwo unter plugin/.
"""
from __future__ import annotations

import contextlib
import http.server
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parent
MCP_WERKZEUGE = PLUGIN_ROOT / "tests" / "mcp_werkzeuge.txt"


def _load_json(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. JSON-Dateien: gültig + Pflichtfelder laut Doku
# ---------------------------------------------------------------------------


def test_marketplace_json_gueltig_und_pflichtfelder():
    daten = _load_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")
    assert isinstance(daten.get("name"), str) and daten["name"]
    assert isinstance(daten.get("owner"), dict)
    assert isinstance(daten["owner"].get("name"), str) and daten["owner"]["name"]
    plugins = daten.get("plugins")
    assert isinstance(plugins, list) and plugins
    for eintrag in plugins:
        assert isinstance(eintrag.get("name"), str) and eintrag["name"]
        assert "source" in eintrag and eintrag["source"]
    compass = next(p for p in plugins if p["name"] == "compass")
    assert compass["source"] == "./plugin"


def test_plugin_json_gueltig_und_pflichtfelder():
    daten = _load_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
    assert daten.get("name") == "compass"
    assert isinstance(daten.get("description"), str) and daten["description"]
    assert daten.get("version") == "0.1.0"
    assert isinstance(daten.get("author"), dict)
    assert daten["author"].get("name") == "ATHRON"
    # Die Lizenz steht in `LICENSE` im Wurzelverzeichnis; das Feld hier nennt dieselbe.
    assert daten.get("license") == "MIT"


def test_mcp_json_gueltig_und_nur_variablen_substitution():
    daten = _load_json(PLUGIN_ROOT / ".mcp.json")
    server = daten["mcpServers"]["compass"]
    assert server.get("type") == "http"
    assert server.get("url") == "${COMPASS_MCP_URL}"
    assert server.get("headers", {}).get("X-Compass-Key") == "${COMPASS_KEY}"


def test_hooks_json_gueltig_und_session_start_registriert():
    daten = _load_json(PLUGIN_ROOT / "hooks" / "hooks.json")
    session_start = daten["hooks"]["SessionStart"]
    assert isinstance(session_start, list) and session_start
    befehle = [h["command"] for eintrag in session_start for h in eintrag["hooks"]]
    assert any("session_start.py" in b and "CLAUDE_PLUGIN_ROOT" in b for b in befehle)


# ---------------------------------------------------------------------------
# 2. SKILL.md nennt nur Werkzeuge, die es im MCP-Server wirklich gibt
# ---------------------------------------------------------------------------


def _mcp_werkzeugnamen() -> set[str]:
    """Die Namen der Werkzeuge des COMPASS-MCP-Servers. Der Server liegt nicht in diesem Repo; die Liste ist ein Abzug
    (`tests/mcp_werkzeuge.txt`, eine Funktion je Zeile) und wird vom Server-Repo aus erneuert. Fehlt die Datei oder ist sie
    leer, ist das ein FEHLER -- ein Test, der ohne Eingabe nichts prueft, meldet "in Ordnung" ueber etwas, das er nie sah."""
    namen = {z.strip() for z in MCP_WERKZEUGE.read_text(encoding="utf-8").splitlines() if z.strip()}
    assert len(namen) >= 20, f"Werkzeugliste zu kurz oder leer: {len(namen)}"
    return namen


def _skill_genannte_werkzeuge() -> list[str]:
    text = (PLUGIN_ROOT / "skills" / "compass" / "SKILL.md").read_text(encoding="utf-8")
    abschnitt = text.split('## Werkzeuge (exakte Namen)', 1)[1]
    abschnitt = abschnitt.split("\n## ", 1)[0]
    return re.findall(r"^- `(\w+)`\s*$", abschnitt, re.MULTILINE)


def test_skill_werkzeugliste_ist_nicht_leer():
    genannte = _skill_genannte_werkzeuge()
    assert len(genannte) >= 5


def test_skill_nennt_nur_existierende_mcp_werkzeuge():
    genannte = _skill_genannte_werkzeuge()
    vorhandene = _mcp_werkzeugnamen()
    fehlende = [name for name in genannte if name not in vorhandene]
    assert not fehlende, f"SKILL.md nennt Werkzeuge, die es im MCP-Server nicht gibt: {fehlende}"


# ---------------------------------------------------------------------------
# 3. SessionStart-Hook
# ---------------------------------------------------------------------------

HOOK_SKRIPT = PLUGIN_ROOT / "hooks" / "session_start.py"


def _hook_lauf(env: dict) -> subprocess.CompletedProcess:
    vollstaendige_env = {"PATH": os.environ.get("PATH", "")}
    vollstaendige_env.update(env)
    return subprocess.run(
        [sys.executable, str(HOOK_SKRIPT)],
        env=vollstaendige_env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_hook_schweigt_ganz_ohne_variablen():
    ergebnis = _hook_lauf({})
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert ergebnis.stderr == ""


def test_hook_schweigt_bei_teilweiser_konfiguration():
    ergebnis = _hook_lauf({"COMPASS_URL": "http://127.0.0.1:9", "COMPASS_KEY": "irgendein-wert"})
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


FAKE_SCHLUESSEL = "test-fake-schluessel-9f3a-nicht-echt"
FAKE_PERSONA = "test-persona"
FAKE_BRIEF = "# Brief der Persona test-persona\n\nEin Inhalt, den es nur im Fake-Core gibt.\n"


class _FakeCoreHandler(http.server.BaseHTTPRequestHandler):
    # zeichnet die zuletzt empfangenen Header auf, damit Tests pruefen koennen, ob
    # der Hook `X-Compass-Sitzung` mitschickt (oder eben nicht) -- Klassenattribut, weil jede
    # Anfrage eine neue Handler-Instanz bekommt (BaseHTTPRequestHandler-Bauart).
    letzte_headers: dict[str, str] = {}

    def do_GET(self):  # noqa: N802 (Signatur von BaseHTTPRequestHandler)
        erwarteter_pfad = f"/personas/{FAKE_PERSONA}/brief"
        type(self).letzte_headers = dict(self.headers.items())
        if self.path == erwarteter_pfad and self.headers.get("X-Compass-Key") == FAKE_SCHLUESSEL:
            body = FAKE_BRIEF.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):  # ruhig halten, keine Test-Ausgabe zumuellen
        pass


@contextlib.contextmanager
def _fake_core():
    server = http.server.HTTPServer(("127.0.0.1", 0), _FakeCoreHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_hook_gibt_brief_aus_und_verraet_den_schluessel_nicht():
    with _fake_core() as port:
        ergebnis = _hook_lauf(
            {
                "COMPASS_URL": f"http://127.0.0.1:{port}",
                "COMPASS_KEY": FAKE_SCHLUESSEL,
                "COMPASS_PERSONA": FAKE_PERSONA,
            }
        )
    assert ergebnis.returncode == 0
    assert FAKE_SCHLUESSEL not in ergebnis.stdout
    assert FAKE_SCHLUESSEL not in ergebnis.stderr
    ausgabe = json.loads(ergebnis.stdout)
    spezifisch = ausgabe["hookSpecificOutput"]
    assert spezifisch["hookEventName"] == "SessionStart"
    assert FAKE_BRIEF.strip() in spezifisch["additionalContext"]


def test_hook_schweigt_wenn_kern_ablehnt():
    """Falscher Schluessel -> 404 vom Fake-Core (Handler oben) -> Hook schweigt, statt einen
    Fehler zu zeigen oder den (falschen) Schluessel in einer Fehlermeldung zu wiederholen."""
    with _fake_core() as port:
        ergebnis = _hook_lauf(
            {
                "COMPASS_URL": f"http://127.0.0.1:{port}",
                "COMPASS_KEY": "falscher-schluessel",
                "COMPASS_PERSONA": FAKE_PERSONA,
            }
        )
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert "falscher-schluessel" not in ergebnis.stderr


# ---------------------------------------------------------------------------
# der Hook haengt `X-Compass-Sitzung` an, sofern eine
# Sitzungskennung bekannt ist (COMPASS_SITZUNG) -- optional,
# anders als die drei Pflicht-Variablen blockiert ihr Fehlen den Hook nicht.
# ---------------------------------------------------------------------------


def _grundkonfiguration(port: int) -> dict:
    return {
        "COMPASS_URL": f"http://127.0.0.1:{port}",
        "COMPASS_KEY": FAKE_SCHLUESSEL,
        "COMPASS_PERSONA": FAKE_PERSONA,
    }


def test_hook_ohne_sitzungs_variablen_sendet_keinen_header():
    with _fake_core() as port:
        ergebnis = _hook_lauf(_grundkonfiguration(port))
    assert ergebnis.returncode == 0
    assert "X-Compass-Sitzung" not in _FakeCoreHandler.letzte_headers


def test_hook_mit_compass_sitzung_sendet_den_header():
    with _fake_core() as port:
        env = _grundkonfiguration(port)
        env["COMPASS_SITZUNG"] = "agent-7ccc6f"
        ergebnis = _hook_lauf(env)
    assert ergebnis.returncode == 0
    assert _FakeCoreHandler.letzte_headers.get("X-Compass-Sitzung") == "agent-7ccc6f"


def test_hook_liest_keine_fremde_sitzungsvariable():
    """Nur `COMPASS_SITZUNG` zaehlt. Eine Variable eines anderen Werkzeugs wird nicht als Sitzungskennung gelesen --
    ein erfundener Rueckfall waere eine falsche Angabe in der Lesespur des Kerns."""
    with _fake_core() as port:
        env = _grundkonfiguration(port)
        env["GIT_GUARD_ACTOR"] = "fremdes-werkzeug"
        ergebnis = _hook_lauf(env)
    assert ergebnis.returncode == 0
    assert "X-Compass-Sitzung" not in _FakeCoreHandler.letzte_headers


# ---------------------------------------------------------------------------
# 4. Kein Schlüssel-/Domain-Literal unter plugin/
# ---------------------------------------------------------------------------

_ERLAUBTE_DOMAINEN = {"docs.claude.com", "code.claude.com", "github.com", "claude.ai"}


_AUSGESCHLOSSENE_TOP_LEVEL = {"tests", ".pytest_cache", "__pycache__", ".git"}


def _dateien_ausser_tests() -> list[Path]:
    ergebnis = []
    for pfad in PLUGIN_ROOT.rglob("*"):
        if not pfad.is_file():
            continue
        teile = pfad.relative_to(PLUGIN_ROOT).parts
        if teile[0] in _AUSGESCHLOSSENE_TOP_LEVEL or any(t == "__pycache__" for t in teile):
            continue
        ergebnis.append(pfad)
    return ergebnis


def test_keine_fremde_domain_im_plugin_ordner():
    muster = re.compile(r"https?://([A-Za-z0-9.\-]+)")
    for pfad in _dateien_ausser_tests():
        if pfad.suffix not in {".json", ".md", ".py"}:
            continue
        for host in muster.findall(pfad.read_text(encoding="utf-8")):
            erlaubt = any(host == d or host.endswith("." + d) for d in _ERLAUBTE_DOMAINEN)
            assert erlaubt, f"{pfad}: unbekannte Domain im Literal: {host!r}"


def test_x_compass_key_header_ist_immer_nur_die_variable():
    muster = re.compile(r'"X-Compass-Key"\s*:\s*"([^"]*)"')
    fundstellen = 0
    for pfad in _dateien_ausser_tests():
        if pfad.suffix != ".json":
            continue
        for wert in muster.findall(pfad.read_text(encoding="utf-8")):
            fundstellen += 1
            assert wert == "${COMPASS_KEY}", f"{pfad}: X-Compass-Key traegt einen Literal-Wert: {wert!r}"
    assert fundstellen >= 1


def test_kein_wert_der_umgebungsvariablen_im_plugin_ordner():
    """Grobe Gegenprobe: keine Datei enthaelt einen Wert, wie ihn `COMPASS_KEY` real haette,
    literal neben dem Variablennamen -- nur `${COMPASS_KEY}` ist erlaubt."""
    for pfad in _dateien_ausser_tests():
        if pfad.suffix not in {".json", ".md", ".py"}:
            continue
        text = pfad.read_text(encoding="utf-8")
        for zeile in text.splitlines():
            if "COMPASS_KEY" not in zeile:
                continue
            rest = zeile.replace("${COMPASS_KEY}", "").replace("COMPASS_KEY", "")
            verdaechtig = re.search(r"[A-Za-z0-9_\-]{24,}", rest)
            assert not verdaechtig, f"{pfad}: moeglicher eingebrannter Schluessel in Zeile: {zeile!r}"


# ---------------------------------------------------------------------------
# 5. Stop-Hook — die Klingel am Postfach
#
# Ein Postfach kann viele ungelesene Nachrichten tragen, ohne dass es jemand
# merkt, solange niemand von aussen anklopft. Das
# Postfach selbst hat keine Klingel: eine Sitzung erfaehrt von Post nur,
# wenn sie danach fragt, und eine gerade fertig gewordene fragt nicht mehr.
#
# Der Stop-Hook laeuft genau an dieser Kante. Er ersetzt den Postboten
# nicht (eine SCHON untaetige Sitzung bekommt kein Stop-Ereignis), aber er
# macht die meisten seiner Schlaege ueberfluessig.
# ---------------------------------------------------------------------------

STOP_SKRIPT = PLUGIN_ROOT / "hooks" / "stop.py"


class _FakePostfachHandler(http.server.BaseHTTPRequestHandler):
    """Antwortet auf `GET /agents/<persona>/postfach`. `stand` ist umschaltbar."""

    stand: dict = {"ungelesen": 0, "auftraege_offen": 0}
    gerufene_pfade: list = []

    def do_GET(self):  # noqa: N802
        type(self).gerufene_pfade.append(self.path)
        erwartet = f"/agents/{FAKE_PERSONA}/postfach"
        if self.path == erwartet and self.headers.get("X-Compass-Key") == FAKE_SCHLUESSEL:
            body = json.dumps(type(self).stand).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


@contextlib.contextmanager
def _fake_postfach(stand: dict):
    _FakePostfachHandler.stand = stand
    _FakePostfachHandler.gerufene_pfade = []
    server = http.server.HTTPServer(("127.0.0.1", 0), _FakePostfachHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        thread.join(timeout=5)


def _stop_lauf(env: dict, ereignis: dict | None = None) -> subprocess.CompletedProcess:
    vollstaendige_env = {"PATH": os.environ.get("PATH", "")}
    vollstaendige_env.update(env)
    return subprocess.run(
        [sys.executable, str(STOP_SKRIPT)],
        env=vollstaendige_env,
        input=json.dumps(ereignis or {}),
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_stop_hook_schweigt_ganz_ohne_variablen():
    ergebnis = _stop_lauf({})
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert ergebnis.stderr == ""


def test_stop_hook_schweigt_bei_leerem_postfach():
    """Der haeufigste Fall, und er muss lautlos sein: die Runde endet normal."""
    with _fake_postfach({"ungelesen": 0, "auftraege_offen": 0}) as port:
        ergebnis = _stop_lauf({
            "COMPASS_URL": f"http://127.0.0.1:{port}",
            "COMPASS_KEY": FAKE_SCHLUESSEL,
            "COMPASS_PERSONA": FAKE_PERSONA,
        })
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_stop_hook_klingelt_bei_ungelesener_post():
    with _fake_postfach({"ungelesen": 3, "auftraege_offen": 1,
                         "aeltestes_ungelesen_am": "2026-09-25T11:22:00Z"}) as port:
        ergebnis = _stop_lauf({
            "COMPASS_URL": f"http://127.0.0.1:{port}",
            "COMPASS_KEY": FAKE_SCHLUESSEL,
            "COMPASS_PERSONA": FAKE_PERSONA,
        })
    assert ergebnis.returncode == 0
    ausgabe = json.loads(ergebnis.stdout)
    assert ausgabe["decision"] == "block"
    assert "3 ungelesene Nachrichten" in ausgabe["reason"]
    assert "nachrichten_abholen" in ausgabe["reason"]
    assert "2026-09-25T11:22:00Z" in ausgabe["reason"]
    assert FAKE_SCHLUESSEL not in ergebnis.stdout
    assert FAKE_SCHLUESSEL not in ergebnis.stderr


def test_stop_hook_klingelt_auch_bei_einem_auftrag_ohne_ungelesene():
    """Ein Auftrag kann gelesen und trotzdem unbeansprucht sein — genau der
    Fall aus dem Ticket (drei Auftraege lagen 26 Stunden auf `offen`)."""
    with _fake_postfach({"ungelesen": 0, "auftraege_offen": 2}) as port:
        ergebnis = _stop_lauf({
            "COMPASS_URL": f"http://127.0.0.1:{port}",
            "COMPASS_KEY": FAKE_SCHLUESSEL,
            "COMPASS_PERSONA": FAKE_PERSONA,
        })
    ausgabe = json.loads(ergebnis.stdout)
    assert ausgabe["decision"] == "block"
    assert "2 offene Auftraege" in ausgabe["reason"]


def test_stop_hook_haelt_die_runde_nicht_zweimal_auf():
    """`stop_hook_active` heisst: diese Runde laeuft schon, WEIL ein
    Stop-Hook sie fortgesetzt hat. Ein zweites Mal waere eine Schleife —
    eine Nachricht, die niemand liest, haette die Sitzung fuer immer in
    Bewegung gehalten."""
    with _fake_postfach({"ungelesen": 5, "auftraege_offen": 0}) as port:
        ergebnis = _stop_lauf(
            {"COMPASS_URL": f"http://127.0.0.1:{port}",
             "COMPASS_KEY": FAKE_SCHLUESSEL, "COMPASS_PERSONA": FAKE_PERSONA},
            ereignis={"stop_hook_active": True},
        )
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert _FakePostfachHandler.gerufene_pfade == [], "bei aktiver Schleife gar nicht erst fragen"


def test_stop_hook_schweigt_wenn_der_kern_nicht_antwortet():
    """Eine stumme Klingel ist besser als eine Sitzung, die nicht enden kann."""
    ergebnis = _stop_lauf({
        "COMPASS_URL": "http://127.0.0.1:9",   # Port 9 = discard, nimmt nichts an
        "COMPASS_KEY": FAKE_SCHLUESSEL,
        "COMPASS_PERSONA": FAKE_PERSONA,
    })
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_stop_hook_liest_nur_und_stempelt_nichts():
    """Die Klingel darf den Briefkasten nicht leeren.

    Geprueft am aufgerufenen Pfad: `…/postfach` (reines Lesen), NICHT
    `…/nachrichten?sitzung=` (das stempelt als zugestellt) und nicht
    `POST /agents/herzschlag` (das schreibt die Sitzungszeile).
    """
    with _fake_postfach({"ungelesen": 1, "auftraege_offen": 0}) as port:
        _stop_lauf({"COMPASS_URL": f"http://127.0.0.1:{port}",
                    "COMPASS_KEY": FAKE_SCHLUESSEL, "COMPASS_PERSONA": FAKE_PERSONA})
    assert _FakePostfachHandler.gerufene_pfade == [f"/agents/{FAKE_PERSONA}/postfach"]


def test_stop_hook_ist_in_hooks_json_registriert():
    daten = _load_json(PLUGIN_ROOT / "hooks" / "hooks.json")
    stop = daten["hooks"]["Stop"]
    assert isinstance(stop, list) and stop
    befehle = [h["command"] for eintrag in stop for h in eintrag["hooks"]]
    assert any("stop.py" in b for b in befehle), befehle
    assert all("${CLAUDE_PLUGIN_ROOT}" in b for b in befehle), "Hook muss plugin-relativ laufen"

# 6. Stop-Hook: Verbrauch melden
#
# Der Hook behebt eine Ursache einer leeren Kosten-Spalte: niemand hatte
# gemeldet, weil `usage_report` Token-Zahlen verlangt, die ein Agent als
# Modell nicht kennt -- auf der Platte stehen sie trotzdem.
# ---------------------------------------------------------------------------

VERBRAUCH_SKRIPT = PLUGIN_ROOT / "hooks" / "verbrauch_melden.py"


def _verbrauch_lauf(env: dict, stdin: str = "") -> subprocess.CompletedProcess:
    vollstaendige_env = {"PATH": os.environ.get("PATH", "")}
    vollstaendige_env.update(env)
    return subprocess.run(
        [sys.executable, str(VERBRAUCH_SKRIPT)],
        env=vollstaendige_env,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _protokoll_schreiben(pfad, zeilen):
    import json as _json

    with open(pfad, "w", encoding="utf-8") as datei:
        for zeile in zeilen:
            datei.write(_json.dumps(zeile) + "\n")


def _usage(ein=0, aus=0, gelesen=0, geschrieben=0):
    return {
        "input_tokens": ein,
        "output_tokens": aus,
        "cache_read_input_tokens": gelesen,
        "cache_creation_input_tokens": geschrieben,
    }


def _zeile(tag, modell="claude-opus-5", **mengen):
    return {
        "type": "assistant",
        "timestamp": f"{tag}T12:00:00.000Z",
        "message": {"model": modell, "usage": _usage(**mengen)},
    }


VOLLE_ENV = {
    "COMPASS_URL": "http://127.0.0.1:9/api/v1",
    "COMPASS_KEY": "geheim-und-bleibt-es",
    "COMPASS_PERSONA": "log",
    "COMPASS_SITZUNG": "s-test",
}


def test_verbrauch_hook_schweigt_ohne_konfiguration():
    ergebnis = _verbrauch_lauf({}, stdin='{"transcript_path": "/gibt/es/nicht"}')
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == "" and ergebnis.stderr == ""


def test_verbrauch_hook_schweigt_ohne_protokollpfad():
    """Der Pfad kommt aus der Hook-Eingabe auf stdin und steht in keiner
    Umgebungsvariable. Ihn aus der Sitzungskennung zu bauen waere geraten --
    die COMPASS-Sitzung und die Protokoll-UUID sind zwei Kennungen."""
    ergebnis = _verbrauch_lauf(VOLLE_ENV, stdin="{}")
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == "" and ergebnis.stderr == ""


def test_verbrauch_hook_summiert_je_tag_und_modell(tmp_path):
    """DIE Behauptung, ohne die der Hook doppelt zaehlen wuerde. Eine
    Sitzung kann ueber mehrere Tage laufen. Eine Gesamtsumme unter dem heutigen Datum haette die
    vier Tage zu einem gemacht -- und weil der Kern je (Tag, ...) ERSETZT,
    waere die Zeile von gestern mit ihrem alten Wert stehen geblieben:
    dieselben Token zweimal.
    """
    sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
    from verbrauch_melden import summiere  # type: ignore[import-not-found]

    protokoll = tmp_path / "sitzung.jsonl"
    _protokoll_schreiben(
        protokoll,
        [
            _zeile("2026-09-24", ein=10, aus=20, gelesen=1000),
            _zeile("2026-09-24", ein=5, aus=5, geschrieben=100),
            _zeile("2026-09-25", ein=1, aus=2),
            _zeile("2026-09-25", modell="gpt-5", ein=7),
        ],
    )
    summen, synthetisch, unlesbar = summiere(protokoll)
    assert synthetisch == 0 and unlesbar == 0
    assert set(summen) == {
        ("2026-09-24", "claude-opus-5"),
        ("2026-09-25", "claude-opus-5"),
        ("2026-09-25", "gpt-5"),
    }
    vortag = summen[("2026-09-24", "claude-opus-5")]
    assert vortag["token_ein"] == 15 and vortag["token_aus"] == 25
    assert vortag["token_cache_gelesen"] == 1000 and vortag["token_cache_geschrieben"] == 100
    assert vortag["aufrufe"] == 2
    assert vortag["zeitpunkt"].startswith("2026-09-24"), "der Zeitpunkt muss AN diesem Tag liegen"


def test_verbrauch_hook_laesst_synthetische_zeilen_aus_und_zaehlt_sie(tmp_path):
    """`model = "<synthetic>"` sind keine echten Modellaufrufe (ein kleiner Teil jedes
    Protokolls). Ihre Token einem Modell zuzuschlagen, das es nicht gibt, ergaebe
    eine Zeile ohne Preis -- eine Luecke, die wie ein fehlender Preis aussieht.
    Ausgelassen, aber GEZAEHLT: still verschluckt waere dasselbe Problem eine
    Ebene tiefer."""
    sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
    from verbrauch_melden import summiere  # type: ignore[import-not-found]

    protokoll = tmp_path / "sitzung.jsonl"
    _protokoll_schreiben(
        protokoll,
        [
            _zeile("2026-09-25", ein=10),
            _zeile("2026-09-25", modell="<synthetic>", ein=999_999),
            "kaputte zeile" if False else {"type": "user", "message": {"content": "kein usage"}},
        ],
    )
    with open(protokoll, "a", encoding="utf-8") as datei:
        datei.write("{halb geschrieben\n")

    summen, synthetisch, unlesbar = summiere(protokoll)
    assert synthetisch == 1
    assert unlesbar == 1, "eine halb geschriebene letzte Zeile ist normal — und wird gezaehlt"
    assert summen[("2026-09-25", "claude-opus-5")]["token_ein"] == 10
    assert not any(modell == "<synthetic>" for _tag, modell in summen)


def test_verbrauch_hook_verraet_den_schluessel_nicht(tmp_path):
    """Der Kern ist hier absichtlich nicht erreichbar (Port 9). Der Hook darf
    das melden -- aber weder den Schluessel noch die URL ausgeben: diese
    Ausgabe landet im Sitzungsverlauf."""
    protokoll = tmp_path / "sitzung.jsonl"
    _protokoll_schreiben(protokoll, [_zeile("2026-09-25", ein=10)])
    ergebnis = _verbrauch_lauf(VOLLE_ENV, stdin=json.dumps({"transcript_path": str(protokoll)}))
    assert ergebnis.returncode == 0, ergebnis.stderr
    gesamt = ergebnis.stdout + ergebnis.stderr
    assert "geheim-und-bleibt-es" not in gesamt
    assert "127.0.0.1" not in gesamt
    assert "fehlgeschlagen" in gesamt, "ein Fehlschlag wird benannt, nicht verschwiegen"


def test_verbrauch_hook_haelt_die_sitzung_nie_auf(tmp_path):
    """Exit 0 auch dann, wenn nichts gemeldet werden konnte. Ein Hook, der mit
    Fehlercode endet, redet in die Arbeit hinein."""
    protokoll = tmp_path / "sitzung.jsonl"
    _protokoll_schreiben(protokoll, [_zeile("2026-09-25", ein=10)])
    ergebnis = _verbrauch_lauf(VOLLE_ENV, stdin=json.dumps({"transcript_path": str(protokoll)}))
    assert ergebnis.returncode == 0


def test_hooks_json_registriert_den_stop_hook():
    daten = _load_json(PLUGIN_ROOT / "hooks" / "hooks.json")
    stop = daten["hooks"]["Stop"]
    befehle = [h["command"] for gruppe in stop for h in gruppe["hooks"]]
    assert any("verbrauch_melden.py" in b for b in befehle), befehle
    assert all("${CLAUDE_PLUGIN_ROOT}" in b for b in befehle), "kein absoluter Pfad ins Plugin"


def test_anbieter_wird_nicht_geraten():
    """`anbieter` ist im Kern eine freie Zeichenkette. Ein geratener Anbieter
    waere eine erfundene Zuordnung -- was nicht in der kurzen Tabelle steht,
    wird `unbekannt`, und dann findet der Kern keinen Preis und SAGT das."""
    sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
    from verbrauch_melden import anbieter_fuer  # type: ignore[import-not-found]

    assert anbieter_fuer("claude-opus-5") == "anthropic"
    assert anbieter_fuer("deepseek-flash") == "deepseek"
    assert anbieter_fuer("irgendwas-neues-7") == "unbekannt"


# ---------------------------------------------------------------------------
# eine verabschiedete Stelle wird nicht zum
# Weiterarbeiten aufgefordert -- und die Klingel nennt das Projekt.
#
# Gefahren wie die uebrigen Stop-Hook-Tests: als Unterprozess gegen einen
# falschen Postfach-Server. Ein Import von `hooks.stop` waere der kuerzere
# Weg und wuerde das Zusammenspiel aus Umgebung, Antwort und Ausgabe gerade
# nicht pruefen -- und genau dort sass der gemeldete Fehler.
# ---------------------------------------------------------------------------

def test_stop_hook_nennt_das_projekt_in_der_klingel():
    """Derselbe Slug kann in zwei Projekten liegen. Eine Klingel ohne
    Projektnamen laedt genau die Verwechslung ein: eine Sitzung liest `0`
    und schliesst daraus, es liege nichts an, waehrend im Nachbarprojekt unter
    demselben Namen Nachrichten liegen."""
    with _fake_postfach({"ungelesen": 3, "auftraege_offen": 0, "aktiv": True,
                         "projekt": "compass"}) as port:
        ergebnis = _stop_lauf({
            "COMPASS_URL": f"http://127.0.0.1:{port}",
            "COMPASS_KEY": FAKE_SCHLUESSEL,
            "COMPASS_PERSONA": FAKE_PERSONA,
        })
    assert ergebnis.returncode == 0
    grund = json.loads(ergebnis.stdout)["reason"]
    assert "3 ungelesene" in grund
    assert "Projekt: compass." in grund, grund


def test_stop_hook_warnt_eine_verabschiedete_stelle_statt_zu_klingeln():
    """LEERES POSTFACH UND TROTZDEM EIN WORT: ohne diesen Zweig schwiege der
    Hook, und die Sitzung erfuehre bis zum naechsten Neustart nicht, dass sie
    unter einer verabschiedeten Identitaet laeuft. Genau das ist im
    gemeldeten Fall passiert."""
    with _fake_postfach({"ungelesen": 0, "auftraege_offen": 0, "aktiv": False,
                         "projekt": "zweitprojekt",
                         "verabschiedet_am": "2026-10-15T11:20:54Z",
                         "nachfolger_slug": "nachfolgerin"}) as port:
        ergebnis = _stop_lauf({
            "COMPASS_URL": f"http://127.0.0.1:{port}",
            "COMPASS_KEY": FAKE_SCHLUESSEL,
            "COMPASS_PERSONA": FAKE_PERSONA,
        })
    assert ergebnis.returncode == 0
    grund = json.loads(ergebnis.stdout)["reason"]
    assert "VERABSCHIEDET" in grund, grund
    assert "zweitprojekt" in grund and "2026-10-15" in grund and "nachfolgerin" in grund
    # Die zweite Haelfte, die nirgends sonst zusammenkommt.
    assert "ANDEREN Projekt" in grund, grund


def test_stop_hook_haelt_ein_fehlendes_aktiv_feld_nicht_fuer_verabschiedet():
    """Ein aelterer Kern ohne das Feld liefert es gar nicht -- das heisst
    „weiss ich nicht", nicht „verabschiedet" (ein fehlender
    Wert wird nicht bewertet). Der Hook laeuft gegen Installationen, die
    aelter sein koennen als er selbst; wuerde er hier blockieren, waere jede
    aeltere Installation ab sofort lahmgelegt."""
    with _fake_postfach({"ungelesen": 0, "auftraege_offen": 0}) as port:
        ergebnis = _stop_lauf({
            "COMPASS_URL": f"http://127.0.0.1:{port}",
            "COMPASS_KEY": FAKE_SCHLUESSEL,
            "COMPASS_PERSONA": FAKE_PERSONA,
        })
    assert ergebnis.returncode == 0
    assert ergebnis.stdout == "", ergebnis.stdout
