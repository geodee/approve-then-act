import hashlib
import json
import logging

from .classify import classify
from .crm import FakeCRM
from .decide import decide
from .store import Store

log = logging.getLogger("flow.pipeline")


def _action_id(event, action):
    raw = json.dumps({"e": event.get("id"), "a": action}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


class Pipeline:
    """The whole loop: intake -> classify -> decide -> (approve) -> execute.

    Nothing that touches the outside world fires without either a rule that
    says it's safe or an explicit human approval.
    """

    def __init__(self, store_path="state.json", crm_path="crm.json"):
        self.store = Store(store_path)
        self.crm = FakeCRM(crm_path)

    def handle(self, event):
        event_id = event["id"]
        if self.store.seen(event_id):
            log.info("skip %s (already handled)", event_id)   # idempotent intake
            return {"status": "duplicate", "event": event_id}

        classification = classify(event)                      # retried LLM/stub
        action = decide(event, classification)                # explicit rules
        action_id = _action_id(event, action)
        self.store.mark_seen(event_id)

        if action.get("needs_human"):
            self.store.add_pending(action_id, {"event": event_id, "action": action})
            log.info("proposed %s, awaiting approval", action_id)
            return {"status": "awaiting_approval", "action_id": action_id, "action": action}

        result = self._execute(action_id, action)
        return {"status": "executed", "action_id": action_id, "result": result}

    def on_approval(self, action_id, approved):
        record = self.store.resolve(action_id)
        if not record:
            return {"status": "not_found", "action_id": action_id}  # expired / handled
        if not approved:
            log.info("denied %s (noop)", action_id)
            return {"status": "denied", "action_id": action_id}
        result = self._execute(action_id, record["action"])
        return {"status": "executed", "action_id": action_id, "result": result}

    def _execute(self, action_id, action):
        if action.get("type") == "noop":
            return {"noop": True}
        applied = self.crm.apply(action_id, action)          # idempotent + retried
        self.store.mark_executed(action_id)
        return applied
