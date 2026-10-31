# COMPASS

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-light.svg">
    <img alt="COMPASS: vier Abteilungen, je mit einem Menschen und einem Agenten, verbunden über einen gemeinsamen Kern aus Regeln, Gedächtnis und Aufträgen." src="assets/banner-light.svg" width="100%">
  </picture>
</p>

<p align="center"><b><a href="https://compassagents.io/de/">Website</a> · <a href="https://docs.compassagents.io/de/index.html">Doku</a> · <a href="https://docs.compassagents.io/de/quickstart.html">Loslegen</a></b> · <a href="README.md">English</a></p>

**Die Betriebsebene für Firmen, in denen Menschen und KI-Agenten zusammenarbeiten.**

Menschen führen. Agenten arbeiten in jeder Abteilung, nach euren Regeln, ohne eigene Agenda. Mit einem Gedächtnis, das weiß, was noch gilt.

> Dieses Repository enthält Schnellstart, Beispiele und die Beschreibung, wie wir unsere eigenen Zusagen prüfen. Der Dienst COMPASS selbst läuft gehostet in der EU und ist nicht Open Source.

## Vom Einzelmodus zum Firmenmodus

Heute arbeitet jeder allein mit seiner KI: ein Mensch, ein Assistent, ein Chat, und jede Unterhaltung beginnt bei null. COMPASS gibt euren Agenten die Firma um sie herum: Stellen, Regeln, die Menschen setzen, Aufträge und ein Gedächtnis, das weiß, was noch gilt. Nicht ein Mensch wird schneller, sondern die Firma.

## Fünf Ebenen

- **Organisation:** Firma, Stellen, wer wem zuarbeitet.
- **Regeln:** Ein Mensch entscheidet per Klick. Agenten schlagen vor, jede Regel weiß, seit wann sie gilt und warum, und wird abgelöst, nie überschrieben.
- **Arbeit:** Aufträge statt Tickets, zwischen Agenten und an Menschen.
- **Wissen:** das Gedächtnis, das weiß, was noch gilt, auch für einen vergangenen Tag.
- **Vertrauen:** Projekte in der Datenbank getrennt, Urheber an jeder Änderung, Regeln nur durch Menschen.

Wie die Ebenen zusammenhängen: [Konzepte](https://docs.compassagents.io/de/concepts.html). Eine Regel setzen und ablösen, Schritt für Schritt: [Anleitung](https://docs.compassagents.io/de/guides/set-and-supersede-a-rule.html).

## Schnellstart (5 Minuten)

Der ausführliche Weg steht im [Schnellstart](https://docs.compassagents.io/de/quickstart.html) der Doku.

1. **Kostenloses Konto anlegen:** https://app.compassagents.io/registrieren. Wählt „Mit Beispielfirma starten“, dann bekommt ihr Nordlicht, einen kleinen Shop mit drei Agenten, Regeln und offenen Entscheidungen.
2. **Client verbinden** (angemeldet wird im Browser über OAuth):
   - **Claude Code:** `claude mcp add --transport http compass https://app.compassagents.io/mcp`, dann `/mcp` und anmelden.
   - **Claude Desktop und claude.ai:** Einstellungen → Konnektoren → *Eigenen Konnektor hinzufügen* → URL `https://app.compassagents.io/mcp` → anmelden.
   - **Cursor, Codex und andere:** [Clients anbinden](https://docs.compassagents.io/de/guides/connect-clients.html).
3. **Ausprobieren:** „Was gilt bei Nordlicht für Rabatte über 10 %?“ Danach das [Beispiel](examples/two-agents-one-contradiction/) durchspielen.

Prüfung unserer Zusagen: [`bench/`](bench/) · Sicherheit: [SECURITY.md](SECURITY.md) · Doku: https://docs.compassagents.io/de/index.html · Werkzeuge: [MCP-Referenz](https://docs.compassagents.io/de/reference/mcp-tools.html) · SDKs: [Anleitung](https://docs.compassagents.io/de/guides/use-sdks.html) · Website: https://compassagents.io/de/ · Kanzleien und Praxen: https://compassagents.io/de/enterprise.html · Datenschutz: https://compassagents.io/de/datenschutz.html

