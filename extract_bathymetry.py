"""Extract pipeline bathymetry data from the KP_Points_1m shapefile: compute cumulative KP, plot profile, and export CSV.

This script uses the generic shapefile_pipeline library for coordinate extraction
and adds GEBCO raster sampling and Spirit-specific output on top.
"""

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import rasterio
from pyproj import Transformer

from shapefile_pipeline import read_shapefile

SHAPEFILE = Path(__file__).parent / "spirit" / "KP_Points" / "KP_Points_1m"
GEBCO_RASTER = Path(__file__).parent / "gebco" / "gebco_2025_n54.0_s53.3_w-3.7_e-3.0_geotiff.tif"
OUTPUT_CSV = Path(__file__).parent / "pipeline_segments.csv"
OUTPUT_PLOT = Path(__file__).parent / "pipeline_profile.png"


def sample_gebco(points: list[dict], raster_path: Path, source_epsg: int = 23030) -> list[float | None]:
    """Sample GEBCO elevation at each pipeline point by transforming from source CRS to WGS84."""
    transformer = Transformer.from_crs(f"EPSG:{source_epsg}", "EPSG:4326", always_xy=True)
    eastings = [p["easting"] for p in points]
    northings = [p["northing"] for p in points]
    lons, lats = transformer.transform(eastings, northings)

    elevations: list[float | None] = []
    with rasterio.open(raster_path) as ds:
        band = ds.read(1)
        nodata = ds.nodata
        for lon, lat in zip(lons, lats):
            try:
                row, col = ds.index(lon, lat)
                if 0 <= row < band.shape[0] and 0 <= col < band.shape[1]:
                    val = float(band[row, col])
                    elevations.append(None if nodata is not None and val == nodata else val)
                else:
                    elevations.append(None)
            except Exception:
                elevations.append(None)
    return elevations


def compute_segments(points: list[dict], gebco_elevations: list[float | None] | None = None) -> list[dict]:
    """Compute segment data between consecutive points (Spirit-specific with GEBCO columns)."""
    segments = []
    cumulative_km = 0.0
    for i in range(1, len(points)):
        p1, p2 = points[i - 1], points[i]
        dx = p2["easting"] - p1["easting"]
        dy = p2["northing"] - p1["northing"]
        length = math.hypot(dx, dy)
        elev_change = p2["depth_m"] - p1["depth_m"]
        seg = {
            "segment": f"{i} -> {i + 1}",
            "start_point": i,
            "end_point": i + 1,
            "start_easting": p1["easting"],
            "start_northing": p1["northing"],
            "end_easting": p2["easting"],
            "end_northing": p2["northing"],
            "start_depth_m": p1["depth_m"],
            "end_depth_m": p2["depth_m"],
            "start_gebco_m": gebco_elevations[i - 1] if gebco_elevations else None,
            "end_gebco_m": gebco_elevations[i] if gebco_elevations else None,
            "elev_change_m": elev_change,
            "gebco_elev_change_m": (
                gebco_elevations[i] - gebco_elevations[i - 1]
                if gebco_elevations and gebco_elevations[i] is not None and gebco_elevations[i - 1] is not None
                else None
            ),
            "length_m": length,
            "length_km": length / 1000,
            "cumulative_km_start": cumulative_km,
            "cumulative_km_end": cumulative_km + length / 1000,
        }
        segments.append(seg)
        cumulative_km += length / 1000
    return segments


def export_csv(segments: list[dict], path: Path) -> None:
    """Write segments to a CSV file."""
    fieldnames = list(segments[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(segments)
    print(f"CSV exported: {path}")


def plot_profile(
    points: list[dict],
    segments: list[dict],
    path: Path,
    gebco_elevations: list[float | None] | None = None,
    title: str = "Pipeline Bathymetry Profile",
) -> None:
    """Generate a high-resolution depth profile plot."""
    kp = [0.0] + [s["cumulative_km_end"] for s in segments]
    depths = [p["depth_m"] for p in points]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(kp, depths, alpha=0.3, color="steelblue", label="Survey (1m)")
    ax.plot(kp, depths, color="steelblue", linewidth=0.5)

    if gebco_elevations:
        ax.plot(kp, gebco_elevations, color="coral", linewidth=1.2, label="GEBCO 2025 (~450m)")

    ax.set_xlabel("KP (km)")
    ax.set_ylabel("Depth (m)")
    ax.set_title(title)
    ax.axhline(0, color="black", linewidth=0.5, linestyle="--", alpha=0.5)

    all_depths = depths + [v for v in (gebco_elevations or []) if v is not None]
    ax.set_ylim(min(all_depths) - 5, max(all_depths) + 5)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"Plot saved: {path}")


def main():
    print(f"Reading shapefile: {SHAPEFILE}.shp\n")
    coord_points, metadata = read_shapefile(SHAPEFILE)
    print(f"Loaded {len(coord_points):,} points")
    print(f"Shape type: {metadata.shape_type_name}, CRS: EPSG:{metadata.crs_epsg} ({metadata.crs_name})\n")

    # Convert CoordinatePoints to legacy dict format for GEBCO pipeline
    points = [{"easting": p.x, "northing": p.y, "depth_m": p.z} for p in coord_points]

    # Determine source EPSG for GEBCO sampling
    source_epsg = metadata.crs_epsg or 23030

    # Sample GEBCO elevations
    gebco_elevations = None
    if GEBCO_RASTER.exists():
        print(f"Sampling GEBCO raster: {GEBCO_RASTER.name}")
        gebco_elevations = sample_gebco(points, GEBCO_RASTER, source_epsg=source_epsg)
        sampled = [v for v in gebco_elevations if v is not None]
        print(f"GEBCO coverage: {len(sampled):,} / {len(points):,} points sampled")
        if sampled:
            print(f"GEBCO range:   {min(sampled):.1f} m  to  {max(sampled):.1f} m")
        print()
    else:
        print(f"GEBCO raster not found at {GEBCO_RASTER}, skipping.\n")

    segments = compute_segments(points, gebco_elevations)

    total_length_m = sum(s["length_m"] for s in segments)
    depths = [p["depth_m"] for p in points]

    print(f"Total length:  {total_length_m:,.1f} m  ({total_length_m / 1000:.2f} km)")
    print(f"Depth range:   {min(depths):.1f} m  to  {max(depths):.1f} m")
    print(f"Point count:   {len(points):,}")
    print(f"Segments:      {len(segments):,}")
    print()

    export_csv(segments, OUTPUT_CSV)

    title = f"Pipeline Bathymetry Profile — {metadata.crs_name or 'Unknown CRS'} (1m resolution)"
    plot_profile(points, segments, OUTPUT_PLOT, gebco_elevations, title=title)


if __name__ == "__main__":
    main()
