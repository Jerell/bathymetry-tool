"""Extract pipeline bathymetry data from the KP_Points_1m shapefile: compute cumulative KP, plot profile, and export CSV."""

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import shapefile

SHAPEFILE = Path(__file__).parent / "spirit" / "KP_Points" / "KP_Points_1m"
OUTPUT_CSV = Path(__file__).parent / "pipeline_segments.csv"
OUTPUT_PLOT = Path(__file__).parent / "pipeline_profile.png"


def read_shapefile(shp_path: Path) -> list[dict]:
    """Read POINTZ shapefile and return list of dicts with easting, northing, depth."""
    sf = shapefile.Reader(str(shp_path))
    points = []
    for shape in sf.shapes():
        x, y = shape.points[0]
        z = shape.z[0]
        points.append({"easting": x, "northing": y, "depth_m": z})
    return points


def compute_segments(points: list[dict]) -> list[dict]:
    """Compute segment data between consecutive points."""
    segments = []
    cumulative_km = 0.0
    for i in range(1, len(points)):
        p1, p2 = points[i - 1], points[i]
        dx = p2["easting"] - p1["easting"]
        dy = p2["northing"] - p1["northing"]
        length = math.hypot(dx, dy)
        elev_change = p2["depth_m"] - p1["depth_m"]
        segments.append(
            {
                "segment": f"{i} -> {i + 1}",
                "start_point": i,
                "end_point": i + 1,
                "start_easting": p1["easting"],
                "start_northing": p1["northing"],
                "end_easting": p2["easting"],
                "end_northing": p2["northing"],
                "start_depth_m": p1["depth_m"],
                "end_depth_m": p2["depth_m"],
                "elev_change_m": elev_change,
                "length_m": length,
                "length_km": length / 1000,
                "cumulative_km_start": cumulative_km,
                "cumulative_km_end": cumulative_km + length / 1000,
            }
        )
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


def plot_profile(points: list[dict], segments: list[dict], path: Path) -> None:
    """Generate a high-resolution depth profile plot."""
    kp = [0.0] + [s["cumulative_km_end"] for s in segments]
    depths = [p["depth_m"] for p in points]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(kp, depths, alpha=0.3, color="steelblue", label="Seabed profile")
    ax.plot(kp, depths, color="steelblue", linewidth=0.5)

    ax.set_xlabel("KP (km)")
    ax.set_ylabel("Depth (m)")
    ax.set_title("Pipeline Bathymetry Profile — Spirit Pipeline Network (1m resolution)")
    ax.axhline(0, color="black", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.set_ylim(min(depths) - 5, max(depths) + 5)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"Plot saved: {path}")


def main():
    print(f"Reading shapefile: {SHAPEFILE}.shp\n")
    points = read_shapefile(SHAPEFILE)
    print(f"Loaded {len(points):,} points\n")

    segments = compute_segments(points)

    total_length_m = sum(s["length_m"] for s in segments)
    depths = [p["depth_m"] for p in points]

    print(f"Total length:  {total_length_m:,.1f} m  ({total_length_m / 1000:.2f} km)")
    print(f"Depth range:   {min(depths):.1f} m  to  {max(depths):.1f} m")
    print(f"Point count:   {len(points):,}")
    print(f"Segments:      {len(segments):,}")
    print()

    export_csv(segments, OUTPUT_CSV)
    plot_profile(points, segments, OUTPUT_PLOT)


if __name__ == "__main__":
    main()
