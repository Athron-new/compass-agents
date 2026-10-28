# COMPASS

**Agent memory that knows what still holds.**

Other memory layers let a model decide in the background what still holds. In COMPASS a person decides, with one click and on the record. Nothing is deleted.

COMPASS is a hosted memory and rulebook for teams that run several AI agents on the same work. Every rule says since when it holds, who decided it, and what it replaced. Agents read the same answer. When something should change, an agent proposes it and a person confirms it.

> This repository holds the quickstart, examples and our benchmark. The COMPASS service itself is hosted in the EU and is not open source.

## Why

Monday you tell one assistant that customer Miller has cancelled. Wednesday another assistant sends Miller a new quote. Neither did anything wrong; they just did not share what holds.

With COMPASS the second assistant looks it up and finds: *Miller cancelled, since Monday, noted by your first assistant.* And if your team changes a rule, the old one is not overwritten. It stays readable as "replaced", with a date and a reason.

## What you get

- **Rules with a history.** Each rule carries *valid since*, *replaces* and *why*. Ask "what held on 4 September?" and get the answer for that day.
- **A person decides.** Agents cannot set rules on their own. They propose; you click in the control room; every agent reads the new rule from then on.
- **Nothing disappears.** A rule is replaced or ended, never deleted. You can always see what held before.
- **One memory for many agents.** Facts, decisions and lessons, shared with their origin and date.
- **Any MCP client.** Claude Code, Claude Desktop, claude.ai, Cursor or your own scripts.

## Quickstart (5 minutes)

1. **Create a free account:** https://compass.athron.io/registrieren
2. **Connect your client** (sign-in happens in the browser via OAuth):

   **Claude Code**
   ```sh
   claude mcp add --transport http compass https://compass.athron.io/mcp
   ```
   Then run `/mcp` in Claude Code and sign in.

   **Claude Desktop and claude.ai**
   Settings → Connectors → *Add custom connector* → URL `https://compass.athron.io/mcp` → sign in.

3. **Try it.** Ask your assistant:
   > "Call `erste_schritte` in COMPASS and show me what is there."

   Then run the example below: [two agents, one contradiction, one click](examples/two-agents-one-contradiction/).

## Claude Code plugin

```sh
/plugin marketplace add Athron-new/compass-agents
/plugin install compass@compass
```

The plugin connects Claude Code to COMPASS, adds a skill that says when to ask COMPASS, loads the briefing of a persona at session start, and rings when the persona's mailbox has something unread. See [`plugin/`](plugin/).

## Python

A small client over the HTTP API: `pip install -e sdk/python` from a checkout. See [`sdk/python/`](sdk/python/).

## Benchmark

We test what we claim. [`bench/`](bench/) describes how we compare COMPASS with other memory layers, what we measured, when, and with which limits. **We publish a number only together with the run that produced it.**

## Security and data

Hosted in the EU. Customers are separated in the database itself. Backups are encrypted. What your agents read from COMPASS goes to the language model you chose for them; that choice is yours. Details: https://athron.io/compass/ · Report a vulnerability: office@athron.io, details in [SECURITY.md](SECURITY.md)

## Links

Docs: https://docs.compass.athron.io · Product: https://athron.io/compass/ · Privacy: https://athron.io/privacy.html

*COMPASS is built by ATHRON.*
