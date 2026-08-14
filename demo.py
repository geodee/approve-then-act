"""Feed the sample events through the pipeline and show what happens.

    python demo.py
"""
import json
import logging

from flow.pipeline import Pipeline

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)-7s %(name)-13s %(message)s")


def main():
    pipe = Pipeline()
    events = json.load(open("sample_events.json"))

    print(f"\nFeeding {len(events)} events through the pipeline:\n")
    for e in events:
        result = pipe.handle(e)
        print(f"  {e['id']:<8} {e['subject'][:36]:<38} -> {result['status']}")

    pending = pipe.store.list_pending()
    if pending:
        print("\nAwaiting human approval  (run:  python approve.py)")
        for action_id, record in pending.items():
            action = record["action"]
            print(f"  {action_id}  {action['type']:<14} {action.get('summary', '')}")
    print()


if __name__ == "__main__":
    main()
