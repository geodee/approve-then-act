import logging
import os

from .retry import with_retries

log = logging.getLogger("flow.classify")


class TransientModelError(Exception):
    """Raised for retryable model/transport failures."""


# Deterministic keyword rules so the demo runs offline with zero setup.
# In production this is an LLM call; the return shape stays identical, and
# anything flagged sensitive is routed to a LOCAL model so private data
# never leaves the machine.
_RULES = [
    ("refund", "billing", "high"),
    ("charge", "billing", "high"),
    ("cancel", "billing", "high"),
    ("password", "support", "high"),
    ("login", "support", "high"),
    ("pricing", "sales", "medium"),
    ("demo", "sales", "medium"),
    ("quote", "sales", "medium"),
    ("unsubscribe", "ops", "low"),
]

_SENSITIVE = ("ssn", "medical", "diagnosis", "salary", "passport")


@with_retries(attempts=3, exceptions=(TransientModelError,))
def classify(event):
    """Return {'category', 'priority', 'sensitive'} for an inbound event.

    Uses an LLM when a provider key is configured, otherwise a deterministic
    stub so the demo is runnable and leaks nothing.
    """
    text = (event.get("subject", "") + " " + event.get("body", "")).lower()
    sensitive = any(w in text for w in _SENSITIVE)

    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"):
        # Real LLM path lives here. Sensitive items would be classified by a
        # local model instead of a hosted API. Kept out of the demo on purpose.
        pass

    for kw, category, priority in _RULES:
        if kw in text:
            log.info("event %s -> %s/%s (sensitive=%s)",
                     event.get("id"), category, priority, sensitive)
            return {"category": category, "priority": priority, "sensitive": sensitive}

    log.info("event %s -> other/low", event.get("id"))
    return {"category": "other", "priority": "low", "sensitive": sensitive}
