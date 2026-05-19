from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.init_db import initialize_database
from app.db.seed_data import seed_demo_vsp_data
from app.db.session import SessionLocal


def main() -> None:
    initialize_database()
    with SessionLocal() as db:
        seed_demo_vsp_data(db)
    print("seed_demo_data=ok")


if __name__ == "__main__":
    main()
