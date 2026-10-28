# Benchmark: does the memory know what still holds?

**Question:** You tell a memory layer something, then later tell it something that contradicts it. Does the memory keep track of which statement holds now, and can it tell you what held before?

**Method of the comparison:**
1. A fixed set of statements, some of which explicitly revoke earlier ones.
2. Each system receives the statements in the same order, through its normal API.
3. We then ask questions and record: which statement is returned first, whether the outdated one is marked, and whether the history can be read.
4. Every run is published with its date, system version, plan and limits.

**What this folder publishes:** the method above and the reality check below. A comparison number is published only together with the run that produced it, with date, system version, plan and limits, using public statements anyone can reproduce, and next to the strengths of the other systems.

**Rules we hold ourselves to:**
- We write "in our run of <date>", never "system X cannot do this".
- We name the plan, version and time window of every run.
- If another system does something better (for example, automatic fact extraction from conversations), it goes in the table.

## What is in this folder: a reality check

A different question from the comparison: does a stored rule still match the world? COMPASS can attach a *check* to a rule, a read-only command that touches the real thing, and writes the result back as a fact. Five small cases show it; one of them is a control that must come back without a deviation, because a bench with only drift cases cannot tell a check that detects drift from a check that always raises an alarm.

| Case | What drifted |
|---|---|
| `five-checks-became-three` | a decision says five required CI checks; the file the CI is generated from lists three |
| `template-folder-does-not-exist` | a rule points to a folder that is not there |
| `rule-points-to-a-frozen-page` | a policy forbids links to a read-only wiki; the one document people open still has one |
| `decision-never-carried-out` | a decision to rotate keys in October; the log ends in July |
| `control-rule-still-holds` | **the control**: nothing drifted, and the check must say so |

## Run it

You need a COMPASS instance you may write to (a throwaway one) and a read-write key.

```bash
# on the COMPASS core: run the checks from bench/world
export COMPASS_HOST_RO_ROOT="$PWD/bench/world"      # then restart the core

python3 bench/lauf.py --base-url http://localhost:18080/api/v1 --key <read-write-key>
```

The core runs each command without a shell and with `bench/world` as working directory, so
`cat ci/required-checks.txt` reads `bench/world/ci/required-checks.txt`. Without
`COMPASS_HOST_RO_ROOT` a `host-ro` check is *not measurable* — and the bench counts that as a miss, not
as green.

Exit code `0`: all five cases come back as expected. `1`: at least one does not. `2`: the setup is
broken (case files missing, instance not answering) — and then there is no result at all.

## Case format

```json
{
  "sache": "slug of the thing the rule is about",
  "frage": "the question the rule answers",
  "regel": "what should hold, with source and date",
  "ort": "where in the world this can be checked",
  "wirklichkeit_soll": "the state the rule demands",
  "wirklichkeit_ist": "the state actually measured",
  "erwartete_abweichung": true,
  "notiz": "why the drift happened, what it shows",
  "pruefweg_befehl": "the read-only command",
  "erwartung": "returncode == 0 and count == 5",
  "laufumgebung": "host-ro"
}
```

`erwartete_abweichung: true` means: run against COMPASS, the check must come back with
`abweichung: true`. If it comes back `false`, either the check is broken or the drift was fixed in the
meantime — then the case must be updated, not quietly accepted as green.
