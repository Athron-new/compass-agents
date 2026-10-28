"""das Python-SDK nennt sich in der Lesespur des Kerns.

Die Lesespur des Kerns fuehrt eine Spalte fuer den Aufrufer, und die eigenen
Klienten setzen einen sprechenden Namen. Ohne das stuende dort
`python-httpx/<version>` -- der Name der Bibliothek.

MIT VERSION, anders als bei `compass-web`/`compass-mcp`: dieses Paket geht an
KUNDEN, und "welche SDK-Version laeuft dort" ist bei einem Fehlerbild die erste
Auskunft, die man braucht. Eine Gruppierung je Version ist hier gewollt.

EINE QUELLE: die Version steht in `client.py` (`VERSION`), `__init__.py` nimmt
sie von dort, und dieser Test haelt sie gegen `pyproject.toml`. Zwei Stellen,
die sich widersprechen koennen, waeren zwei Wahrheiten -- und die eine, die im
`User-Agent` landet, waere die, die niemand pflegt.
"""
from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest
import respx

import compass_client
from compass_client import AsyncCompass, Compass
from compass_client.client import KLIENT, VERSION

BASE = "http://core.test"
API = f"{BASE}/api/v1"
KEY = "test-key-123"


@pytest.fixture(autouse=True)
def _keine_sitzungs_umgebung(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("COMPASS_SITZUNG", raising=False)
    monkeypatch.delenv("GIT_GUARD_ACTOR", raising=False)


@respx.mock
def test_der_synchrone_client_nennt_sich():
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY) as c:
        c.gilt("x")
    assert route.calls.last.request.headers["User-Agent"] == f"compass-sdk-python/{VERSION}"


@respx.mock
@pytest.mark.asyncio
async def test_der_asynchrone_client_nennt_sich_genauso():
    """Zwei Klassen, ein Klient: wer nur die synchrone Fassung nennt, teilt
    denselben Aufrufer in der Auskunft in zwei."""
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    async with AsyncCompass(BASE, KEY) as c:
        await c.gilt("x")
    assert route.calls.last.request.headers["User-Agent"] == f"compass-sdk-python/{VERSION}"


@respx.mock
def test_der_schluessel_bleibt_der_beweis():
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY) as c:
        c.gilt("x")
    kopf = route.calls.last.request.headers
    assert kopf["X-Compass-Key"] == KEY
    assert kopf["User-Agent"].startswith("compass-sdk-python/")


def test_der_name_traegt_die_version_des_pakets():
    assert KLIENT == f"compass-sdk-python/{VERSION}"
    assert compass_client.__version__ == VERSION, "__init__ und client.py duerfen nicht auseinanderlaufen"
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    treffer = re.search(r'^version = "([^"]+)"', pyproject, re.M)
    assert treffer is not None, "pyproject.toml ohne version"
    assert treffer.group(1) == VERSION, (
        f"pyproject.toml sagt {treffer.group(1)}, client.py sagt {VERSION} -- "
        "der User-Agent traegt die falsche Zahl"
    )
