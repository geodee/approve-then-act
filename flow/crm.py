import json
import logging
import os

from .retry import with_retries

log = logging.getLogger("flow.crm")


class FlakyAPIError(Exception):
    """Retryable downstream-API failure."""


class FakeCRM:
    """Stands in for HubSpot / Salesforce / Airtable.

    Writes are idempotent: applying the same action id twice is a no-op.
    That's what makes retries safe. Swapping this for a real CRM client is
    a one-file change; the idempotency contract stays the same.
    """

    def __init__(self, path):
        self.path = path
        self.records = {}
        if os.path.exists(path):
            with open(path) as f:
                self.records = json.load(f)

    @with_retries(attempts=3, exceptions=(FlakyAPIError,))
    def apply(self, action_id, action):
        if action_id in self.records:
            log.info("crm: %s already applied (idempotent no-op)", action_id)
            return self.records[action_id]
        self.records[action_id] = action
        with open(self.path, "w") as f:
            json.dump(self.records, f, indent=2)
        log.info("crm: applied %s (%s)", action_id, action.get("type"))
        return action
