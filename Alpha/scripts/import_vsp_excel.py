from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.excel_importers import import_airlines_excel, import_vsp_excel
from app.db.init_db import initialize_database
from app.db.session import SessionLocal


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python scripts/import_vsp_excel.py <vsp_xlsx_path> <airlines_xlsx_path>")
        raise SystemExit(1)

    vsp_path = sys.argv[1]
    airlines_path = sys.argv[2]

    initialize_database()
    with SessionLocal() as db:
        vsp_result = import_vsp_excel(db, vsp_path)
        airline_result = import_airlines_excel(db, airlines_path)
    print({"vsp": vsp_result, "airlines": airline_result})


if __name__ == "__main__":
    main()

