"""`Compass`/`AsyncCompass` haengen `X-Compass-Sitzung` an jede
Anfrage, sofern eine Sitzungskennung bekannt ist. Herkunft, in dieser Reihenfolge: das
Konstruktor-Feld `sitzung` (damit eine Anwendung es selbst setzen kann), sonst die
Umgebungsvariable `COMPASS_SITZUNG`, sonst nichts. Ist nichts davon
gesetzt: kein Header -- kein erfundener Wert wie `"compass-client-python"`."""
from __future__ import annotations

import httpx
import pytest
import respx

from compass_client import AsyncCompass, Compass

BASE = "http://core.test"
API = f"{BASE}/api/v1"
KEY = "test-key-123"


@pytest.fixture(autouse=True)
def _keine_sitzungs_umgebung(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("COMPASS_SITZUNG", raising=False)
    monkeypatch.delenv("GIT_GUARD_ACTOR", raising=False)


@respx.mock
def test_ohne_konfiguration_fehlt_der_header():
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY) as c:
        c.gilt("x")
    assert "X-Compass-Sitzung" not in route.calls.last.request.headers


@respx.mock
def test_konstruktor_feld_setzt_den_header():
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY, sitzung="agent-7ccc6f") as c:
        c.gilt("x")
    assert route.calls.last.request.headers["X-Compass-Sitzung"] == "agent-7ccc6f"


@respx.mock
def test_compass_sitzung_umgebungsvariable_setzt_den_header(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMPASS_SITZUNG", "agent-7ccc6f")
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY) as c:
        c.gilt("x")
    assert route.calls.last.request.headers["X-Compass-Sitzung"] == "agent-7ccc6f"


@respx.mock
def test_eine_fremde_variable_ist_kein_ruckfall(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GIT_GUARD_ACTOR", "fremdes-werkzeug")
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY) as c:
        c.gilt("x")
    assert "X-Compass-Sitzung" not in route.calls.last.request.headers


@respx.mock
def test_konstruktor_feld_hat_vorrang_vor_umgebungsvariablen(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMPASS_SITZUNG", "aus-der-umgebung")
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY, sitzung="explizit-gesetzt") as c:
        c.gilt("x")
    assert route.calls.last.request.headers["X-Compass-Sitzung"] == "explizit-gesetzt"


@pytest.mark.asyncio
@respx.mock
async def test_async_compass_sendet_den_header_ebenso():
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    async with AsyncCompass(BASE, KEY, sitzung="agent-7ccc6f") as c:
        await c.gilt("x")
    assert route.calls.last.request.headers["X-Compass-Sitzung"] == "agent-7ccc6f"


@pytest.mark.asyncio
@respx.mock
async def test_async_compass_ohne_konfiguration_fehlt_der_header():
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    async with AsyncCompass(BASE, KEY) as c:
        await c.gilt("x")
    assert "X-Compass-Sitzung" not in route.calls.last.request.headers
