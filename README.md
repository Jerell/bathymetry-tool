# bathymetry-tool

Extract pipe segment lengths and elevations from pipeline bathymetry survey data.

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

That's it. A summary table prints to stdout, a CSV is exported, and a profile plot is saved as PNG.

## Output

The tool reads the Spirit pipeline bathymetry waypoints and produces:

| File                    | Description                                               |
| ----------------------- | --------------------------------------------------------- |
| `pipeline_segments.csv` | Segment data: coordinates, depths, lengths, cumulative KP |
| `pipeline_profile.png`  | Bathymetry elevation profile along the pipeline           |

### CSV Columns

| Column                                     | Description                                               |
| ------------------------------------------ | --------------------------------------------------------- |
| `segment`                                  | Segment label (e.g. `1 -> 2`)                             |
| `start_point`, `end_point`                 | Waypoint indices                                          |
| `start_lon`, `start_lat`                   | Start coordinates (WGS-84 decimal degrees)                |
| `end_lon`, `end_lat`                       | End coordinates (WGS-84 decimal degrees)                  |
| `start_depth_m`, `end_depth_m`             | Seabed depth at each end (metres, negative below surface) |
| `elev_change_m`                            | Elevation change across the segment                       |
| `length_m`, `length_km`                    | Horizontal segment length (Haversine)                     |
| `cumulative_km_start`, `cumulative_km_end` | Cumulative distance along the pipeline                    |

## Input Data

The tool reads from `spirit/MNZ_exp_ppl_bathy_estimate_DMS_WGS84.txt`, a tab-separated file of waypoints in DMS (degrees/minutes/seconds) format with WGS-84 coordinates and depth estimates:

```
3°7'56"W 53°26'7"N	0
3°9'34"W 53°27'9"N	-5
3°14'16"W 53°27'27"N	-10
...
```

### Additional Data

The `spirit/` directory also contains supporting shapefiles:

| Dataset                                     | Format    | Content                                                        |
| ------------------------------------------- | --------- | -------------------------------------------------------------- |
| `KP_Points/KP_Points_1m`                    | Shapefile | 1-metre spaced reference points along the route (ED50 UTM 30N) |
| `MNZ_Export/MNZ_Export_Line`                | Shapefile | Pipeline route polyline (ED50 UTM 30N)                         |
| `PipelinesANDCables/PipelineandCables_NSTA` | Shapefile | NSTA pipeline registry with names, diameters, operators        |
| `PipelinesANDCables/KIS_ORCA_SHAPEFILE`     | Shapefile | KIS-ORCA subsea infrastructure                                 |

## How It Works

1. DMS coordinates and depths are parsed from the bathymetry text file
2. Haversine distances are computed between consecutive waypoints
3. Segment data (lengths, elevations, cumulative KP) is assembled
4. Results are printed as a table, exported to CSV, and plotted as a depth profile
