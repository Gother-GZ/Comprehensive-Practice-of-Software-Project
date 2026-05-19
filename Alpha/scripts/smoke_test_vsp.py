from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.db.excel_importers import import_airlines_excel, import_vsp_excel
from app.db.init_db import initialize_database
from app.db.session import SessionLocal
from app.main import app


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python scripts/smoke_test_vsp.py <vsp_xlsx_path> <airlines_xlsx_path>")
        raise SystemExit(1)

    initialize_database()
    with SessionLocal() as db:
        import_vsp_excel(db, sys.argv[1])
        import_airlines_excel(db, sys.argv[2])

    client = TestClient(app)
    checks = [
        "/api/v1/vsp/airports?icao_code=VHHH",
        "/api/v1/vsp/waypoints?type=navaid&page=1&page_size=20",
        "/api/v1/vsp/runways?airport_id=airport_vhhh",
        "/api/v1/vsp/frequencies?airport_id=airport_vhhh",
        "/api/v1/vsp/navaids?airport_id=airport_vhhh",
        "/api/v1/vsp/airlines?airline_code=CX",
    ]

    for path in checks:
        response = client.get(path)
        body = response.json()
        if response.status_code != 200 or body.get("code") != 0:
            raise RuntimeError(f"request failed: {path} -> {response.status_code} {body}")

        data = body.get("data")
        if isinstance(data, list) and not data:
            raise RuntimeError(f"empty response for path: {path}")

    print("smoke_test_vsp=ok")


if __name__ == "__main__":
    main()
