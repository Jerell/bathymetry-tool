"""Pydantic data models for the shapefile pipeline."""

from pydantic import BaseModel


class CoordinatePoint(BaseModel):
    """A single coordinate point extracted from a shapefile."""

    index: int
    x: float
    y: float
    z: float | None = None
    lon: float | None = None
    lat: float | None = None


class ShapefileMetadata(BaseModel):
    """Metadata about a parsed shapefile."""

    shape_type_name: str
    crs_epsg: int | None = None
    crs_name: str | None = None
    is_projected: bool | None = None
    num_points: int
    has_z: bool
    fields: list[str]


class Segment(BaseModel):
    """A segment between two consecutive coordinate points."""

    segment: str
    start_point: int
    end_point: int
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    start_z: float | None = None
    end_z: float | None = None
    z_change: float | None = None
    length_m: float
    length_km: float
    cumulative_km_start: float
    cumulative_km_end: float


class PipelineResult(BaseModel):
    """Complete result of processing a shapefile."""

    metadata: ShapefileMetadata
    segments: list[Segment]
