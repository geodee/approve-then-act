"""Business rules: a classification becomes a proposed action.

Rules, not vibes. This is deliberately boring and explicit, because the
whole system's behaviour should be auditable, not emergent.
"""


def decide(event, classification):
    category = classification["category"]
    priority = classification["priority"]

    if category == "billing":
        return {
            "type": "create_ticket",
            "queue": "billing",
            "needs_human": True,               # money moves get a human
            "summary": f"Billing: {event.get('subject', '')}",
        }

    if category == "support" and priority == "high":
        return {
            "type": "create_ticket",
            "queue": "support",
            "needs_human": True,
            "summary": f"Urgent support: {event.get('subject', '')}",
        }

    if category == "sales":
        return {
            "type": "crm_upsert",
            "needs_human": False,              # low-risk, safe to auto-run
            "contact": event.get("from"),
            "stage": "lead",
        }

    if category == "ops":
        return {"type": "noop", "needs_human": False}

    return {
        "type": "crm_upsert",
        "needs_human": False,
        "contact": event.get("from"),
        "stage": "triage",
    }
