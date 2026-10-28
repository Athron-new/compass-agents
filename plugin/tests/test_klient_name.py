"""die Hooks des Plugins nennen sich in der Lesespur.

Die Hooks setzen einen sprechenden Aufrufernamen: aus `Python-urllib/3.12`
wird `compass-hook/verbrauch_melden`. Ohne ihn waeren die eigenen Hooks in der
Lesespur des Kerns von jedem anderen Python-Programm nicht zu unterscheiden.

Gemessen wird gegen einen echten lokalen Fake-Server und den Hook als PROZESS
(wie der Rest von test_plugin.py) -- nicht gegen eine importierte Funktion:
ein Hook laeuft in Produktion als Prozess, und nur so ist auch der Aufruf in
`main()` mit geprueft.
"""
from __future__ import annotations

import contextlib
import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
FAKE_SCHLUESSEL = "test-fake-schluessel-9f3a-nicht-echt"
FAKE_PERSONA = "test-persona"


class _AufzeichnenderHandler(http.server.BaseHTTPRequestHandler):
    letzte_headers: dict[str, str] = {}

    def _antwort(self, body: bytes, typ: str = "application/json") -> None:
        type(self).letzte_headers = dict(self.headers.items())
        self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.endswith("/brief"):
            self._antwort(b"# Brief\n", "text/markdown")
        else:
            # Postfach-Stand fuer den Stop-Hook.
            self._antwort(json.dumps({"offen": 0, "ungelesen": 0, "nachrichten": []}).encode())

    def do_POST(self):  # noqa: N802
        laenge = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(laenge)
        self._antwort(b"{}")

    def log_message(self, format, *args):  # ruhig halten
        pass


@contextlib.contextmanager
def _fake_core():
    server = http.server.HTTPServer(("127.0.0.1", 0), _AufzeichnenderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        thread.join(timeout=5)


def _lauf(skript: str, env: dict, eingabe: str | None = None) -> subprocess.CompletedProcess:
    vollstaendige_env = {"PATH": os.environ.get("PATH", "")}
    vollstaendige_env.update(env)
    return subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "hooks" / skript)],
        env=vollstaendige_env,
        input=eingabe,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_session_start_nennt_sich():
    with _fake_core() as port:
        _lauf(
            "session_start.py",
            {
                "COMPASS_URL": f"http://127.0.0.1:{port}",
                "COMPASS_KEY": FAKE_SCHLUESSEL,
                "COMPASS_PERSONA": FAKE_PERSONA,
            },
        )
    assert _AufzeichnenderHandler.letzte_headers.get("User-Agent") == "compass-hook/session_start"


def test_stop_nennt_sich():
    with _fake_core() as port:
        _lauf(
            "stop.py",
            {
                "COMPASS_URL": f"http://127.0.0.1:{port}",
                "COMPASS_KEY": FAKE_SCHLUESSEL,
                "COMPASS_PERSONA": FAKE_PERSONA,
            },
        )
    assert _AufzeichnenderHandler.letzte_headers.get("User-Agent") == "compass-hook/stop"


def test_jeder_hook_hat_seinen_eigenen_namen():
    """Drei Hooks, drei Namen -- ein gemeinsamer Name waere in der Auskunft ein
    Aufrufer, wo es drei sind, und damit genau die Verdichtung, die dieses
    Ticket aufloest. Gelesen aus dem Quelltext, damit auch der Hook mitgeprueft
    ist, dessen Lauf hier keinen Server braucht."""
    namen = {}
    for datei in ("session_start.py", "stop.py", "verbrauch_melden.py"):
        quelle = (PLUGIN_ROOT / "hooks" / datei).read_text(encoding="utf-8")
        zeile = [z for z in quelle.splitlines() if z.startswith("KLIENT = ")]
        assert zeile, f"{datei} setzt keinen KLIENT"
        namen[datei] = zeile[0].split("=", 1)[1].strip().strip('"')
    assert namen == {
        "session_start.py": "compass-hook/session_start",
        "stop.py": "compass-hook/stop",
        "verbrauch_melden.py": "compass-hook/verbrauch_melden",
    }
    assert len(set(namen.values())) == 3


def test_der_name_steht_in_jeder_kopfzeile_des_hooks():
    """Waechter gegen die halbe Verdrahtung: eine Datei, die `KLIENT` setzt,
    ihn aber bei einer ihrer Anfragen nicht mitschickt, ist schlimmer als
    keine -- dann fehlt genau ein Weg in der Auskunft und niemand sieht es."""
    for datei in ("session_start.py", "stop.py", "verbrauch_melden.py"):
        quelle = (PLUGIN_ROOT / "hooks" / datei).read_text(encoding="utf-8")
        anfragen = quelle.count("urllib.request.Request(")
        # Gezaehlt wird die KOPFZEILE, nicht ein bestimmter Bezeichner:
        # `session_start.py` setzt sie aus dem Parameter `klient` (mit `KLIENT`
        # als Standard), weil ein anderes Programm denselben Weg
        # benutzen kann. Ein Test, der auf
        # `KLIENT` bestand, wuerde diese richtige Loesung rot machen.
        kopfzeilen = quelle.count('"User-Agent"')
        assert kopfzeilen >= anfragen, (
            f"{datei}: {anfragen} Anfragen, aber nur {kopfzeilen} mit User-Agent"
        )
