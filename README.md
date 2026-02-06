# bathymetry-tool

Extract pipeline bathymetry data from high-resolution KP_Points_1m shapefile (65,000+ points at 1m spacing).

## Quick Start

**Prerequisites:**

Install [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Run it:**

```bash
uv run python extract_bathymetry.py
```

Summary stats print to stdout, a CSV is exported, and a profile plot is saved as PNG.

## Output

| File                    | Description                                               |
| ----------------------- | --------------------------------------------------------- |
| `pipeline_segments.csv` | Segment data: coordinates, depths, lengths, cumulative KP |
| `pipeline_profile.png`  | High-resolution bathymetry depth profile along pipeline   |

### CSV Columns

| Column                                     | Description                                               |
| ------------------------------------------ | --------------------------------------------------------- |
| `segment`                                  | Segment label (e.g. `1 -> 2`)                             |
| `start_point`, `end_point`                 | Point indices                                             |
| `start_easting`, `start_northing`          | Start coordinates (ED50 UTM Zone 30N, metres)             |
| `end_easting`, `end_northing`              | End coordinates (ED50 UTM Zone 30N, metres)               |
| `start_depth_m`, `end_depth_m`             | Seabed depth at each end (metres, negative below surface) |
| `start_gebco_m`, `end_gebco_m`             | GEBCO 2025 elevation at each end (metres, ~450m res)      |
| `elev_change_m`                            | Elevation change across the segment (survey)              |
| `gebco_elev_change_m`                      | Elevation change across the segment (GEBCO)               |
| `length_m`, `length_km`                    | Segment length (Euclidean)                                |
| `cumulative_km_start`, `cumulative_km_end` | Cumulative distance along the pipeline                    |

## Input Data

The tool reads from `spirit/KP_Points/KP_Points_1m`, a POINTZ shapefile with ~65,883 3D points at 1-metre spacing along the Spirit pipeline route. Coordinates are in ED50 UTM Zone 30N; the Z values represent seabed depth (range approx. -31m to +3m).

A GEBCO 2025 GeoTIFF subset (`gebco/gebco_2025_n54.0_s53.3_w-3.7_e-3.0_geotiff.tif`) provides global bathymetry at ~450m resolution in WGS84 (EPSG:4326). Pipeline coordinates are transformed from ED50 UTM 30N to WGS84 to sample this raster. The GEBCO elevation is included as a comparison line on the profile plot (coral) alongside the high-resolution survey data (steelblue).

### Additional Data

The `spirit/` directory also contains supporting shapefiles:

| Dataset                                     | Format    | Content                                                        |
| ------------------------------------------- | --------- | -------------------------------------------------------------- |
| `MNZ_Export/MNZ_Export_Line`                | Shapefile | Pipeline route polyline (ED50 UTM 30N)                         |
| `PipelinesANDCables/PipelineandCables_NSTA` | Shapefile | NSTA pipeline registry with names, diameters, operators        |
| `PipelinesANDCables/KIS_ORCA_SHAPEFILE`     | Shapefile | KIS-ORCA subsea infrastructure                                 |

## How It Works

1. POINTZ shapes are read from the KP_Points_1m shapefile using `pyshp`
2. Euclidean distances between consecutive points are computed (UTM coordinates)
3. Cumulative KP (kilometre post) values are calculated as a running sum
4. Results are printed as summary stats, exported to CSV, and plotted as a depth profile
