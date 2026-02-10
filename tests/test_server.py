"""Tests for the FastAPI server endpoint."""

import io
import zipfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from shapefile_pipeline.server import app

SAMPLEDATA = Path(__file__).parent.parent / "sampledata"


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _upload(path: Path) -> tuple[str, bytes, str]:
    """Return a (filename, content, content_type) tuple for upload."""
    return (path.name, path.read_bytes(), "application/octet-stream")


@pytest.mark.asyncio
class TestShapefileUpload:
    async def test_multi_file_csv(self, client):
        base = SAMPLEDATA / "spirit" / "KP_Points" / "KP_Points_1m"
        files = [
            ("files", _upload(base.with_suffix(".shp"))),
            ("files", _upload(base.with_suffix(".shx"))),
            ("files", _upload(base.with_suffix(".dbf"))),
            ("files", _upload(base.with_suffix(".prj"))),
        ]
        resp = await client.post("/process", files=files)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        lines = resp.text.strip().split("\n")
        assert lines[0].startswith("segment,")
        assert len(lines) == 65_883  # header + 65882 segments

    async def test_multi_file_json(self, client):
        base = SAMPLEDATA / "spirit" / "MNZ_Export" / "MNZ_Export_Line"
        files = [
            ("files", _upload(base.with_suffix(".shp"))),
            ("files", _upload(base.with_suffix(".shx"))),
            ("files", _upload(base.with_suffix(".dbf"))),
            ("files", _upload(base.with_suffix(".prj"))),
        ]
        resp = await client.post("/process?format=json", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["shape_type_name"] == "POLYLINEZ"
        assert data["metadata"]["crs_epsg"] == 23030
        assert len(data["segments"]) == 285

    async def test_zip_upload(self, client):
        base = SAMPLEDATA / "spirit" / "MNZ_Export" / "MNZ_Export_Line"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                p = base.with_suffix(ext)
                zf.writestr(p.name, p.read_bytes())
        buf.seek(0)
        files = [("files", ("archive.zip", buf.getvalue(), "application/zip"))]
        resp = await client.post("/process?format=json", files=files)
        assert resp.status_code == 200
        assert len(resp.json()["segments"]) == 285

    async def test_missing_shp_returns_400(self, client):
        base = SAMPLEDATA / "spirit" / "KP_Points" / "KP_Points_1m"
        files = [("files", _upload(base.with_suffix(".dbf")))]
        resp = await client.post("/process", files=files)
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestKmzUpload:
    async def test_kmz_upload_json(self, client):
        kmz = SAMPLEDATA / "calcasieu.kmz"
        files = [("files", _upload(kmz))]
        resp = await client.post("/process?format=json", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["crs_epsg"] == 4326
        assert "KML" in data["metadata"]["shape_type_name"]
        assert len(data["segments"]) > 0

    async def test_kmz_upload_csv(self, client):
        kmz = SAMPLEDATA / "calcasieu.kmz"
        files = [("files", _upload(kmz))]
        resp = await client.post("/process", files=files)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().split("\n")
        assert len(lines) > 1  # header + at least 1 segment

    async def test_kml_upload(self, client):
        kml = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>0,0,0 1,1,10 2,2,20</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
        files = [("files", ("route.kml", kml.encode(), "application/vnd.google-earth.kml+xml"))]
        resp = await client.post("/process?format=json", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["segments"]) == 2
