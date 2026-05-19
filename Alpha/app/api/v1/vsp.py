from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import success_response
from app.db.session import get_db
from app.schemas.vsp import AirlineOut, AirportOut, FrequencyOut, NavaidOut, ProcedureOut, RunwayOut, WaypointOut
from app.services.vsp_service import VspService

router = APIRouter()


@router.get("/airports")
def airports(icao_code: str | None = None, db: Session = Depends(get_db)):
    items = VspService(db).get_airports(icao_code)
    return success_response(data=[AirportOut.model_validate(item).model_dump() for item in items])


@router.get("/waypoints")
def waypoints(keyword: str | None = None, type: str | None = None, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    data = VspService(db).get_waypoints(keyword=keyword, waypoint_type=type, page=page, page_size=page_size)
    data["items"] = [WaypointOut.model_validate(item).model_dump() for item in data["items"]]
    return success_response(data=data)


@router.get("/procedures")
def procedures(
    airport_id: str | None = None,
    procedure_type: str | None = None,
    runway: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    items = VspService(db).get_procedures(airport_id=airport_id, procedure_type=procedure_type, runway=runway, keyword=keyword)
    return success_response(data=[ProcedureOut.model_validate(item).model_dump() for item in items])


@router.get("/airlines")
def airlines(keyword: str | None = None, airline_code: str | None = None, db: Session = Depends(get_db)):
    items = VspService(db).get_airlines(keyword=keyword, airline_code=airline_code)
    return success_response(data=[AirlineOut.model_validate(item).model_dump() for item in items])


@router.get("/runways")
def runways(airport_id: str | None = None, runway_designator: str | None = None, db: Session = Depends(get_db)):
    items = VspService(db).get_runways(airport_id=airport_id, runway_designator=runway_designator)
    return success_response(data=[RunwayOut.model_validate(item).model_dump() for item in items])


@router.get("/frequencies")
def frequencies(
    airport_id: str | None = None,
    service_designator: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    items = VspService(db).get_frequencies(airport_id=airport_id, service_designator=service_designator, keyword=keyword)
    return success_response(data=[FrequencyOut.model_validate(item).model_dump() for item in items])


@router.get("/navaids")
def navaids(
    airport_id: str | None = None,
    ident: str | None = None,
    navaid_type: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    items = VspService(db).get_navaids(airport_id=airport_id, ident=ident, navaid_type=navaid_type, keyword=keyword)
    return success_response(data=[NavaidOut.model_validate(item).model_dump() for item in items])


@router.get("/geojson/procedures/{procedure_id}")
def procedure_geojson(procedure_id: str, db: Session = Depends(get_db)):
    return success_response(data=VspService(db).get_procedure_geojson(procedure_id))
