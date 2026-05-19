from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.migrations import run_migrations
from app.db.session import engine


def main() -> None:
    summary = run_migrations(engine)
    print(summary.to_dict())
    print("run_migrations=ok")


if __name__ == "__main__":
    main()
