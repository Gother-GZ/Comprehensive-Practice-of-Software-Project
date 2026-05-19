from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.consumer_service import ConsumerService


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python scripts/run_consumer_once.py <queue_name>")
        raise SystemExit(1)
    result = ConsumerService().consume_once(sys.argv[1])
    print(result)


if __name__ == "__main__":
    main()
