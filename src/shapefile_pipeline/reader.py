"""Generic shapefile reader with CRS auto-detection and shape type handling."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO

import shapefile
from pyproj import CRS, Transformer

from .models import CoordinatePoint, ShapefileMetadata


def detect_crs(prj_source: str | Path | None) -> tuple[int | None, str | None, bool | None]:
    """Parse CRS from a .prj WKT string or file path.

    Returns (epsg_code, crs_name, is_projected) or (None, None, None) on failure.
    """
    if prj_source is None:
        return None, None, None

    wkt = prj_source if isinstance(prj_source, str) else ""
    if isinstance(prj_source, Path):
        if not prj_source.exists():
            return None, None, None
        wkt = prj_source.read_text()

    if not wkt.strip():
        return None, None, None

    try:
        crs = CRS.from_wkt(wkt)
    except Exception:
        return None, None, None

    epsg = crs.to_epsg()
    return epsg, crs.name, crs.is_projected


def read_shapefile(
    shp_path: str | Path | None = None,
    *,
    shp_file: BinaryIO | None = None,
    shx_file: BinaryIO | None = None,
    dbf_file: BinaryIO | None = None,
    prj_wkt: str | None = None,
) -> tuple[list[CoordinatePoint], ShapefileMetadata]:
    """Read a shapefile and return coordinate points with metadata.

    Supports two modes:
    - File path: pass ``shp_path`` (the .prj is auto-discovered)
    - File objects: pass ``shp_file``, ``shx_file``, ``dbf_file``, and optionally ``prj_wkt``
    """
    if shp_path is not None:
        shp_path = Path(shp_path)
        sf = shapefile.Reader(str(shp_path))
        prj_path = shp_path.with_suffix(".prj")
        if not prj_path.exists():
            # shp_path might already lack an extension (pyshp convention)
            prj_path = Path(str(shp_path) + ".prj") if not prj_path.exists() else prj_path
        epsg, crs_name, is_projected = detect_crs(prj_path if prj_path.exists() else None)
    elif shp_file is not None:
        sf = shapefile.Reader(shp=shp_file, shx=shx_file, dbf=dbf_file)
        epsg, crs_name, is_projected = detect_crs(prj_wkt)
    else:
        raise ValueError("Provide either shp_path or shp_file")

    shape_type_name = sf.shapeTypeName
    upper = shape_type_name.upper()
    fields = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag

    if "POLYGON" in upper:
        raise ValueError(f"Unsupported shape type: {shape_type_name}. POLYGON shapes are not supported.")

    has_z = "Z" in upper
    points = _extract_points(sf, upper, has_z)

    # Transform to WGS84 lon/lat if CRS is projected
    if is_projected and epsg is not None:
        _populate_lonlat(points, epsg)

    metadata = ShapefileMetadata(
        shape_type_name=shape_type_name,
        crs_epsg=epsg,
        crs_name=crs_name,
        is_projected=is_projected,
        num_points=len(points),
        has_z=has_z,
        fields=fields,
    )
    return points, metadata


def _extract_points(sf: shapefile.Reader, upper_type: str, has_z: bool) -> list[CoordinatePoint]:
    """Extract CoordinatePoints from shapes based on shape type."""
    points: list[CoordinatePoint] = []
    idx = 1

    if "POINT" in upper_type and "POLY" not in upper_type:
        # POINT / POINTZ / POINTM
        for shape in sf.shapes():
            x, y = shape.points[0]
            z = shape.z[0] if has_z else None
            points.append(CoordinatePoint(index=idx, x=x, y=y, z=z))
            idx += 1
    elif "POLYLINE" in upper_type or upper_type in ("ARC", "ARCZ", "ARCM"):
        # POLYLINE / POLYLINEZ — extract all vertices across all records and parts
        for shape in sf.shapes():
            part_starts = list(shape.parts)
            for part_idx in range(len(part_starts)):
                start = part_starts[part_idx]
                end = part_starts[part_idx + 1] if part_idx + 1 < len(part_starts) else len(shape.points)
                for v in range(start, end):
                    x, y = shape.points[v]
                    z = shape.z[v] if has_z and hasattr(shape, "z") and len(shape.z) > v else None
                    points.append(CoordinatePoint(index=idx, x=x, y=y, z=z))
                    idx += 1
    else:
        raise ValueError(f"Unsupported shape type: {upper_type}")

    return points


def _populate_lonlat(points: list[CoordinatePoint], source_epsg: int) -> None:
    """Transform projected x/y to WGS84 lon/lat in-place."""
    transformer = Transformer.from_crs(f"EPSG:{source_epsg}", "EPSG:4326", always_xy=True)
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    lons, lats = transformer.transform(xs, ys)
    for p, lon, lat in zip(points, lons, lats):
        p.lon = lon
        p.lat = lat
