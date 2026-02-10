# bathymetry-tool

A generic pipeline for extracting coordinate data from geospatial files (Shapefiles, KMZ, KML), computing segment distances and cumulative KP, and returning the results as CSV or JSON.

Includes a FastAPI server with a single upload endpoint and a standalone Spirit pipeline script with GEBCO raster comparison.

## Quick Start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Start the server

```bash
uv run python main.py
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Run the Spirit pipeline script

```bash
uv sync --extra spirit
uv run python extract_bathymetry.py
```

This reads the Spirit KP_Points_1m shapefile, samples GEBCO elevations, exports a 17-column CSV, and saves a profile plot.

## Docker

```bash
docker build -t bathymetry-tool .
docker run -p 8000:8000 bathymetry-tool
```

## API

### `POST /process`

Upload geospatial files and receive pipeline segments back.

**Query parameters:**

| Param    | Default | Description              |
| -------- | ------- | ------------------------ |
| `format` | `csv`   | Response format: `csv` or `json` |

**Supported upload formats:**

| Format         | How to upload                                                |
| -------------- | ------------------------------------------------------------ |
| Shapefile      | Multiple files: `.shp` + `.shx` + `.dbf` (+ optional `.prj`) |
| Zipped shapefile | Single `.zip` containing the shapefile components          |
| KMZ            | Single `.kmz` file                                           |
| KML            | Single `.kml` file                                           |

**Examples:**

```bash
# Shapefile (multi-file upload)
curl -X POST http://localhost:8000/process \
  -F "files=@route.shp" \
  -F "files=@route.shx" \
  -F "files=@route.dbf" \
  -F "files=@route.prj"

# Zipped shapefile
curl -X POST http://localhost:8000/process \
  -F "files=@route.zip"

# KMZ
curl -X POST http://localhost:8000/process \
  -F "files=@route.kmz"

# KML, JSON response
curl -X POST "http://localhost:8000/process?format=json" \
  -F "files=@route.kml"
```

**CSV columns (14):**

| Column                                     | Description                             |
| ------------------------------------------ | --------------------------------------- |
| `segment`                                  | Segment label (e.g. `1 -> 2`)          |
| `start_point`, `end_point`                 | Point indices                           |
| `start_x`, `start_y`                       | Start coordinates (source CRS)          |
| `end_x`, `end_y`                           | End coordinates (source CRS)            |
| `start_z`, `end_z`                         | Elevation/depth at each end (if available) |
| `z_change`                                 | Elevation change across the segment     |
| `length_m`, `length_km`                    | Segment length (Euclidean)              |
| `cumulative_km_start`, `cumulative_km_end` | Cumulative distance along the route     |

**JSON response** includes a `metadata` object with auto-detected CRS, shape type, and point count, plus the full `segments` array.

## Supported Shape Types

| Type                  | Source     | Notes                                     |
| --------------------- | ---------- | ----------------------------------------- |
| POINT / POINTZ        | Shapefile  | One point per record                      |
| POLYLINE / POLYLINEZ  | Shapefile  | All vertices across all parts and records |
| LineString            | KML/KMZ    | All vertices from `<coordinates>`         |
| Point                 | KML/KMZ    | One point per `<Placemark>`               |
| POLYGON               | Shapefile  | Rejected with 422 error                   |

CRS is auto-detected from the `.prj` file (shapefiles) or assumed WGS84 (KML/KMZ). For projected CRS, lon/lat values are computed automatically via reprojection to EPSG:4326.

## Project Structure

```
bathymetry/
  src/shapefile_pipeline/
    __init__.py         # Package exports
    models.py           # Pydantic data models
    reader.py           # Shapefile reader (CRS + shape type auto-detection)
    kml_reader.py       # KMZ/KML reader
    segments.py         # Segment computation (distances, cumulative KP)
    server.py           # FastAPI app with upload endpoint
  extract_bathymetry.py # Spirit-specific script (GEBCO sampling, profile plot)
  main.py               # Launches FastAPI server
  pyproject.toml        # Dependencies and build config
  Dockerfile            # Container image
```

## Spirit Pipeline Data

The `sampledata/spirit/` directory contains the project-specific data:

| Dataset                                     | Format    | Content                                                 |
| ------------------------------------------- | --------- | ------------------------------------------------------- |
| `KP_Points/KP_Points_1m`                   | POINTZ    | 65,883 points at 1m spacing along the pipeline route    |
| `MNZ_Export/MNZ_Export_Line`                | POLYLINEZ | Pipeline route polyline (286 vertices)                  |
| `PipelinesANDCables/PipelineandCables_NSTA` | Shapefile | NSTA pipeline registry with names, diameters, operators |
| `PipelinesANDCables/KIS_ORCA_SHAPEFILE`     | Shapefile | KIS-ORCA subsea infrastructure                          |

All shapefiles use ED50 UTM Zone 30N (EPSG:23030). The GEBCO 2025 GeoTIFF in `gebco/` provides global bathymetry at ~450m resolution in WGS84 for comparison.
