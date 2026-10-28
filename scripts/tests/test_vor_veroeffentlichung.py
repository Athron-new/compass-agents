"""The guard finds what it claims to find -- one planted violation per rule, plus a clean control."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location("guard", Path(__file__).resolve().parents[1] / "vor_veroeffentlichung.py")
guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(guard)

FAELLE = {
    "ticket": "see COMPASS-123 for details",
    "aussage": "decided in Aussage 554",
    "person": "ask Carsten about it",
    "persona": "Trinity lost an hour on this",
    "kunde": "the Athlet table has it",
    "pfad": "lives in /home/someone/work",
    "ip": "connect to 10.1.2.3 first",
    "mail": "write to someone@company.org",
    "geheimnis": "token ghp_" + "a" * 30,
    "schluessel-kopfzeile": "X-Compass-Key: " + "A1b2C3d4E5f6G7h8I9j0K1l2",
}


def _baum(tmp_path: Path, inhalt: str) -> Path:
    (tmp_path / "datei.md").write_text(inhalt + "\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("regel", sorted(FAELLE))
def test_jede_regel_findet_ihren_fall(tmp_path, regel):
    funde, gelesen = guard.pruefen(_baum(tmp_path, FAELLE[regel]), erlaube_platzhalter=True)
    assert gelesen == 1
    assert any(f"[{regel}]" in f for f in funde), (regel, funde)


def test_ein_sauberer_baum_hat_keinen_fund(tmp_path):
    funde, gelesen = guard.pruefen(_baum(tmp_path, "Set COMPASS_KEY in your environment. Host: <your-compass-host>, 127.0.0.1."), True)
    assert gelesen == 1 and funde == []


def test_die_eigenen_namen_des_herausgebers_sind_erlaubt_fremde_athron_pfade_nicht(tmp_path):
    ok = "Copyright (c) 2026 Athron.io GmbH, https://compass.athron.io, /plugin marketplace add Athron-new/compass-agents, built by ATHRON, office@athron.io"
    assert guard.pruefen(_baum(tmp_path, ok), True)[0] == []
    assert any("[kunde]" in f for f in guard.pruefen(_baum(tmp_path, "see Athron-new/athron for it or the internal Athron-new/compass repo"), True)[0])


def test_platzhalter_sind_im_strengen_modus_ein_fund(tmp_path):
    baum = _baum(tmp_path, "/plugin marketplace add <ORG>/<REPO> and write to «address to be set»")
    assert guard.pruefen(baum, erlaube_platzhalter=True)[0] == []
    assert any("[platzhalter]" in f for f in guard.pruefen(baum, erlaube_platzhalter=False)[0])


def test_geheimnisse_werden_nie_im_klartext_ausgegeben(tmp_path):
    geheim = "ghp_" + "Z9y8X7w6V5u4T3s2R1q0P9o8"
    funde, _ = guard.pruefen(_baum(tmp_path, geheim), True)
    assert funde and all(geheim not in f for f in funde)


def test_ein_leerer_baum_ist_ein_fehler_und_kein_sauberes_ergebnis(tmp_path):
    assert guard.main(["--wurzel", str(tmp_path)]) == 2
