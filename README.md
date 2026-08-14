# approve-then-act

A small, production-shaped AI intake workflow. An event comes in, an LLM
classifies it against business rules, and the system either runs a safe action
on its own or **proposes** a riskier one and waits for a human to approve it
before touching anything.

It's deliberately tiny, but it's built the way a real one has to be: retries,
idempotency, durable approvals, structured logging, and a clean seam to swap
the stubs for real services. The core runs on the Python standard library, so
you can try it in ten seconds with nothing to install.

```
  event ──▶ ingest ──▶ classify ──▶ decide ──┬─▶ (safe)   execute
          (dedupe)     (LLM/rules)  (rules)   │
                                              └─▶ (risky)  propose ──▶ human ──▶ execute
                                                                       approve/deny
        reliability everywhere: retries · idempotency · durable state · logging
```

## Try it

```bash
python demo.py          # feed sample events through the pipeline
python approve.py       # see what's waiting on a human
python approve.py approve <id>   # approve it -> it executes
python approve.py deny <id>      # deny it -> nothing happens
```

Run `python demo.py` twice: the second run reports the events as duplicates
instead of processing them again. That's the idempotency doing its job.

```bash
pip install pytest && pytest -q      # the test suite
```

## What it demonstrates

This is the difference between a quick automation and something you can leave
running:

- **Human-in-the-loop by design.** Anything risky (a refund, an account
  change) is proposed, not fired. The pending action is stored durably, so a
  human's approve/deny still resolves correctly even if the process restarted
  in between — and a stale approval can't fire the same action twice.
- **Idempotent intake.** A redelivered webhook is recognised and skipped, so
  you never double-process an event or double-write a record.
- **Fails safely.** Model and API calls retry with exponential backoff; CRM
  writes are idempotent, so a retry is never a duplicate.
- **Auditable decisions.** Classification feeds explicit business rules, not
  emergent behaviour. You can read exactly why any action was taken.
- **Privacy-aware.** Items flagged sensitive are meant to be classified by a
  local model, never a hosted API. (Stubbed here; the seam is in `classify.py`.)
- **Observable.** Structured logs at every step.

## Layout

```
flow/
  classify.py   LLM-or-stub classifier (retryable)
  decide.py     classification -> a proposed action (explicit rules)
  store.py      idempotency + durable pending approvals (atomic JSON)
  crm.py        stand-in for HubSpot/Salesforce/Airtable (idempotent writes)
  pipeline.py   the loop: handle() and on_approval()
  retry.py      backoff decorator
demo.py         run the sample events
approve.py      the human side (CLI here; a Telegram/Slack button in prod)
```

## Making it real

Every stub is a single-file swap, and the contract around it doesn't change:

- **Classifier** → a real LLM call in `classify.py` (sensitive items to a local
  model). Return the same `{category, priority, sensitive}` shape.
- **CRM** → a real client in `crm.py`. Keep writes idempotent by action id.
- **Approvals** → replace the CLI in `approve.py` with a Telegram/Slack button;
  `pipeline.on_approval()` stays exactly the same.

## License

MIT.
