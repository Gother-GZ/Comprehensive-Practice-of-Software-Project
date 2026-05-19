from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.common.exceptions import not_found
from app.models.vsp import VspAirline, VspAirport, VspFrequency, VspNavaid, VspProcedure, VspRunway, VspWaypoint


class VspService:
    def __init__(self, db: Session):
        self.db = db

    def get_airports(self, icao_code: str | None):
        stmt = select(VspAirport)
        if icao_code:
            stmt = stmt.where(VspAirport.icao_code == icao_code)
        return self.db.scalars(stmt).all()

    def get_waypoints(self, keyword: str | None, waypoint_type: str | None, page: int, page_size: int):
        stmt = select(VspWaypoint)
        if keyword:
            stmt = stmt.where(VspWaypoint.name.like(f"%{keyword}%"))
        if waypoint_type:
            stmt = stmt.where(VspWaypoint.type == waypoint_type)
        total = len(self.db.scalars(stmt).all())
        items = self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_procedures(self, airport_id: str | None, procedure_type: str | None, runway: str | None, keyword: str | None):
        stmt = select(VspProcedure)
        if airport_id:
            stmt = stmt.where(VspProcedure.airport_id == airport_id)
        if procedure_type:
            stmt = stmt.where(VspProcedure.procedure_type == procedure_type)
        if runway:
            stmt = stmt.where(VspProcedure.runway == runway)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(or_(VspProcedure.procedure_code.like(like), VspProcedure.procedure_name.like(like)))
        return self.db.scalars(stmt).all()

    def get_airlines(self, keyword: str | None, airline_code: str | None):
        stmt = select(VspAirline)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(or_(VspAirline.airline_code.like(like), VspAirline.airline_name.like(like)))
        if airline_code:
            stmt = stmt.where(VspAirline.airline_code == airline_code)
        return self.db.scalars(stmt).all()

    def get_runways(self, airport_id: str | None, runway_designator: str | None):
        stmt = select(VspRunway)
        if airport_id:
            stmt = stmt.where(VspRunway.airport_id == airport_id)
        if runway_designator:
            stmt = stmt.where(VspRunway.runway_designator == runway_designator)
        return self.db.scalars(stmt).all()

    def get_frequencies(self, airport_id: str | None, service_designator: str | None, keyword: str | None):
        stmt = select(VspFrequency)
        if airport_id:
            stmt = stmt.where(VspFrequency.airport_id == airport_id)
        if service_designator:
            stmt = stmt.where(VspFrequency.service_designator == service_designator)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    VspFrequency.callsign.like(like),
                    VspFrequency.frequency.like(like),
                    VspFrequency.remarks.like(like),
                )
            )
        return self.db.scalars(stmt).all()

    def get_navaids(self, airport_id: str | None, ident: str | None, navaid_type: str | None, keyword: str | None):
        stmt = select(VspNavaid)
        if airport_id:
            stmt = stmt.where(VspNavaid.airport_id == airport_id)
        if ident:
            stmt = stmt.where(VspNavaid.ident == ident)
        if navaid_type:
            stmt = stmt.where(VspNavaid.navaid_type == navaid_type)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    VspNavaid.ident.like(like),
                    VspNavaid.name.like(like),
                    VspNavaid.remarks.like(like),
                )
            )
        return self.db.scalars(stmt).all()

    def get_procedure_geojson(self, procedure_id: str) -> dict:
        procedure = self.db.get(VspProcedure, procedure_id)
        if not procedure:
            raise not_found("procedure not found", code=42001)
        return {"procedure_id": procedure.procedure_id, "procedure_name": procedure.procedure_name, "geojson": procedure.path_geojson}
