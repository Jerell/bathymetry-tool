"""Tests for shapefile reader (POINTZ, POLYLINEZ) and KMZ/KML reader."""

import io
import zipfile

import pytest

from shapefile_pipeline import read_shapefile, read_kmz, compute_segments


class TestPointZShapefile:
    def test_reads_all_points(self, spirit_pointz_path):
        points, meta = read_shapefile(spirit_pointz_path)
        assert meta.shape_type_name == "POINTZ"
        assert meta.num_points == 65_883
        assert len(points) == 65_883

    def test_detects_crs(self, spirit_pointz_path):
        _, meta = read_shapefile(spirit_pointz_path)
        assert meta.crs_epsg == 23030
        assert meta.is_projected is True
        assert "ED" in meta.crs_name and "UTM" in meta.crs_name

    def test_has_z_values(self, spirit_pointz_path):
        points, meta = read_shapefile(spirit_pointz_path)
        assert meta.has_z is True
        assert all(p.z is not None for p in points)

    def test_populates_lonlat(self, spirit_pointz_path):
        points, _ = read_shapefile(spirit_pointz_path)
        p = points[0]
        assert p.lon is not None and p.lat is not None
        # Should be roughly in the North Sea area
        assert -4 < p.lon < -2
        assert 53 < p.lat < 55

    def test_segments(self, spirit_pointz_path):
        points, _ = read_shapefile(spirit_pointz_path)
        segments = compute_segments(points)
        assert len(segments) == len(points) - 1
        total_km = segments[-1].cumulative_km_end
        assert 65 < total_km < 67  # ~65.88 km


class TestPolylineShapefile:
    def test_reads_vertices(self, spirit_polyline_path):
        points, meta = read_shapefile(spirit_polyline_path)
        assert "POLYLINE" in meta.shape_type_name.upper()
        assert meta.num_points == 286
        assert len(points) == 286

    def test_segments(self, spirit_polyline_path):
        points, _ = read_shapefile(spirit_polyline_path)
        segments = compute_segments(points)
        assert len(segments) == 285


class TestKmzReader:
    def test_reads_kmz_file(self, calcasieu_kmz_path):
        points, meta = read_kmz(str(calcasieu_kmz_path))
        assert meta.crs_epsg == 4326
        assert meta.is_projected is False
        assert meta.num_points > 0
        assert len(points) == meta.num_points

    def test_kmz_has_lonlat(self, calcasieu_kmz_path):
        points, _ = read_kmz(str(calcasieu_kmz_path))
        for p in points:
            assert p.lon == p.x
            assert p.lat == p.y

    def test_kmz_linestring_geometry(self, calcasieu_kmz_path):
        _, meta = read_kmz(str(calcasieu_kmz_path))
        assert "LINESTRING" in meta.shape_type_name

    def test_kmz_segments(self, calcasieu_kmz_path):
        points, _ = read_kmz(str(calcasieu_kmz_path))
        segments = compute_segments(points)
        assert len(segments) == len(points) - 1
        assert segments[-1].cumulative_km_end > 0


class TestKmlInline:
    KML_LINESTRING = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>-3.5,53.5,-10 -3.4,53.6,-20 -3.3,53.7,-30</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""

    KML_POINTS = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark><Point><coordinates>1.0,2.0,100</coordinates></Point></Placemark>
    <Placemark><Point><coordinates>3.0,4.0,200</coordinates></Point></Placemark>
  </Document>
</kml>"""

    KML_NO_Z = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <LineString>
        <coordinates>0,0 1,1 2,2</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""

    def test_linestring(self):
        points, meta = read_kmz(io.BytesIO(self.KML_LINESTRING.encode()))
        assert meta.shape_type_name == "KML_LINESTRING"
        assert len(points) == 3
        assert points[0].z == -10
        assert points[2].z == -30

    def test_points(self):
        points, meta = read_kmz(io.BytesIO(self.KML_POINTS.encode()))
        assert meta.shape_type_name == "KML_POINT"
        assert len(points) == 2
        assert points[0].x == 1.0
        assert points[1].z == 200

    def test_no_altitude(self):
        points, meta = read_kmz(io.BytesIO(self.KML_NO_Z.encode()))
        assert meta.has_z is False
        assert all(p.z is None for p in points)

    def test_kmz_from_bytes(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("doc.kml", self.KML_LINESTRING)
        buf.seek(0)
        points, meta = read_kmz(buf)
        assert len(points) == 3
        assert "KML" in meta.shape_type_name

    def test_segments_z_change(self):
        points, _ = read_kmz(io.BytesIO(self.KML_LINESTRING.encode()))
        segments = compute_segments(points)
        assert len(segments) == 2
        assert segments[0].z_change == -10  # -20 - (-10)
        assert segments[0].cumulative_km_start == 0.0
        assert segments[1].cumulative_km_end > segments[1].cumulative_km_start
