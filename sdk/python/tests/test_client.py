"""Tests for compass_client.Compass/AsyncCompass against a mocked Core.

Every method: correct path, HTTP method, X-Compass-Key header, request body,
and error mapping (CompassFehler with status/detail/feld). Uses respx so no
real network/Core is needed.
"""
from __future__ import annotations

import json

import pytest
import respx
import httpx

from compass_client import AsyncCompass, Compass, CompassFehler

BASE = "http://core.test"
API = f"{BASE}/api/v1"
KEY = "test-key-123"


@pytest.fixture
def client():
    with Compass(BASE, KEY) as c:
        yield c


# ---------------------------------------------------------------------------
# gilt / warum
# ---------------------------------------------------------------------------


@respx.mock
def test_gilt_path_method_header(client: Compass) -> None:
    route = respx.get(f"{API}/gilt/deploy-freigabe").mock(
        return_value=httpx.Response(200, json={"id": 1, "text": "Nur mit Freigabe.", "gilt_seit": "2026-01-01T00:00:00Z"})
    )
    result = client.gilt("deploy-freigabe")
    assert route.called
    request = route.calls.last.request
    assert request.method == "GET"
    assert request.headers["X-Compass-Key"] == KEY
    assert result["id"] == 1


@respx.mock
def test_gilt_passes_query_params(client: Compass) -> None:
    route = respx.get(f"{API}/gilt/deploy-freigabe").mock(return_value=httpx.Response(200, json={"id": 1}))
    client.gilt("deploy-freigabe", subjekt_id=7, persona="alpha-persona", alle=True)
    request = route.calls.last.request
    assert request.url.params["subjekt_id"] == "7"
    assert request.url.params["persona"] == "alpha-persona"
    assert request.url.params["alle"] == "true"


@respx.mock
def test_gilt_404_maps_to_compass_fehler(client: Compass) -> None:
    respx.get(f"{API}/gilt/unbekannt").mock(
        return_value=httpx.Response(404, json={"detail": "keine geltende Regel", "offen": []})
    )
    with pytest.raises(CompassFehler) as exc_info:
        client.gilt("unbekannt")
    err = exc_info.value
    assert err.status == 404
    assert err.detail == "keine geltende Regel"
    assert err.feld is None
    assert err.extra["offen"] == []


@respx.mock
def test_warum_path_and_method(client: Compass) -> None:
    route = respx.get(f"{API}/warum/deploy-freigabe").mock(
        return_value=httpx.Response(200, json={"regel": None, "beleg_text": None, "historie": [], "pruefweg_ergebnis": None})
    )
    result = client.warum("deploy-freigabe")
    assert route.called
    assert route.calls.last.request.method == "GET"
    assert result["historie"] == []


# ---------------------------------------------------------------------------
# sache_anlegen
# ---------------------------------------------------------------------------


@respx.mock
def test_sache_anlegen_path_method_body(client: Compass) -> None:
    route = respx.post(f"{API}/sachen").mock(
        return_value=httpx.Response(201, json={"slug": "deploy-freigabe", "titel": "Deploy-Freigabe"})
    )
    result = client.sache_anlegen("deploy-freigabe", "Deploy-Freigabe", "Wer darf deployen?", "ops")
    assert route.called
    request = route.calls.last.request
    assert request.method == "POST"
    assert request.headers["X-Compass-Key"] == KEY
    body = json.loads(request.content)
    assert body == {
        "slug": "deploy-freigabe",
        "titel": "Deploy-Freigabe",
        "frage": "Wer darf deployen?",
        "bereich": "ops",
    }
    assert result["slug"] == "deploy-freigabe"


@respx.mock
def test_sache_anlegen_omits_none_fields(client: Compass) -> None:
    route = respx.post(f"{API}/sachen").mock(return_value=httpx.Response(201, json={"slug": "x"}))
    client.sache_anlegen("x", "X", "Frage?")
    body = json.loads(route.calls.last.request.content)
    assert "bereich" not in body
    assert "persona_slug" not in body


@respx.mock
def test_sache_anlegen_422_unbekannter_persona_slug(client: Compass) -> None:
    respx.post(f"{API}/sachen").mock(
        return_value=httpx.Response(
            422, json={"detail": "persona_slug 'ghost' ist unbekannt", "feld": "persona_slug"}
        )
    )
    with pytest.raises(CompassFehler) as exc_info:
        client.sache_anlegen("x", "X", "Frage?", persona_slug="ghost")
    assert exc_info.value.status == 422
    assert exc_info.value.feld == "persona_slug"


# ---------------------------------------------------------------------------
# regel_setzen
# ---------------------------------------------------------------------------


@respx.mock
def test_regel_setzen_path_method_body(client: Compass) -> None:
    route = respx.post(f"{API}/aussagen").mock(return_value=httpx.Response(201, json={"id": 42}))
    result = client.regel_setzen("deploy-freigabe", "Nur mit Freigabe.", angelegt_von="ci-bot")
    assert route.called
    request = route.calls.last.request
    assert request.method == "POST"
    body = json.loads(request.content)
    assert body["sache"] == "deploy-freigabe"
    assert body["art"] == "regel"
    assert body["text"] == "Nur mit Freigabe."
    assert body["herkunft"] == "entschieden"
    assert body["angelegt_von"] == "ci-bot"
    assert "ersetzt" not in body
    assert result["id"] == 42


@respx.mock
def test_regel_setzen_mit_ersetzt_und_beleg(client: Compass) -> None:
    route = respx.post(f"{API}/aussagen").mock(return_value=httpx.Response(201, json={"id": 43}))
    client.regel_setzen(
        "deploy-freigabe", "Neuer Text.", ersetzt=42, quelle="handbuch", beleg=["doc-1"], angelegt_von="ci-bot"
    )
    body = json.loads(route.calls.last.request.content)
    assert body["ersetzt"] == 42
    assert body["quelle"] == "handbuch"
    assert body["beleg"] == ["doc-1"]


@respx.mock
def test_regel_setzen_409_ohne_ersetzt_traegt_geltende(client: Compass) -> None:
    respx.post(f"{API}/aussagen").mock(
        return_value=httpx.Response(
            409,
            json={
                "detail": "es gilt bereits eine Regel fuer diese Sache",
                "geltende": {"id": 1, "text": "Alt.", "gilt_seit": "2026-01-01T00:00:00Z", "quelle": None},
            },
        )
    )
    with pytest.raises(CompassFehler) as exc_info:
        client.regel_setzen("deploy-freigabe", "Neuer Text.", angelegt_von="ci-bot")
    err = exc_info.value
    assert err.status == 409
    assert err.extra["geltende"]["id"] == 1


# ---------------------------------------------------------------------------
# lehre_festhalten
# ---------------------------------------------------------------------------


@respx.mock
def test_lehre_festhalten_path_method_body(client: Compass) -> None:
    route = respx.post(f"{API}/lehren").mock(return_value=httpx.Response(201, json={"id": 5, "status": "offen"}))
    result = client.lehre_festhalten(
        "fehler",
        "CI brach ab",
        "Der Deploy schlug fehl.",
        "Immer erst auf staging testen.",
        ursache="fehlende Vorschau",
        belege=["doc-99"],
        angelegt_von="ci-bot",
    )
    assert route.called
    request = route.calls.last.request
    assert request.method == "POST"
    body = json.loads(request.content)
    assert body == {
        "art": "fehler",
        "titel": "CI brach ab",
        "was": "Der Deploy schlug fehl.",
        "lehre": "Immer erst auf staging testen.",
        "ursache": "fehlende Vorschau",
        "belege": ["doc-99"],
        "angelegt_von": "ci-bot",
    }
    assert result["id"] == 5


@respx.mock
def test_lehre_festhalten_422_fehler_ohne_ursache(client: Compass) -> None:
    respx.post(f"{API}/lehren").mock(
        return_value=httpx.Response(
            422,
            json={
                "detail": "ein Fehler ohne Ursache ist keine Lehre, sondern ein Ereignis",
                "feld": "ursache",
            },
        )
    )
    with pytest.raises(CompassFehler) as exc_info:
        client.lehre_festhalten("fehler", "Titel", "Was", "Lehre", angelegt_von="ci-bot")
    assert exc_info.value.status == 422
    assert exc_info.value.feld == "ursache"


# ---------------------------------------------------------------------------
# suche
# ---------------------------------------------------------------------------


@respx.mock
def test_suche_path_method_params(client: Compass) -> None:
    """die Antwort ist ein Objekt, keine Liste --
    hier stand `json=[{...}]` und `result[0]`, und das wuerde den brechenden
    Wechsel stillschweigend durchlassen."""
    route = respx.get(f"{API}/suche").mock(
        return_value=httpx.Response(
            200,
            json={"treffer": [{"typ": "aussage", "id": 1}], "gesamt": 290,
                  "abgeschnitten": True, "weiter": 100},
        )
    )
    result = client.suche("freigabe", limit=5, offset=100)
    assert route.called
    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.params["q"] == "freigabe"
    assert request.url.params["limit"] == "5"
    assert request.url.params["offset"] == "100"
    assert result["treffer"][0]["typ"] == "aussage"
    assert result["gesamt"] == 290
    assert result["abgeschnitten"] is True
    assert result["weiter"] == 100


@respx.mock
def test_suche_422_ueber_deckel(client: Compass) -> None:
    respx.get(f"{API}/suche").mock(
        return_value=httpx.Response(422, json={"detail": "limit ueber dem Deckel der Modellklasse", "feld": "limit"})
    )
    with pytest.raises(CompassFehler) as exc_info:
        client.suche("x", limit=99999, persona="alpha-persona")
    assert exc_info.value.status == 422


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@respx.mock
def test_export_claude_md_section0_returns_text(client: Compass) -> None:
    route = respx.get(f"{API}/export/claude-md-section0").mock(
        return_value=httpx.Response(200, text="## 0. Verbindliche Mindest-Regeln\n")
    )
    result = client.export("claude-md-section0")
    assert route.called
    assert route.calls.last.request.method == "GET"
    assert isinstance(result, str)
    assert "Mindest-Regeln" in result


@respx.mock
def test_export_agents_md_returns_text(client: Compass) -> None:
    respx.get(f"{API}/export/agents-md").mock(return_value=httpx.Response(200, text="# AGENTS.md\n"))
    result = client.export("agents-md")
    assert isinstance(result, str)


@respx.mock
def test_export_cursor_rules_returns_bytes(client: Compass) -> None:
    respx.get(f"{API}/export/cursor-rules").mock(
        return_value=httpx.Response(200, content=b"PK\x03\x04zipbytes", headers={"content-type": "application/zip"})
    )
    result = client.export("cursor-rules")
    assert isinstance(result, bytes)
    assert result.startswith(b"PK")


def test_export_unknown_art_raises_valueerror(client: Compass) -> None:
    with pytest.raises(ValueError):
        client.export("unbekannt")


# ---------------------------------------------------------------------------
# AsyncCompass mirrors Compass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_async_gilt() -> None:
    route = respx.get(f"{API}/gilt/deploy-freigabe").mock(return_value=httpx.Response(200, json={"id": 1}))
    async with AsyncCompass(BASE, KEY) as c:
        result = await c.gilt("deploy-freigabe")
    assert route.called
    assert route.calls.last.request.headers["X-Compass-Key"] == KEY
    assert result["id"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_async_regel_setzen_409() -> None:
    respx.post(f"{API}/aussagen").mock(
        return_value=httpx.Response(409, json={"detail": "geltende Regel vorhanden", "geltende": {"id": 1}})
    )
    async with AsyncCompass(BASE, KEY) as c:
        with pytest.raises(CompassFehler) as exc_info:
            await c.regel_setzen("x", "text", angelegt_von="ci-bot")
    assert exc_info.value.status == 409


@pytest.mark.asyncio
@respx.mock
async def test_async_export_cursor_rules_bytes() -> None:
    respx.get(f"{API}/export/cursor-rules").mock(return_value=httpx.Response(200, content=b"PK\x03\x04"))
    async with AsyncCompass(BASE, KEY) as c:
        result = await c.export("cursor-rules")
    assert isinstance(result, bytes)
