import pytest

from flow.pipeline import Pipeline
from flow.retry import with_retries


@pytest.fixture
def pipe(tmp_path):
    return Pipeline(store_path=str(tmp_path / "s.json"),
                    crm_path=str(tmp_path / "c.json"))


def test_sales_auto_executes(pipe):
    r = pipe.handle({"id": "e1", "from": "a@b.com",
                     "subject": "pricing please", "body": "pricing"})
    assert r["status"] == "executed"


def test_billing_needs_approval_then_executes(pipe):
    r = pipe.handle({"id": "e2", "from": "a@b.com",
                     "subject": "refund", "body": "refund"})
    assert r["status"] == "awaiting_approval"
    r2 = pipe.on_approval(r["action_id"], approved=True)
    assert r2["status"] == "executed"


def test_denied_action_does_not_execute(pipe):
    r = pipe.handle({"id": "e3", "from": "a@b.com",
                     "subject": "cancel account", "body": "cancel"})
    r2 = pipe.on_approval(r["action_id"], approved=False)
    assert r2["status"] == "denied"


def test_stale_approval_cannot_fire_twice(pipe):
    r = pipe.handle({"id": "e4", "from": "a@b.com",
                     "subject": "refund", "body": "refund"})
    aid = r["action_id"]
    assert pipe.on_approval(aid, approved=True)["status"] == "executed"
    # second approval of the same action resolves to nothing
    assert pipe.on_approval(aid, approved=True)["status"] == "not_found"


def test_idempotent_intake(pipe):
    e = {"id": "dup", "from": "a@b.com", "subject": "pricing", "body": "pricing"}
    pipe.handle(e)
    assert pipe.handle(e)["status"] == "duplicate"


def test_retry_recovers_from_transient_failure():
    calls = {"n": 0}

    @with_retries(attempts=3, base_delay=0.001, exceptions=(ValueError,))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3
