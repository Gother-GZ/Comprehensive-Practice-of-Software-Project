from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.db.excel_importers import import_airlines_excel, import_vsp_excel
from app.db.init_db import initialize_database
from app.db.session import SessionLocal
from app.models.vsp import VspAirline, VspAirport, VspFrequency, VspNavaid, VspRunway, VspWaypoint


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python scripts/verify_vsp_import.py <vsp_xlsx_path> <airlines_xlsx_path>")
        raise SystemExit(1)

    db_path = ROOT / "tmp" / "vsp_import_verify.db"
    os.environ["SQLITE_PATH"] = str(db_path)

    initialize_database()
    with SessionLocal() as db:
        vsp_result = import_vsp_excel(db, sys.argv[1])
        airline_result = import_airlines_excel(db, sys.argv[2])
        counts = {
            "airports": db.scalar(select(func.count()).select_from(VspAirport)) or 0,
            "runways": db.scalar(select(func.count()).select_from(VspRunway)) or 0,
            "frequencies": db.scalar(select(func.count()).select_from(VspFrequency)) or 0,
            "navaids": db.scalar(select(func.count()).select_from(VspNavaid)) or 0,
            "waypoints": db.scalar(select(func.count()).select_from(VspWaypoint)) or 0,
            "airlines": db.scalar(select(func.count()).select_from(VspAirline)) or 0,
        }
        airport = db.scalar(select(VspAirport).where(VspAirport.icao_code == "VHHH"))

    print({"vsp": vsp_result, "airlines": airline_result, "counts": counts})
    if airport:
        print(
            {
                "airport_id": airport.airport_id,
                "icao_code": airport.icao_code,
                "airport_name": airport.airport_name,
                "lat": airport.lat,
                "lng": airport.lng,
                "elevation_ft": airport.elevation_ft,
            }
        )
    print("verify_vsp_import=ok")


if __name__ == "__main__":
    main()
