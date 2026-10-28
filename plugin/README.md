# compass — COMPASS as a Claude Code plugin

COMPASS is the operating layer for companies where people and AI agents work together. Its memory
knows what still holds: every stored rule says whether it still applies, since when, and why. This
plugin connects Claude Code to COMPASS in two commands.

```
/plugin marketplace add Athron-new/compass-agents
/plugin install compass@compass
```

It installs:

- the COMPASS MCP server connection (`.mcp.json`, streamable HTTP),
- the skill `compass` (`skills/compass/SKILL.md`) — when to talk to COMPASS: before assuming a
  rule, when something went wrong, when a rule no longer seems to hold,
- a `SessionStart` hook that loads the briefing of a persona when the session starts,
- two `Stop` hooks: one rings when the persona's mailbox has something unread (read-only), one
  reports this session's token usage (the only hook that writes — remove it from your hook
  configuration if you do not want that).

## Environment variables

None of them has a real value in this repository. Set them in your own environment before
`claude` starts.

| Variable | Needed for | Meaning |
|---|---|---|
| `COMPASS_MCP_URL` | the MCP server | full MCP endpoint, e.g. `https://<host>/mcp` |
| `COMPASS_KEY` | MCP server **and** hooks | your `X-Compass-Key` (read-only or read-write; the core refuses writing tools for a read-only key) |
| `COMPASS_URL` | the hooks | base of the core REST API, e.g. `https://<host>/api/v1` — not the same address as `COMPASS_MCP_URL`; core and MCP are two services |
| `COMPASS_PERSONA` | the hooks | slug of the persona whose briefing is loaded at session start |
| `COMPASS_SITZUNG` | the hooks, optional | the session identifier of this client; sent as `X-Compass-Sitzung`. The core records it as *declared*, never as proof |

Where you get your key: the *Connect* page of your COMPASS instance.

If `COMPASS_MCP_URL` or `COMPASS_KEY` is missing, the MCP server does not connect (Claude Code
shows a failed connection under `/mcp`). If one of the three hook variables (`COMPASS_URL`,
`COMPASS_KEY`, `COMPASS_PERSONA`) is missing, the hooks stay silent: exit 0, no output, no
error, the session starts normally. Missing configuration closes, it never opens.

## What the hooks do

- **`hooks/session_start.py`** calls `GET {COMPASS_URL}/personas/{COMPASS_PERSONA}/brief` and
  prints the deterministic Markdown briefing as additional context. Time limit 3 seconds — a
  slow or unreachable core never delays the session. The key itself never appears in the output.
- **`hooks/stop.py`** rings at the end of a turn when the persona's mailbox has something
  unread. It only reads.
- **`hooks/verbrauch_melden.py`** reports token usage to `POST {COMPASS_URL}/agents/verbrauch`:
  it reads the session transcript (path given by Claude Code on stdin), sums `message.usage`
  per (day, model) and sends the sums. Numbers only (tokens, calls, time) — never content from
  the transcript. Reports are cumulative, not increments: the core replaces the row, so a
  repeated report is not a double count.

## The key in the header

`.mcp.json` carries the key only as `${COMPASS_KEY}` — plain variable substitution, no literal
and no fallback value.

## Tests

```
cd plugin && python -m pytest tests -q
```

`tests/mcp_werkzeuge.txt` is a snapshot of the MCP server's tool names; the test
`test_skill_nennt_nur_existierende_mcp_werkzeuge` checks that the skill names only tools that
exist. The server lives outside this repository, so the snapshot is renewed from there.

## License

MIT, see `LICENSE` in the repository root.
