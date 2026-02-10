"""Generic shapefile-to-CSV pipeline library."""

from .kml_reader import read_kmz
from .models import CoordinatePoint, PipelineResult, Segment, ShapefileMetadata
from .reader import detect_crs, read_shapefile
from .segments import compute_segments

__all__ = [
    "CoordinatePoint",
    "PipelineResult",
    "Segment",
    "ShapefileMetadata",
    "compute_segments",
    "detect_crs",
    "read_kmz",
    "read_shapefile",
]
