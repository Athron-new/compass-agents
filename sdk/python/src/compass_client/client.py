"""COMPASS — dünner Python-Client (kein MCP nötig).

Ruft ausschliesslich die dokumentierten REST-Routen des Kerns auf:
Auth per Kopfzeile ``X-Compass-Key``, Fehlerform überall
``{"detail": "<Satz>", ...felder}``. Keine eigene Fachlogik — was der Kern entscheidet, entscheidet
der Kern (dieselbe Haltung wie der MCP-Server, nur ohne ihn dazwischen).

Drei Zeilen:

    from compass_client import Compass
    c = Compass("http://localhost:18080", "<key>")
    regel = c.gilt("deploy-freigabe")
"""

from __future__ import annotations

import os
from typing import Any

import httpx

API_PREFIX = "/api/v1"
DEFAULT_TIMEOUT = 10.0

# das SDK nennt sich in der
# Lesespur des Kerns. Bis hierher stand dort `python-httpx/<version>` -- der
# Name der Bibliothek, nicht der des Programms; eine Auskunft "welches Ihrer
# Programme fragt hier so oft?" war damit nicht zu geben.
#
# HIER MIT VERSION, anders als bei unseren internen Klienten (`compass-web`,
# `compass-mcp`): dieses Paket geht an KUNDEN. Welche SDK-Version bei einem
# Kunden laeuft, ist die Auskunft, die man bei einem Fehlerbild zuerst
# braucht, und eine Gruppierung je Version ist hier deshalb gewollt, nicht
# stoerend.
#
# EINE QUELLE FUER DIE VERSION: sie steht hier, und `__init__.py` nimmt sie
# von hier (`__version__ = VERSION`). Umgekehrt geht nicht -- `__init__`
# importiert diesen Modul, ein Rueckimport waere ein Zirkel.
# `tests/test_version_einmal.py` haelt sie gegen `pyproject.toml`.
VERSION = "0.1.0"
KLIENT = f"compass-sdk-python/{VERSION}"


class CompassFehler(Exception):
    """Eine Nicht-2xx-Antwort des Kerns, strukturiert.

    ``status`` ist der HTTP-Status, ``detail`` der Klartext-Satz, ``feld``
    (falls vorhanden) das Feld, das ein 422/409 nennt (REST-Referenz,
    "Fehlerform"). ``extra`` trägt alles Übrige aus dem Antwort-Body (z.B.
    ``bestehend`` bei einem 409, ``offen`` bei einem 404 auf ``GET
    /gilt/{sache}``).
    """

    def __init__(self, status: int, detail: str, feld: str | None = None, **extra: Any) -> None:
        self.status = status
        self.detail = detail
        self.feld = feld
        self.extra = extra
        teil = f" (feld={feld})" if feld else ""
        super().__init__(f"[{status}] {detail}{teil}")


def _ohne_leerwerte(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


def _fehler_aus_antwort(status: int, body: Any) -> CompassFehler:
    if isinstance(body, dict):
        detail = body.get("detail") or f"Fehler {status}"
        feld = body.get("feld")
        extra = {k: v for k, v in body.items() if k not in ("detail", "feld")}
        return CompassFehler(status, detail, feld, **extra)
    return CompassFehler(status, str(body) if body is not None else f"Fehler {status}")


def _body_aus_antwort(response: httpx.Response) -> Any:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


def _sitzung_aufloesen(sitzung: str | None) -> str | None:
    """Die Sitzungskennung fuer diesen Client: das explizite ``sitzung``-Argument
    hat Vorrang, sonst ``COMPASS_SITZUNG`` (z.B. ``agent-7ccc6f``). Ist nichts davon gesetzt: ``None`` --
    kein erfundener Wert wie ``"unbekannt"`` oder ``"compass-client-python"``. Der Kern fuehrt die Sitzungskennung
    nur als "erklaert", nie als Beweis -- Beweis ist ausschliesslich der Schluessel."""
    if sitzung is not None:
        return sitzung
    return os.environ.get("COMPASS_SITZUNG") or None


def _menschen_sitzung_aufloesen(menschen_sitzung: str | None) -> str | None:
    """Das Sitzungs-Token eines MENSCHEN (``POST /auth/anmelden`` -> ``sitzungs_token``), das der Client neben dem Schluessel
    mitsendet: ``Authorization: Bearer <token>``. Gebraucht wird es dort, wo ein Mensch handeln muss -- REGELN SETZT DER MENSCH
    (``regel_setzen`` bekommt mit einem Schluessel allein 403). Das explizite Argument hat Vorrang, sonst
    ``COMPASS_MENSCHEN_SITZUNG``; ist nichts gesetzt: ``None``, kein Header (fehlende Konfiguration oeffnet nichts). Dieses
    Token ist ein Geheimnis wie der Schluessel -- nicht protokollieren."""
    if menschen_sitzung is not None:
        return menschen_sitzung or None
    return os.environ.get("COMPASS_MENSCHEN_SITZUNG") or None


_EXPORT_PFADE = {
    "claude-md-section0": "/export/claude-md-section0",
    "agents-md": "/export/agents-md",
    "cursor-rules": "/export/cursor-rules",
}


def _sache_anlegen_body(
    slug: str,
    titel: str,
    frage: str,
    bereich: str | None,
    *,
    stufe: str | None,
    eltern_slug: str | None,
    subjekt_typ: str | None,
    persona_slug: str | None,
    nummer: str | None,
) -> dict[str, Any]:
    return _ohne_leerwerte(
        {
            "slug": slug,
            "titel": titel,
            "frage": frage,
            "bereich": bereich,
            "stufe": stufe,
            "eltern_slug": eltern_slug,
            "subjekt_typ": subjekt_typ,
            "persona_slug": persona_slug,
            "nummer": nummer,
        }
    )


def _regel_setzen_body(
    sache: str,
    text: str,
    ersetzt: int | None,
    quelle: str | None,
    beleg: list[str] | None,
    *,
    herkunft: str,
    angelegt_von: str,
    subjekt_id: int | None,
    quelle_ref: str | None,
    gilt_seit: str | None,
) -> dict[str, Any]:
    return _ohne_leerwerte(
        {
            "sache": sache,
            "art": "regel",
            "text": text,
            "herkunft": herkunft,
            "ersetzt": ersetzt,
            "quelle": quelle,
            "beleg": beleg,
            "angelegt_von": angelegt_von,
            "subjekt_id": subjekt_id,
            "quelle_ref": quelle_ref,
            "gilt_seit": gilt_seit,
        }
    )


def _lehre_festhalten_body(
    art: str,
    titel: str,
    was: str,
    lehre: str,
    ursache: str | None,
    belege: list[str] | None,
    *,
    angelegt_von: str,
    bereich: str | None,
    persona_slug: str | None,
    wirkung: str | None,
    regel_vorschlag: str | None,
    quelle: str | None,
    quelle_ref: str | None,
    herkunft: str | None,
) -> dict[str, Any]:
    return _ohne_leerwerte(
        {
            "art": art,
            "titel": titel,
            "was": was,
            "lehre": lehre,
            "ursache": ursache,
            "belege": belege,
            "angelegt_von": angelegt_von,
            "bereich": bereich,
            "persona_slug": persona_slug,
            "wirkung": wirkung,
            "regel_vorschlag": regel_vorschlag,
            "quelle": quelle,
            "quelle_ref": quelle_ref,
            "herkunft": herkunft,
        }
    )


class Compass:
    """Synchroner Client. Ein Client pro Prozess/Thread, wiederverwendbar."""

    def __init__(
        self, base_url: str, key: str, timeout: float = DEFAULT_TIMEOUT, *, sitzung: str | None = None,
        menschen_sitzung: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.key = key
        self.timeout = timeout
        self.sitzung = _sitzung_aufloesen(sitzung)
        headers = {"X-Compass-Key": key, "User-Agent": KLIENT}
        if self.sitzung:
            headers["X-Compass-Sitzung"] = self.sitzung
        # Der Kern belegt damit den Menschen (``benutzer_id``) -- ohne ihn bekommt ``regel_setzen`` 403.
        menschen_token = _menschen_sitzung_aufloesen(menschen_sitzung)
        if menschen_token:
            headers["Authorization"] = f"Bearer {menschen_token}"
        self._client = httpx.Client(
            base_url=f"{self.base_url}{API_PREFIX}",
            headers=headers,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Compass":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> Any:
        response = self._client.request(method, path, params=_ohne_leerwerte(params or {}), json=json)
        body = _body_aus_antwort(response)
        if response.status_code >= 400:
            raise _fehler_aus_antwort(response.status_code, body)
        return body

    def gilt(self, sache: str, *, subjekt_id: int | None = None, persona: str | None = None, alle: bool = False) -> dict[str, Any]:
        """``GET /gilt/{sache}`` — die aktuell geltende Regel, oder ``CompassFehler(404, ...)``."""
        return self._request(
            "GET", f"/gilt/{sache}", params={"subjekt_id": subjekt_id, "persona": persona, "alle": alle}
        )

    def warum(self, sache: str, *, subjekt_id: int | None = None) -> dict[str, Any]:
        """``GET /warum/{sache}`` — Regel, Beleg, Historie, Prüfweg-Ergebnis."""
        return self._request("GET", f"/warum/{sache}", params={"subjekt_id": subjekt_id})

    def sache_anlegen(
        self,
        slug: str,
        titel: str,
        frage: str,
        bereich: str | None = None,
        *,
        stufe: str | None = None,
        eltern_slug: str | None = None,
        subjekt_typ: str | None = None,
        persona_slug: str | None = None,
        nummer: str | None = None,
    ) -> dict[str, Any]:
        """``POST /sachen`` — 201 neu, 200 wenn der Slug schon besteht (idempotent)."""
        body = _sache_anlegen_body(
            slug, titel, frage, bereich,
            stufe=stufe, eltern_slug=eltern_slug, subjekt_typ=subjekt_typ,
            persona_slug=persona_slug, nummer=nummer,
        )
        return self._request("POST", "/sachen", json=body)

    def regel_setzen(
        self,
        sache: str,
        text: str,
        ersetzt: int | None = None,
        quelle: str | None = None,
        beleg: list[str] | None = None,
        *,
        herkunft: str = "entschieden",
        angelegt_von: str,
        subjekt_id: int | None = None,
        quelle_ref: str | None = None,
        gilt_seit: str | None = None,
    ) -> dict[str, Any]:
        """``POST /aussagen`` mit ``art=regel`` — setzt oder löst eine Regel ab.

        Ohne ``ersetzt`` und mit bereits geltender Regel derselben Sache
        antwortet der Kern mit 409 (``CompassFehler.extra["geltende"]`` trägt
        die bestehende Aussage) — genau die Ein-Regel-Invariante, die
        ``ersetzt`` auflöst.

        REGELN SETZT DER MENSCH: mit einem Schlüssel allein antwortet der Kern 403. Der Client braucht das
        Sitzungs-Token eines Menschen (``Compass(..., menschen_sitzung=...)``, aus ``POST /auth/anmelden``);
        ein Agent schlägt stattdessen eine Regel vor (``lehre_festhalten`` mit ``regel_vorschlag``).
        """
        body = _regel_setzen_body(
            sache, text, ersetzt, quelle, beleg,
            herkunft=herkunft, angelegt_von=angelegt_von, subjekt_id=subjekt_id,
            quelle_ref=quelle_ref, gilt_seit=gilt_seit,
        )
        return self._request("POST", "/aussagen", json=body)

    def lehre_festhalten(
        self,
        art: str,
        titel: str,
        was: str,
        lehre: str,
        ursache: str | None = None,
        belege: list[str] | None = None,
        *,
        angelegt_von: str,
        bereich: str | None = None,
        persona_slug: str | None = None,
        wirkung: str | None = None,
        regel_vorschlag: str | None = None,
        quelle: str | None = None,
        quelle_ref: str | None = None,
        herkunft: str | None = None,
    ) -> dict[str, Any]:
        """``POST /lehren`` — ``art`` ∈ ``fehler``/``gelungen``/``hinweis``; ``ursache`` ist bei ``art=fehler`` Pflicht."""
        body = _lehre_festhalten_body(
            art, titel, was, lehre, ursache, belege,
            angelegt_von=angelegt_von, bereich=bereich, persona_slug=persona_slug,
            wirkung=wirkung, regel_vorschlag=regel_vorschlag, quelle=quelle,
            quelle_ref=quelle_ref, herkunft=herkunft,
        )
        return self._request("POST", "/lehren", json=body)

    def suche(
        self,
        q: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        subjekt_id: int | None = None,
        persona: str | None = None,
        alle: bool = False,
    ) -> dict[str, Any]:
        """``GET /suche`` — Volltext über Aussagen + Ereignisse.

        die Antwort ist ein **Objekt**, keine Liste
        mehr — ``{treffer, gesamt, abgeschnitten, weiter}``. Vorher schnitt der
        Kern stumm bei 100 ab; gemessen waren 290 Treffer, geliefert 100, und
        die Liste sah vollständig aus. Brechend, und das ist erlaubt, solange
        wir einziger Kunde sind (keine Kompatibilitäts-Schale: die würde die
        halbe Messung weiter wie eine ganze aussehen lassen).

        Wer alles will, blättert, bis ``weiter`` ``None`` ist::

            offset, alle_treffer = 0, []
            while True:
                seite = c.suche("pr:", offset=offset)
                alle_treffer += seite["treffer"]
                if seite["weiter"] is None:
                    break
                offset = seite["weiter"]
        """
        return self._request(
            "GET", "/suche",
            params={"q": q, "limit": limit, "offset": offset, "subjekt_id": subjekt_id,
                    "persona": persona, "alle": alle},
        )

    def export(self, art: str = "claude-md-section0", *, subjekt_id: int | None = None) -> str | bytes:
        """``GET /export/{art}`` — ``art`` ∈ ``claude-md-section0``/``agents-md``/``cursor-rules``.

        Die ersten beiden liefern Markdown/Text (``str``); ``cursor-rules``
        liefert ein ZIP (``bytes``).
        """
        if art not in _EXPORT_PFADE:
            raise ValueError(f"art muss eines von {sorted(_EXPORT_PFADE)} sein, nicht {art!r}")
        response = self._client.get(_EXPORT_PFADE[art], params=_ohne_leerwerte({"subjekt_id": subjekt_id}))
        if response.status_code >= 400:
            raise _fehler_aus_antwort(response.status_code, _body_aus_antwort(response))
        return response.content if art == "cursor-rules" else response.text


class AsyncCompass:
    """Asynchrones Gegenstück zu :class:`Compass`, dieselben Methoden/Signaturen."""

    def __init__(
        self, base_url: str, key: str, timeout: float = DEFAULT_TIMEOUT, *, sitzung: str | None = None,
        menschen_sitzung: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.key = key
        self.timeout = timeout
        self.sitzung = _sitzung_aufloesen(sitzung)
        headers = {"X-Compass-Key": key, "User-Agent": KLIENT}
        if self.sitzung:
            headers["X-Compass-Sitzung"] = self.sitzung
        # Der Kern belegt damit den Menschen (``benutzer_id``) -- ohne ihn bekommt ``regel_setzen`` 403.
        menschen_token = _menschen_sitzung_aufloesen(menschen_sitzung)
        if menschen_token:
            headers["Authorization"] = f"Bearer {menschen_token}"
        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}{API_PREFIX}",
            headers=headers,
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncCompass":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> Any:
        response = await self._client.request(method, path, params=_ohne_leerwerte(params or {}), json=json)
        body = _body_aus_antwort(response)
        if response.status_code >= 400:
            raise _fehler_aus_antwort(response.status_code, body)
        return body

    async def gilt(self, sache: str, *, subjekt_id: int | None = None, persona: str | None = None, alle: bool = False) -> dict[str, Any]:
        return await self._request(
            "GET", f"/gilt/{sache}", params={"subjekt_id": subjekt_id, "persona": persona, "alle": alle}
        )

    async def warum(self, sache: str, *, subjekt_id: int | None = None) -> dict[str, Any]:
        return await self._request("GET", f"/warum/{sache}", params={"subjekt_id": subjekt_id})

    async def sache_anlegen(
        self,
        slug: str,
        titel: str,
        frage: str,
        bereich: str | None = None,
        *,
        stufe: str | None = None,
        eltern_slug: str | None = None,
        subjekt_typ: str | None = None,
        persona_slug: str | None = None,
        nummer: str | None = None,
    ) -> dict[str, Any]:
        body = _sache_anlegen_body(
            slug, titel, frage, bereich,
            stufe=stufe, eltern_slug=eltern_slug, subjekt_typ=subjekt_typ,
            persona_slug=persona_slug, nummer=nummer,
        )
        return await self._request("POST", "/sachen", json=body)

    async def regel_setzen(
        self,
        sache: str,
        text: str,
        ersetzt: int | None = None,
        quelle: str | None = None,
        beleg: list[str] | None = None,
        *,
        herkunft: str = "entschieden",
        angelegt_von: str,
        subjekt_id: int | None = None,
        quelle_ref: str | None = None,
        gilt_seit: str | None = None,
    ) -> dict[str, Any]:
        body = _regel_setzen_body(
            sache, text, ersetzt, quelle, beleg,
            herkunft=herkunft, angelegt_von=angelegt_von, subjekt_id=subjekt_id,
            quelle_ref=quelle_ref, gilt_seit=gilt_seit,
        )
        return await self._request("POST", "/aussagen", json=body)

    async def lehre_festhalten(
        self,
        art: str,
        titel: str,
        was: str,
        lehre: str,
        ursache: str | None = None,
        belege: list[str] | None = None,
        *,
        angelegt_von: str,
        bereich: str | None = None,
        persona_slug: str | None = None,
        wirkung: str | None = None,
        regel_vorschlag: str | None = None,
        quelle: str | None = None,
        quelle_ref: str | None = None,
        herkunft: str | None = None,
    ) -> dict[str, Any]:
        body = _lehre_festhalten_body(
            art, titel, was, lehre, ursache, belege,
            angelegt_von=angelegt_von, bereich=bereich, persona_slug=persona_slug,
            wirkung=wirkung, regel_vorschlag=regel_vorschlag, quelle=quelle,
            quelle_ref=quelle_ref, herkunft=herkunft,
        )
        return await self._request("POST", "/lehren", json=body)

    async def suche(
        self,
        q: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        subjekt_id: int | None = None,
        persona: str | None = None,
        alle: bool = False,
    ) -> dict[str, Any]:
        """Wie ``Compass.suche`` — ein Objekt
        ``{treffer, gesamt, abgeschnitten, weiter}``, keine Liste."""
        return await self._request(
            "GET", "/suche",
            params={"q": q, "limit": limit, "offset": offset, "subjekt_id": subjekt_id,
                    "persona": persona, "alle": alle},
        )

    async def export(self, art: str = "claude-md-section0", *, subjekt_id: int | None = None) -> str | bytes:
        if art not in _EXPORT_PFADE:
            raise ValueError(f"art muss eines von {sorted(_EXPORT_PFADE)} sein, nicht {art!r}")
        response = await self._client.get(_EXPORT_PFADE[art], params=_ohne_leerwerte({"subjekt_id": subjekt_id}))
        if response.status_code >= 400:
            raise _fehler_aus_antwort(response.status_code, _body_aus_antwort(response))
        return response.content if art == "cursor-rules" else response.text
