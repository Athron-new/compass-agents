# COMPASS

**Das Gedächtnis für KI-Agenten, das weiß, was noch gilt.**

Andere Gedächtnisse lassen ein Modell im Hintergrund entscheiden, was noch gilt. Bei COMPASS entscheidet das ein Mensch, mit einem Klick und nachlesbar. Gelöscht wird nichts.

COMPASS ist ein gehostetes Gedächtnis und Regelwerk für Teams, in denen mehrere KI-Agenten an derselben Sache arbeiten. Jede Regel sagt, seit wann sie gilt, wer sie entschieden hat und was sie abgelöst hat. Alle Agenten lesen dieselbe Antwort. Soll sich etwas ändern, schlägt ein Agent es vor, und ein Mensch bestätigt es.

> Dieses Repository enthält Schnellstart, Beispiele und unseren Prüfstand. Der Dienst COMPASS selbst läuft gehostet in der EU und ist nicht Open Source.

## Schnellstart (5 Minuten)

1. **Kostenloses Konto anlegen:** https://compass.athron.io/registrieren
2. **Client verbinden** (angemeldet wird im Browser über OAuth):
   - **Claude Code:** `claude mcp add --transport http compass https://compass.athron.io/mcp`, dann `/mcp` und anmelden.
   - **Claude Desktop und claude.ai:** Einstellungen → Konnektoren → *Eigenen Konnektor hinzufügen* → URL `https://compass.athron.io/mcp` → anmelden.
3. **Ausprobieren:** „Ruf in COMPASS `erste_schritte` auf und zeig mir, was da ist.“ Danach das [Beispiel](examples/two-agents-one-contradiction/) durchspielen.

## Was ihr bekommt

- **Regeln mit Geschichte:** gilt seit, löst ab, warum. Auch für einen vergangenen Tag abfragbar.
- **Ein Mensch entscheidet:** Agenten setzen keine Regeln selbst. Sie schlagen vor, ihr klickt.
- **Nichts verschwindet:** Eine Regel wird abgelöst oder beendet, nie gelöscht.
- **Ein Gedächtnis für viele Agenten:** Fakten, Entscheidungen und Lehren mit Herkunft und Datum.

Prüfstand: [`bench/`](bench/) · Sicherheit: office@athron.io, Einzelheiten in [SECURITY.md](SECURITY.md) · Doku: https://docs.compass.athron.io
