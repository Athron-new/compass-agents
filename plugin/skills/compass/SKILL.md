---
name: compass
description: COMPASS-Gedächtnis (Agenten-Regelwerk, das weiß, was noch gilt) ansprechen — bevor eine Regel angenommen wird, wenn beim Arbeiten etwas schiefgegangen ist, oder wenn eine bestehende Regel nicht mehr zu stimmen scheint. Nutzen, um zu prüfen ob eine Regel noch gilt, um eine Lehre festzuhalten, oder um eine Frage an den Menschen zu stellen — nie um eine Regel selbst zu ändern.
---

# COMPASS

COMPASS ist das Gedächtnis, das weiß, was noch gilt. Es speichert Regeln,
nicht nur Fakten — und jede gespeicherte Regel sagt, ob sie noch gilt und warum. Diese Skill
nennt die drei Momente, in denen ein Agent COMPASS ansprechen sollte, und das jeweils passende
Werkzeug. Alle Namen unten sind MCP-Werkzeuge von COMPASS (siehe Abschnitt „Werkzeuge").

## 1. Bevor eine Regel angenommen wird

Bevor du eine Annahme über „so machen wir das hier" triffst oder befolgst, frag COMPASS statt
zu vermuten:

1. `gilt` — die eine geltende Regel für eine Sache, mit Beleg und `gilt_seit`. Eine Antwort mit
   `gilt: false` ist ein gültiger Leerzustand (es gibt einfach noch keine Regel), kein Fehler.
2. `warum`, wenn du den Beleg oder die Historie brauchst — den Wortlaut der Entscheidung, frühere
   abgelöste Regeln, das letzte Prüfweg-Ergebnis.
3. `sache_get` / `sache_list`, um die passende Sache überhaupt erst zu finden.

Messen schlägt herleiten: eine Regel aus COMPASS schlägt jede Vermutung aus dem eigenen
Kontext oder Training.

## 2. Wenn etwas schiefgegangen ist

Ein Fehler, ein überraschender Erfolg oder ein Hinweis, den ein künftiger Lauf brauchen wird,
gehört als Lehre festgehalten — nicht als Regel, und nicht nur im eigenen Kontextfenster, das
die nächste Sitzung nicht mehr hat:

- `lehre_put` — `art` ist `fehler` (Ursache ist dann Pflicht), `gelungen` oder `hinweis`.
- `hinweis_an_mensch`, wenn die Lehre ausdrücklich für den Menschen bestimmt ist, nicht für die
  nächste Agenten-Sitzung.

Eine Lehre sagt „das ist mir passiert" — sie ist kein Regelvorschlag und ändert nichts am
Regelwerk.

## 3. Wenn eine Regel nicht mehr zu stimmen scheint

**Nie selbst ändern.** Eine Regel setzen oder ablösen ist die Sache eines Menschen, nicht die eines
Agenten. Wenn eine geltende Regel falsch wirkt:

1. `lehre_put` mit `art="fehler"` oder `art="hinweis"`, damit der Widerspruch nicht verloren geht.
2. `lehre_regel_vorschlagen`, falls ein konkreter neuer Regeltext sinnvoll ist — das Werkzeug
   stellt dabei **immer nur die Klickfrage**, es setzt nie selbst eine neue Regel.
3. `frage_stellen`, wenn die Entscheidung dringend ist: Empfehlung zuerst, jede Option mit ihrer
   Folge, höchstens vier Optionen — dann auf die Antwort warten, nicht auf eigene Faust umsetzen.

`aussage_put` (eine Regel setzen/ablösen) ist ein echtes MCP-Werkzeug, aber für einen
Agenten nur auf ausdrückliche Anweisung eines Menschen gedacht — nie als Reaktion auf einen
eigenen Verdacht.

## Werkzeuge (exakte Namen)

- `gilt`
- `warum`
- `sache_get`
- `sache_list`
- `abweichungen`
- `aussage_put`
- `lehre_put`
- `hinweis_an_mensch`
- `lehre_regel_vorschlagen`
- `frage_stellen`
- `offen_fuer_mensch`
- `persona_brief`
- `memory_search`

## Weiteres Nachschlagen

- `offen_fuer_mensch` — was gerade auf eine menschliche Antwort wartet, bevor du eine neue Frage
  stellst (keine doppelten Fragen).
- `persona_brief` — der eigene deterministische Brief (Aufgabe, Regeln im Sichtfeld, Gedächtnis,
  jüngste Lehren); Ausgangspunkt jeder Sitzung mit einer festen Persona. Läuft dieses Plugin mit
  `COMPASS_URL`/`COMPASS_KEY`/`COMPASS_PERSONA`, holt der SessionStart-Hook ihn bereits automatisch.
- `memory_search` — das eigene Gedächtnis durchsuchen, bevor du etwas als neu behandelst, das
  schon einmal notiert wurde.
