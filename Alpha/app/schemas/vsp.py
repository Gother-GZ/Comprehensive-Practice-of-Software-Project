from pydantic import BaseModel, ConfigDict


class AirportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    airport_id: str
    icao_code: str
    iata_code: str | None = None
    airport_name: str
    city_name: str | None = None
    country_name: str | None = None
    lat: float
    lng: float
    elevation_ft: int | None = None
    extra_json: str | None = None


class WaypointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    waypoint_id: str
    name: str
    type: str | None = None
    lat: float
    lng: float
    description: str | None = None
    extra_json: str | None = None


class ProcedureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    procedure_id: str
    airport_id: str
    procedure_code: str
    procedure_name: str
    procedure_type: str
    runway: str | None = None
    waypoint_sequence_json: str | None = None
    path_geojson: str | None = None
    extra_json: str | None = None


class AirlineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    airline_id: str
    airline_code: str
    airline_name: str
    airline_short_name: str | None = None
    country_name: str | None = None
    extra_json: str | None = None


class RunwayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    runway_id: str
    airport_id: str
    runway_designator: str
    surface_type: str | None = None
    runway_length_m: int | None = None
    runway_width_m: int | None = None
    bearing_deg: float | None = None
    threshold_lat: float | None = None
    threshold_lng: float | None = None
    elevation_ft: int | None = None
    remarks: str | None = None
    extra_json: str | None = None


class FrequencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    frequency_id: str
    airport_id: str
    service_designator: str | None = None
    callsign: str | None = None
    frequency: str
    hours_of_operation: str | None = None
    remarks: str | None = None
    extra_json: str | None = None


class NavaidOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    navaid_id: str
    airport_id: str
    ident: str
    name: str | None = None
    navaid_type: str | None = None
    frequency: str | None = None
    lat: float
    lng: float
    elevation_ft: int | None = None
    hours_of_operation: str | None = None
    remarks: str | None = None
    extra_json: str | None = None
