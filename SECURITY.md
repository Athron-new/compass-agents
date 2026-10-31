# Security

## Reporting a vulnerability

Please report security issues privately to **office@athron.io**. Do not open a public issue.

Include what you found, how to reproduce it, and what you think the impact is. We will confirm receipt and keep you informed until it is fixed.

## Scope

This repository contains examples, a quickstart and a benchmark. The COMPASS service at `app.compassagents.io` (and at its earlier address `compass.athron.io`, which stays active) is in scope for reports as well. Please test only with your own account, do not access other customers' data, and do not run load or denial-of-service tests.

## How COMPASS protects data

- Hosted in the EU.
- Each customer is separated by row-level security in the database; the application role cannot bypass it.
- Backups are encrypted before they leave the server.
- By default COMPASS calls no external AI service in your data path.
- What your agents read from COMPASS is sent to the language model you chose for them. That provider is your decision.
