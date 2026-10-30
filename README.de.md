# COMPASS

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-light.svg">
    <img alt="COMPASS: vier Abteilungen, je mit einem Menschen und einem Agenten, verbunden über einen gemeinsamen Kern aus Regeln, Gedächtnis und Aufträgen." src="assets/banner-light.svg" width="100%">
  </picture>
</p>

[English](README.md) · Website: **[compassagents.io](https://compassagents.io/de/)**

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

## Schnellstart (5 Minuten)

1. **Kostenloses Konto anlegen:** https://compass.athron.io/registrieren. Wählt „Mit Beispielfirma starten“, dann bekommt ihr Nordlicht, einen kleinen Shop mit drei Agenten, Regeln und offenen Entscheidungen.
2. **Client verbinden** (angemeldet wird im Browser über OAuth):
   - **Claude Code:** `claude mcp add --transport http compass https://compass.athron.io/mcp`, dann `/mcp` und anmelden.
   - **Claude Desktop und claude.ai:** Einstellungen → Konnektoren → *Eigenen Konnektor hinzufügen* → URL `https://compass.athron.io/mcp` → anmelden.
3. **Ausprobieren:** „Was gilt bei Nordlicht für Rabatte über 10 %?“ Danach das [Beispiel](examples/two-agents-one-contradiction/) durchspielen.

Prüfung unserer Zusagen: [`bench/`](bench/) · Sicherheit: [SECURITY.md](SECURITY.md) · Doku: https://docs.compass.athron.io · Website: https://compassagents.io/de/ · Kanzleien und Praxen: https://compassagents.io/de/enterprise.html · Datenschutz: https://compassagents.io/de/datenschutz.html

