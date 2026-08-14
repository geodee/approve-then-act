"""The human-in-the-loop side. In production this is a Telegram/Slack button;
here it's a CLI so the demo stays self-contained.

    python approve.py                 # list what's waiting
    python approve.py approve <id>    # approve -> it executes
    python approve.py deny <id>       # deny -> nothing happens
"""
import logging
import sys

from flow.pipeline import Pipeline

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)-7s %(name)-13s %(message)s")


def main():
    pipe = Pipeline()
    args = sys.argv[1:]

    if not args or args[0] == "list":
        pending = pipe.store.list_pending()
        if not pending:
            print("Nothing pending.")
            return
        for action_id, record in pending.items():
            action = record["action"]
            print(f"{action_id}  {action['type']:<14} {action.get('summary', '')}")
        print("\napprove:  python approve.py approve <id>")
        print("deny:     python approve.py deny <id>")
        return

    cmd, action_id = args[0], args[1]
    result = pipe.on_approval(action_id, approved=(cmd == "approve"))
    print(result)


if __name__ == "__main__":
    main()
