# Two agents, one contradiction, one click

A made-up agency, *Northwind Studio*, runs two assistants: **Sales** writes quotes, **Billing** sends invoices. Nobody at Northwind is real.

You can play this in any MCP client connected to COMPASS. Open two chats, one per assistant. Or run the agents' steps as a script (see [Run it as a script](#run-it-as-a-script)); you can still do the click yourself in the control room.

### 1 · Sales proposes a rule

Sales (chat 1):
> "In COMPASS, propose a rule for the topic `payment-terms`: *Invoices are due within 30 days.* Use `frage_stellen` with this text as `regel_vorschlag`."

COMPASS does not store it as a rule. A question appears in the control room.

### 2 · You click

Open the control room (https://compass.athron.io), find the question and choose the option that makes the rule hold.

From now on the rule holds, with your name and the date.

### 3 · Billing reads it

Billing (chat 2):
> "What holds in COMPASS for `payment-terms`? Use `gilt`."

Answer: *Invoices are due within 30 days*, since today, confirmed by you.

### 4 · The contradiction

A week later the team agrees on 14 days. Billing does not overwrite anything. It proposes:
> "Propose a new rule for `payment-terms`: *Invoices are due within 14 days*, replacing the current one. Use `frage_stellen` and mark the option that makes it hold as replacing the current rule (`ersetzt_geltende`)."

Agents cannot set rules themselves. If Billing tried to write the rule directly, COMPASS would refuse (HTTP 403). The proposal is the only way.

### 5 · One click

You click once more. The 14-day rule now holds. **The 30-day rule is not gone**: it is marked as replaced.

### 6 · Ask why

Sales (chat 1):
> "Why does the 14-day rule hold? Use `warum` for `payment-terms`."

You see the chain: 30 days (replaced, with date) → 14 days (holds since, confirmed by). Ask `gilt_am` for a moment before your second click and you get 30 days, because that was true then.

**What just happened:** two agents never contradicted each other in silence. Every change went through a person, and the history stayed.

### Run it as a script

`run.py` plays the two agents with the Python SDK and the person with the sign-in of a real person in your project, so you can see the whole chain without two chats. Use a throwaway project: it writes.

```sh
pip install -e sdk/python
COMPASS_API_URL=https://compass.athron.io/api/v1 COMPASS_KEY=<read-write key> \
COMPASS_EMAIL=<a person in the project> COMPASS_PASSWORT=<their password> \
python3 examples/two-agents-one-contradiction/run.py
```

It checks every step: nothing holds before the click, an agent writing the rule directly is refused (403), the rule changes only after the second click, the 30-day rule stays in the history, and `gilt_am` for the moment before the second click still says 30 days. It prints `OK` when the chain came out as described.
