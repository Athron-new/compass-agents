"""Regeln setzt der Mensch : der Kern antwortet auf ``regel_setzen`` mit einem Schluessel allein
403. Der Client kann deshalb das Sitzungs-Token eines Menschen mitsenden (``Authorization: Bearer``): Konstruktor-Argument
``menschen_sitzung`` (Vorrang) oder ``COMPASS_MENSCHEN_SITZUNG``; ohne beides kein Header (fehlende Konfiguration oeffnet
nichts). Der Schluessel bleibt, wie er war."""
from __future__ import annotations

import httpx
import pytest
import respx

from compass_client import AsyncCompass, Compass

BASE = "http://core.test"
API = f"{BASE}/api/v1"
KEY = "test-key-123"


@pytest.fixture(autouse=True)
def _keine_umgebung(monkeypatch: pytest.MonkeyPatch):
    for n in ("COMPASS_MENSCHEN_SITZUNG", "COMPASS_SITZUNG", "GIT_GUARD_ACTOR"):
        monkeypatch.delenv(n, raising=False)


@respx.mock
def test_ohne_menschen_sitzung_kein_authorization_header():
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY) as c:
        c.gilt("x")
    assert "Authorization" not in route.calls.last.request.headers


@respx.mock
def test_konstruktor_argument_sendet_bearer_neben_dem_schluessel():
    route = respx.post(f"{API}/aussagen").mock(return_value=httpx.Response(201, json={"id": 7}))
    with Compass(BASE, KEY, menschen_sitzung="sitzungs-token-1") as c:
        c.regel_setzen("sache", "Es gilt dies.", angelegt_von="test")
    h = route.calls.last.request.headers
    assert h["Authorization"] == "Bearer sitzungs-token-1" and h["X-Compass-Key"] == KEY


@respx.mock
def test_umgebungsvariable_und_vorrang_des_arguments(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMPASS_MENSCHEN_SITZUNG", "aus-der-umgebung")
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    with Compass(BASE, KEY) as c:
        c.gilt("x")
    assert route.calls.last.request.headers["Authorization"] == "Bearer aus-der-umgebung"
    with Compass(BASE, KEY, menschen_sitzung="explizit") as c:
        c.gilt("x")
    assert route.calls.last.request.headers["Authorization"] == "Bearer explizit"


@respx.mock
@pytest.mark.asyncio
async def test_der_asynchrone_client_sendet_es_ebenso():
    route = respx.get(f"{API}/gilt/x").mock(return_value=httpx.Response(200, json={"id": 1}))
    async with AsyncCompass(BASE, KEY, menschen_sitzung="async-token") as c:
        await c.gilt("x")
    assert route.calls.last.request.headers["Authorization"] == "Bearer async-token"
