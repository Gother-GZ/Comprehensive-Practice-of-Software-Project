from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class VspAirport(Base):
    __tablename__ = "vsp_airports"

    airport_id: Mapped[str] = mapped_column(String, primary_key=True)
    icao_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    iata_code: Mapped[str | None] = mapped_column(String, nullable=True)
    airport_name: Mapped[str] = mapped_column(String, nullable=False)
    city_name: Mapped[str | None] = mapped_column(String, nullable=True)
    country_name: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class VspWaypoint(Base):
    __tablename__ = "vsp_waypoints"

    waypoint_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class VspProcedure(Base):
    __tablename__ = "vsp_procedures"

    procedure_id: Mapped[str] = mapped_column(String, primary_key=True)
    airport_id: Mapped[str] = mapped_column(ForeignKey("vsp_airports.airport_id"), nullable=False)
    procedure_code: Mapped[str] = mapped_column(String, nullable=False)
    procedure_name: Mapped[str] = mapped_column(String, nullable=False)
    procedure_type: Mapped[str] = mapped_column(String, nullable=False)
    runway: Mapped[str | None] = mapped_column(String, nullable=True)
    waypoint_sequence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    path_geojson: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class VspAirline(Base):
    __tablename__ = "vsp_airlines"

    airline_id: Mapped[str] = mapped_column(String, primary_key=True)
    airline_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    airline_name: Mapped[str] = mapped_column(String, nullable=False)
    airline_short_name: Mapped[str | None] = mapped_column(String, nullable=True)
    country_name: Mapped[str | None] = mapped_column(String, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class VspRunway(Base):
    __tablename__ = "vsp_runways"

    runway_id: Mapped[str] = mapped_column(String, primary_key=True)
    airport_id: Mapped[str] = mapped_column(ForeignKey("vsp_airports.airport_id"), nullable=False)
    runway_designator: Mapped[str] = mapped_column(String, nullable=False)
    surface_type: Mapped[str | None] = mapped_column(String, nullable=True)
    runway_length_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runway_width_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bearing_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class VspFrequency(Base):
    __tablename__ = "vsp_frequencies"

    frequency_id: Mapped[str] = mapped_column(String, primary_key=True)
    airport_id: Mapped[str] = mapped_column(ForeignKey("vsp_airports.airport_id"), nullable=False)
    service_designator: Mapped[str | None] = mapped_column(String, nullable=True)
    callsign: Mapped[str | None] = mapped_column(String, nullable=True)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    hours_of_operation: Mapped[str | None] = mapped_column(String, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class VspNavaid(Base):
    __tablename__ = "vsp_navaids"

    navaid_id: Mapped[str] = mapped_column(String, primary_key=True)
    airport_id: Mapped[str] = mapped_column(ForeignKey("vsp_airports.airport_id"), nullable=False)
    ident: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    navaid_type: Mapped[str | None] = mapped_column(String, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hours_of_operation: Mapped[str | None] = mapped_column(String, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
