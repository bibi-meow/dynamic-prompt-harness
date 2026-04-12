import sys
from pathlib import Path
from .dispatcher import Dispatcher

def main() -> int:
    if len(sys.argv) < 2:
        return 0
    trigger = sys.argv[1]
    raw = sys.stdin.read()
    return Dispatcher(base=Path.cwd()).run(trigger, raw)

if __name__ == "__main__":
    sys.exit(main())
