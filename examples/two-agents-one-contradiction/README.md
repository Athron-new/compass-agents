# Two agents, one contradiction, one click

*Nordlicht* is a made-up small shop for sailing gear. Two of its assistants: **Sales** writes quotes, **Finance** sends invoices. Nobody at Nordlicht is real.

Play this in any MCP client connected to COMPASS, with two chats, one per assistant. Works in an empty project. If you started with the sample company, the payment-terms rule is already there and has a history, so skip to step 3.

### 1 · Finance proposes a rule
Finance (chat 1):
> "In COMPASS, propose a rule for the topic `payment-terms`: *Invoices are due within 30 days.* Use `frage_stellen` with this text as `regel_vorschlag`."

COMPASS does not store it as a rule yet. A question appears in the control room.

### 2 · You click
Open the control room (https://app.compassagents.io), find the question and choose the option that makes the rule hold. From now on the rule holds, with your name and the date.

### 3 · Sales reads it
Sales (chat 2):
> "What holds in COMPASS for `payment-terms`? Use `gilt`."

### 4 · The contradiction
The team agrees on 14 days. Finance does not overwrite anything. It proposes:
> "Propose a new rule for `payment-terms`: *Invoices are due within 14 days*, replacing the current one."

Agents cannot set rules themselves. If Finance tried to write the rule directly, COMPASS would refuse (HTTP 403). The proposal is the only way.

### 5 · One click
You click again. The 14-day rule now holds. **The 30-day rule is not gone**: it is marked as replaced.

### 6 · Ask why
Sales (chat 2):
> "Why does the 14-day rule hold? Use `warum` for `payment-terms`."

You see the chain: 30 days (replaced, with date) → 14 days (holds since, confirmed by). Ask `gilt_am` for a moment before your second click and you get 30 days, because that was true then.

**What just happened:** two agents never contradicted each other in silence. Every change went through a person, and the history stayed.

## Run it as a script

`run.py` plays both assistants with the Python SDK and the click with the sign-in of a person in your project. Use a throwaway project, it writes:

```sh
pip install -e sdk/python
COMPASS_API_URL=https://<your-compass-host>/api/v1 COMPASS_KEY=<read-write key> \
COMPASS_EMAIL=<a person in the project> COMPASS_PASSWORT=<their password> \
python3 examples/two-agents-one-contradiction/run.py
```
