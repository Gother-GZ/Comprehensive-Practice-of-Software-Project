from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vsp import VspAirline, VspAirport, VspFrequency, VspNavaid, VspProcedure, VspRunway, VspWaypoint


def seed_demo_vsp_data(db: Session) -> None:
    if db.scalar(select(VspAirport).where(VspAirport.icao_code == "VHHH")):
        return

    airport = VspAirport(
        airport_id="airport_vhhh",
        icao_code="VHHH",
        iata_code="HKG",
        airport_name="Hong Kong International Airport",
        city_name="Hong Kong",
        country_name="China",
        lat=22.3080,
        lng=113.9185,
        elevation_ft=28,
        extra_json='{"source":"seed"}',
        created_at="2026-04-15T00:00:00.000Z",
        updated_at="2026-04-15T00:00:00.000Z",
    )
    waypoints = [
        VspWaypoint(
            waypoint_id="wpt_ataga",
            name="ATAGA",
            type="fix",
            lat=22.2000,
            lng=114.1000,
            description="Demo waypoint",
            extra_json='{"source":"seed"}',
            created_at="2026-04-15T00:00:00.000Z",
            updated_at="2026-04-15T00:00:00.000Z",
        ),
        VspWaypoint(
            waypoint_id="wpt_bekol",
            name="BEKOL",
            type="fix",
            lat=22.4200,
            lng=113.7600,
            description="Demo waypoint",
            extra_json='{"source":"seed"}',
            created_at="2026-04-15T00:00:00.000Z",
            updated_at="2026-04-15T00:00:00.000Z",
        ),
    ]
    procedure = VspProcedure(
        procedure_id="proc_vhhh_star_01",
        airport_id="airport_vhhh",
        procedure_code="VHHH-STAR-01",
        procedure_name="Demo STAR",
        procedure_type="star",
        runway="25L",
        waypoint_sequence_json='["ATAGA","BEKOL"]',
        path_geojson='{"type":"LineString","coordinates":[[114.1,22.2],[113.76,22.42],[113.9185,22.308]]}',
        extra_json='{"source":"seed"}',
        created_at="2026-04-15T00:00:00.000Z",
        updated_at="2026-04-15T00:00:00.000Z",
    )
    airline = VspAirline(
        airline_id="airline_cx",
        airline_code="CX",
        airline_name="Cathay Pacific",
        airline_short_name="Cathay",
        country_name="China Hong Kong",
        extra_json='{"source":"seed"}',
        created_at="2026-04-15T00:00:00.000Z",
        updated_at="2026-04-15T00:00:00.000Z",
    )
    runway = VspRunway(
        runway_id="runway_airport_vhhh_25l",
        airport_id="airport_vhhh",
        runway_designator="25L",
        surface_type="Asphalt",
        runway_length_m=3800,
        runway_width_m=60,
        bearing_deg=250.9,
        threshold_lat=22.305536,
        threshold_lng=113.930356,
        elevation_ft=23,
        remarks="Demo runway",
        extra_json='{"source":"seed"}',
        created_at="2026-04-15T00:00:00.000Z",
        updated_at="2026-04-15T00:00:00.000Z",
    )
    frequency = VspFrequency(
        frequency_id="freq_airport_vhhh_twr_118_2_mhz",
        airport_id="airport_vhhh",
        service_designator="TWR",
        callsign="HONG KONG TOWER",
        frequency="118.2 MHZ",
        hours_of_operation="H24",
        remarks=None,
        extra_json='{"source":"seed"}',
        created_at="2026-04-15T00:00:00.000Z",
        updated_at="2026-04-15T00:00:00.000Z",
    )
    navaid = VspNavaid(
        navaid_id="navaid_airport_vhhh_itfl",
        airport_id="airport_vhhh",
        ident="ITFL",
        name="LOC25L",
        navaid_type="LOC25L",
        frequency="109.5 MHZ",
        lat=22.305536,
        lng=113.930356,
        elevation_ft=None,
        hours_of_operation="H24",
        remarks="Demo navaid",
        extra_json='{"source":"seed"}',
        created_at="2026-04-15T00:00:00.000Z",
        updated_at="2026-04-15T00:00:00.000Z",
    )
    db.add(airport)
    db.add_all(waypoints)
    db.add(procedure)
    db.add(airline)
    db.add(runway)
    db.add(frequency)
    db.add(navaid)
    db.commit()
