import json
import os
import threading


class Store:
    """Tiny JSON-backed store with two production jobs:

    - idempotency: remember which event ids we've already handled, so a
      redelivered webhook doesn't get processed twice.
    - durable approvals: a proposed action is persisted, so a human's
      approve/deny still resolves to the right thing even if the process
      restarted in between. Writes are atomic (write-temp-then-rename).
    """

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._data = {"seen": [], "pending": {}, "executed": []}
        if os.path.exists(path):
            with open(path) as f:
                self._data = json.load(f)

    def _flush(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self.path)  # atomic on POSIX

    def seen(self, event_id):
        return event_id in self._data["seen"]

    def mark_seen(self, event_id):
        with self._lock:
            if event_id not in self._data["seen"]:
                self._data["seen"].append(event_id)
                self._flush()

    def add_pending(self, action_id, record):
        with self._lock:
            self._data["pending"][action_id] = record
            self._flush()

    def resolve(self, action_id):
        """Pop a pending action. Returns None if it's gone (expired or
        already handled) so a stale approval can't fire twice."""
        with self._lock:
            record = self._data["pending"].pop(action_id, None)
            self._flush()
            return record

    def list_pending(self):
        return dict(self._data["pending"])

    def mark_executed(self, action_id):
        with self._lock:
            if action_id not in self._data["executed"]:
                self._data["executed"].append(action_id)
                self._flush()
