"""Generic shapefile-to-CSV pipeline library."""

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
    "read_shapefile",
]
