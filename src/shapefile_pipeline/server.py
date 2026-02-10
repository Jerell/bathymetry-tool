"""FastAPI server for shapefile processing."""

from __future__ import annotations

import csv
import io
import tempfile
import zipfile
from pathlib import Path

import shapefile
from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from .kml_reader import read_kmz
from .models import PipelineResult, Segment
from .reader import detect_crs, read_shapefile
from .segments import compute_segments

app = FastAPI(title="Shapefile Pipeline", version="0.1.0")

REQUIRED_EXT = ".shp"
COMPANION_EXTS = {".shp", ".shx", ".dbf", ".prj"}


@app.post("/process")
async def process_shapefile(
    files: list[UploadFile],
    format: str = Query("csv", pattern="^(csv|json)$"),
):
    """Process uploaded shapefile(s) or KMZ/KML and return pipeline segments.

    Accepts:
    - A single .kmz or .kml file
    - A single .zip containing shapefile components
    - Multiple files (.shp, .shx, .dbf, and optionally .prj)
    """
    filename = (files[0].filename or "").lower() if len(files) == 1 else ""

    if filename.endswith((".kmz", ".kml")):
        points, metadata = await _handle_kmz(files[0])
    elif filename.endswith(".zip"):
        points, metadata = await _handle_zip(files[0])
    else:
        points, metadata = await _handle_multi_file(files)

    segments = compute_segments(points)
    result = PipelineResult(metadata=metadata, segments=segments)

    if format == "json":
        return result

    return _segments_to_csv_response(segments)


async def _handle_zip(upload: UploadFile):
    """Extract shapefile from a zip archive and process it."""
    content = await upload.read()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Extract .prj WKT if present in the zip
        prj_wkt = None
        with zipfile.ZipFile(tmp_path) as zf:
            for name in zf.namelist():
                if name.lower().endswith(".prj"):
                    prj_wkt = zf.read(name).decode("utf-8", errors="replace")
                    break

        # pyshp can read directly from zip paths
        shp_name = None
        with zipfile.ZipFile(tmp_path) as zf:
            for name in zf.namelist():
                if name.lower().endswith(".shp"):
                    shp_name = name
                    break

        if shp_name is None:
            raise HTTPException(status_code=400, detail="No .shp file found in zip archive")

        # Read using pyshp's zip support: "zip://path.zip/shapefile.shp" -- but
        # that syntax may not be reliable, so extract to temp dir instead
        with zipfile.ZipFile(tmp_path) as zf:
            extract_dir = tempfile.mkdtemp()
            zf.extractall(extract_dir)

        # Find the .shp in extracted dir
        shp_files = list(Path(extract_dir).rglob("*.shp"))
        if not shp_files:
            raise HTTPException(status_code=400, detail="No .shp file found in zip archive")

        shp_path = shp_files[0]
        return read_shapefile(shp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


async def _handle_kmz(upload: UploadFile):
    """Process a KMZ or KML file upload."""
    content = await upload.read()
    return read_kmz(io.BytesIO(content))


async def _handle_multi_file(files: list[UploadFile]):
    """Process shapefile from multiple uploaded component files."""
    file_map: dict[str, bytes] = {}
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext in COMPANION_EXTS:
            file_map[ext] = await f.read()

    if ".shp" not in file_map:
        raise HTTPException(status_code=400, detail="Missing required .shp file")

    shp_file = io.BytesIO(file_map[".shp"])
    shx_file = io.BytesIO(file_map[".shx"]) if ".shx" in file_map else None
    dbf_file = io.BytesIO(file_map[".dbf"]) if ".dbf" in file_map else None

    prj_wkt = None
    if ".prj" in file_map:
        prj_wkt = file_map[".prj"].decode("utf-8", errors="replace")

    return read_shapefile(
        shp_file=shp_file,
        shx_file=shx_file,
        dbf_file=dbf_file,
        prj_wkt=prj_wkt,
    )


def _segments_to_csv_response(segments: list[Segment]) -> StreamingResponse:
    """Convert segments to a streaming CSV response."""
    fieldnames = [
        "segment", "start_point", "end_point",
        "start_x", "start_y", "end_x", "end_y",
        "start_z", "end_z", "z_change",
        "length_m", "length_km",
        "cumulative_km_start", "cumulative_km_end",
    ]

    def generate():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for seg in segments:
            writer.writerow(seg.model_dump())
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pipeline_segments.csv"},
    )
