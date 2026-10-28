# compass-client (Python)

Python client for COMPASS, the operating layer for companies where people and AI agents work together. Its memory knows what still holds: every rule says since when it applies and why.
No MCP server needed: it talks to the core REST API directly. One dependency: `httpx`.

## Three lines

```python
from compass_client import Compass

c = Compass("http://localhost:18080", "<your-key>")
rule = c.gilt("deploy-approval")
print(rule["text"])
```

## Installation

Install from a checkout:

```bash
pip install -e sdk/python
```

## Methods

Each method maps to exactly one route of the REST reference; required fields and the 409/422
cases are documented there. `X-Compass-Key` is set once at construction and sent with every call.

In addition, when known: `X-Compass-Sitzung` — a session identifier that the core records only as
*declared*, never as proof (the key stays the proof). Source, in order: the constructor field
`sitzung`, then the environment variable `COMPASS_SITZUNG`. If neither is set the header is simply
left out — no invented value.

```python
c = Compass("http://localhost:18080", "<your-key>", sitzung="agent-7ccc6f")
```

| Method | Route |
|---|---|
| `gilt(sache, *, subjekt_id=None, persona=None, alle=False)` | `GET /gilt/{sache}` |
| `warum(sache, *, subjekt_id=None)` | `GET /warum/{sache}` |
| `sache_anlegen(slug, titel, frage, bereich=None, ...)` | `POST /sachen` |
| `regel_setzen(sache, text, ersetzt=None, quelle=None, beleg=None, ...)` | `POST /aussagen` (`art=regel`) |
| `lehre_festhalten(art, titel, was, lehre, ursache=None, belege=None, *, angelegt_von, ...)` | `POST /lehren` |
| `suche(q, *, limit=None, offset=None, ...)` | `GET /suche` — returns an object `{treffer, gesamt, abgeschnitten, weiter}`, not a list |
| `export(art="claude-md-section0", *, subjekt_id=None)` | `GET /export/{art}` |

`art` for `export()` is one of `claude-md-section0`, `agents-md`, `cursor-rules` — the first two
return text, `cursor-rules` returns a ZIP (`bytes`).

## Setting and replacing a rule

**A person sets rules.** With a key alone, the core answers `regel_setzen` with 403. The client
additionally needs the session token of a signed-in person — `menschen_sitzung=...` (or the
environment variable `COMPASS_MENSCHEN_SITZUNG`); the token comes from `POST /auth/anmelden`
(`sitzungs_token`). Like the key, it is a secret. **`COMPASS_MENSCHEN_SITZUNG` never belongs in an
agent's environment:** the core could no longer tell person and agent apart, and the rule
"a person sets rules" would be lifted for that agent. An agent without a person's session proposes
a rule (`lehre_festhalten` with `regel_vorschlag`); a person confirms it.

```python
c = Compass("http://localhost:18080", "<your-key>", menschen_sitzung="<session-token>")
c.sache_anlegen("deploy-approval", "Deploy approval", "Who may deploy after 6 pm?")
c.regel_setzen("deploy-approval", "Only with approval in #ops.", angelegt_von="ci-bot")

# A rule that already holds is only replaced through `ersetzt` — without it the core answers
# 409 (CompassFehler.extra["geltende"] carries the existing statement). No silent overwrite.
old = c.gilt("deploy-approval")
c.regel_setzen("deploy-approval", "No approval needed on Saturdays.", ersetzt=old["id"], angelegt_von="ci-bot")
```

## Errors

Every non-2xx response is raised as `CompassFehler`:

```python
from compass_client import CompassFehler

try:
    c.gilt("unknown-thing")
except CompassFehler as e:
    print(e.status, e.detail, e.feld)  # e.g. 404 "<sentence>" None
```

## Async

`AsyncCompass` mirrors the same methods and signatures as `async def`:

```python
from compass_client import AsyncCompass

async with AsyncCompass("http://localhost:18080", "<key>") as c:
    rule = await c.gilt("deploy-approval")
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT, see `LICENSE` in the repository root.
