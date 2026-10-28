#!/usr/bin/env python3
"""Two agents, one contradiction, one click -- the agents' steps as a script.

Northwind Studio is made up. Its assistant **Sales** writes quotes, **Billing** sends invoices. Neither may set
a rule; both may propose one. A person confirms with one click. This script plays the two agents with the
`compass_client` SDK and plays the person with the sign-in of a real person in your project -- you do not have
to be that person in a browser to see the whole chain.

Run it against a THROWAWAY project (it writes):

    pip install -e sdk/python
    COMPASS_API_URL=https://<your-compass-host>/api/v1 \\
    COMPASS_KEY=<read-write key> COMPASS_EMAIL=<a person in the project> COMPASS_PASSWORT=<their password> \\
    python3 examples/two-agents-one-contradiction/run.py

The password stays in the environment and is never printed. Every run uses a new topic (random suffix).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from compass_client import Compass, CompassFehler


def _env(name: str) -> str:
    wert = os.environ.get(name, "").strip()
    if not wert:
        sys.exit(f"{name} is not set. See the docstring of this file.")
    return wert


def _http(basis: str, pfad: str, *, key: str, body: dict | None = None, token: str | None = None) -> dict | list:
    """The routes the SDK does not wrap (sign-in, question, answer, point-in-time read) -- plain HTTP."""
    kopf = {"Content-Type": "application/json", "X-Compass-Key": key}
    if token:
        kopf["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(basis + pfad, data=json.dumps(body).encode() if body is not None else None,
                                 headers=kopf, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as antwort:
            return json.loads(antwort.read() or b"{}")
    except urllib.error.HTTPError as exc:
        sys.exit(f"{pfad}: HTTP {exc.code} {exc.read().decode()[:300]}")


def _vorschlag(api: str, key: str, sache: str, text: str, von: str, ersetzt: bool) -> int:
    """An agent proposes a rule: that is a question with the draft attached, never a rule."""
    frage = _http(api, "/fragen", key=key, body={
        "sache": sache,
        "frage": f"Should this become the rule? {text}",
        "gestellt_von": von,
        "regel_vorschlag": text,
        "regel_schluessel": "uebernehmen",
        "empfehlung_key": "uebernehmen",
        "optionen": [
            {"key": "uebernehmen", "label": "Make it the rule", "folge": text, "ersetzt_geltende": ersetzt},
            {"key": "ablehnen", "label": "Do not", "folge": "Nothing changes.", "ersetzt_geltende": False},
        ],
    })
    return frage["id"]


def main() -> int:
    api, key = _env("COMPASS_API_URL").rstrip("/"), _env("COMPASS_KEY")
    host = api.removesuffix("/api/v1")
    mensch = _http(api, "/auth/anmelden", key=key, body={"email": _env("COMPASS_EMAIL"), "passwort": _env("COMPASS_PASSWORT")})
    token = mensch["sitzungs_token"]
    sales, billing = Compass(host, key, sitzung="sales"), Compass(host, key, sitzung="billing")
    sache = f"payment-terms-{secrets.token_hex(3)}"

    def klick(frage_id: int) -> None:
        _http(api, f"/fragen/{frage_id}/antwort", key=key, token=token, body={"key": "uebernehmen", "beantwortet_von": "person"})

    print(f"Topic: {sache}")
    sales.sache_anlegen(sache, "Payment terms", "When are invoices due?", bereich="unsortiert")

    print("1. Sales proposes a rule. That is a question in the control room, not a rule.")
    f1 = _vorschlag(api, key, sache, "Invoices are due within 30 days.", "sales", ersetzt=False)
    try:
        billing.gilt(sache)
        print("   !! something already holds -- this must not happen before the click")
        return 1
    except CompassFehler as exc:
        print(f"   nothing holds before the click (HTTP {exc.status})")

    print("2. One click.")
    klick(f1)
    time.sleep(1.2)

    print("3. Billing reads what holds.")
    print(f"   {billing.gilt(sache)['text']!r}")
    stand_davor = dt.datetime.now(dt.timezone.utc)
    time.sleep(1.2)

    print("4. The team agrees on 14 days. Billing tries to write the rule itself -- and is refused.")
    try:
        billing.regel_setzen(sache, "Invoices are due within 14 days.", angelegt_von="billing")
        print("   !! the core let an agent set a rule -- this must not happen")
        return 1
    except CompassFehler as exc:
        print(f"   refused: HTTP {exc.status}")
    print("   So Billing proposes, and says the proposal replaces the current rule.")
    f2 = _vorschlag(api, key, sache, "Invoices are due within 14 days.", "billing", ersetzt=True)
    print(f"   still holds: {billing.gilt(sache)['text']!r}")

    print("5. One more click.")
    klick(f2)
    neu = billing.gilt(sache)["text"]
    print(f"   now holds: {neu!r}")

    print("6. Ask why -- and ask what held before the second click.")
    verlauf = json.dumps(sales.warum(sache), ensure_ascii=False)
    fruehere = _http(api, f"/gilt-am/{sache}?datum={urllib.parse.quote(stand_davor.isoformat())}", key=key)
    # `gilt_am` lists every statement that held, the rule and the decision the click recorded; the rule is what we ask for.
    alt = [a["text"] for a in fruehere if a.get("art") == "regel"]
    print(f"   the 30-day rule is in the history: {'30 days' in verlauf}")
    print(f"   the rule that held just before the second click: {alt}")
    ok = neu == "Invoices are due within 14 days." and "30 days" in verlauf and alt == ["Invoices are due within 30 days."]
    print("OK" if ok else "UNEXPECTED -- the chain did not come out as described")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
