"""KMZ/KML reader — extracts coordinate points from KML geometry elements.

KMZ is a ZIP archive containing KML. KML coordinates are always WGS84 (EPSG:4326)
in ``longitude,latitude,altitude`` format.
"""

from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET
from typing import BinaryIO

from .models import CoordinatePoint, ShapefileMetadata

KML_NS = "{http://www.opengis.net/kml/2.2}"


def read_kmz(
    file: str | BinaryIO,
) -> tuple[list[CoordinatePoint], ShapefileMetadata]:
    """Read a KMZ (or plain KML) file and return coordinate points with metadata.

    Args:
        file: Path to a .kmz/.kml file, or a file-like object containing KMZ/KML bytes.
    """
    data = _read_bytes(file)

    # KMZ is a ZIP; plain KML is XML text
    if _is_zip(data):
        kml_text = _extract_kml_from_kmz(data)
    else:
        kml_text = data.decode("utf-8", errors="replace")

    root = ET.fromstring(kml_text)
    points, geometry_type = _extract_coordinates(root)

    has_z = any(p.z is not None for p in points)

    # KML is always WGS84 — populate lon/lat from x/y (they're the same in KML)
    for p in points:
        p.lon = p.x
        p.lat = p.y

    metadata = ShapefileMetadata(
        shape_type_name=f"KML_{geometry_type}",
        crs_epsg=4326,
        crs_name="WGS 84",
        is_projected=False,
        num_points=len(points),
        has_z=has_z,
        fields=[],
    )
    return points, metadata


def _read_bytes(file: str | BinaryIO) -> bytes:
    if isinstance(file, (str, bytes)):
        if isinstance(file, str):
            with open(file, "rb") as f:
                return f.read()
        return file
    return file.read()


def _is_zip(data: bytes) -> bool:
    return data[:4] == b"PK\x03\x04"


def _extract_kml_from_kmz(data: bytes) -> str:
    """Extract the first .kml file from a KMZ (ZIP) archive."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Prefer doc.kml, fall back to any .kml
        names = zf.namelist()
        kml_name = None
        for name in names:
            if name.lower() == "doc.kml":
                kml_name = name
                break
        if kml_name is None:
            for name in names:
                if name.lower().endswith(".kml"):
                    kml_name = name
                    break
        if kml_name is None:
            raise ValueError("No .kml file found in KMZ archive")
        return zf.read(kml_name).decode("utf-8", errors="replace")


def _extract_coordinates(root: ET.Element) -> tuple[list[CoordinatePoint], str]:
    """Walk the KML tree and extract coordinates from all geometry elements."""
    points: list[CoordinatePoint] = []
    geometry_type = "UNKNOWN"
    idx = 1

    # Search for all <coordinates> elements under supported geometry types
    # KML geometry: Point, LineString, LinearRing (inside Polygon)
    for elem in root.iter():
        tag = elem.tag.replace(KML_NS, "")

        if tag in ("LineString", "LinearRing"):
            geometry_type = "LINESTRING" if tag == "LineString" else geometry_type
            coords_elem = elem.find(f"{KML_NS}coordinates")
            if coords_elem is not None and coords_elem.text:
                for pt in _parse_coordinates_text(coords_elem.text, idx):
                    points.append(pt)
                    idx += 1

        elif tag == "Point":
            if geometry_type == "UNKNOWN":
                geometry_type = "POINT"
            coords_elem = elem.find(f"{KML_NS}coordinates")
            if coords_elem is not None and coords_elem.text:
                for pt in _parse_coordinates_text(coords_elem.text, idx):
                    points.append(pt)
                    idx += 1

    if geometry_type == "UNKNOWN" and points:
        geometry_type = "MIXED"

    return points, geometry_type


def _parse_coordinates_text(text: str, start_idx: int) -> list[CoordinatePoint]:
    """Parse a KML ``<coordinates>`` text block.

    Format: ``lon,lat[,alt] lon,lat[,alt] ...`` (whitespace-separated tuples).
    """
    points: list[CoordinatePoint] = []
    idx = start_idx
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        lon = float(parts[0])
        lat = float(parts[1])
        alt = float(parts[2]) if len(parts) >= 3 else None
        # In KML, x=lon, y=lat (geographic coordinates)
        points.append(CoordinatePoint(index=idx, x=lon, y=lat, z=alt))
        idx += 1
    return points
