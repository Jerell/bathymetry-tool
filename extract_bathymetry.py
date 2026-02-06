"""Extract pipeline bathymetry data: parse waypoints, compute segment lengths, plot, and export CSV."""

import csv
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt

DATA_FILE = Path(__file__).parent / "spirit" / "MNZ_exp_ppl_bathy_estimate_DMS_WGS84.txt"
OUTPUT_CSV = Path(__file__).parent / "pipeline_segments.csv"
OUTPUT_PLOT = Path(__file__).parent / "pipeline_profile.png"


def parse_dms(s: str) -> float | None:
    """Parse a DMS string like 3°7'56\"W or 53°30'N to decimal degrees."""
    s = s.strip()
    m = re.match(r"(\d+)\u00b0(\d+)'(\d+)\"([NSEW])", s)
    if m:
        deg = int(m.group(1)) + int(m.group(2)) / 60 + int(m.group(3)) / 3600
        if m.group(4) in ("S", "W"):
            deg = -deg
        return deg
    m = re.match(r"(\d+)\u00b0(\d+)'([NSEW])", s)
    if m:
        deg = int(m.group(1)) + int(m.group(2)) / 60
        if m.group(3) in ("S", "W"):
            deg = -deg
        return deg
    return None


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_waypoints(path: Path) -> list[dict]:
    """Read the bathymetry text file and return a list of waypoint dicts."""
    text = path.read_text(encoding="utf-8")
    points = []
    for line in text.strip().splitlines():
        line = line.strip().replace("\r", "")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        coord_str = parts[0].strip()
        depth = float(parts[1].strip())
        m = re.match(r"(.+?[EW])\s+(.+?[NS])", coord_str)
        if not m:
            continue
        lon = parse_dms(m.group(1))
        lat = parse_dms(m.group(2))
        if lon is None or lat is None:
            continue
        points.append({"lon": lon, "lat": lat, "depth_m": depth})
    return points


def compute_segments(points: list[dict]) -> list[dict]:
    """Compute segment lengths, cumulative KP, and elevation changes."""
    segments = []
    cumulative_km = 0.0
    for i in range(1, len(points)):
        p1, p2 = points[i - 1], points[i]
        length = haversine(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
        elev_change = p2["depth_m"] - p1["depth_m"]
        segments.append(
            {
                "segment": f"{i} -> {i + 1}",
                "start_point": i,
                "end_point": i + 1,
                "start_lon": p1["lon"],
                "start_lat": p1["lat"],
                "end_lon": p2["lon"],
                "end_lat": p2["lat"],
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
    """Generate an elevation profile plot along the pipeline."""
    kp = [0.0]
    for seg in segments:
        kp.append(seg["cumulative_km_end"])
    depths = [p["depth_m"] for p in points]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(kp, depths, alpha=0.3, color="steelblue", label="Seabed profile")
    ax.plot(kp, depths, "o-", color="steelblue", markersize=6, linewidth=2)

    for i, (x, d) in enumerate(zip(kp, depths)):
        ax.annotate(
            f"{d:.0f} m",
            (x, d),
            textcoords="offset points",
            xytext=(0, -16),
            ha="center",
            fontsize=7,
            color="navy",
        )

    ax.set_xlabel("Distance along pipeline (km)")
    ax.set_ylabel("Depth (m)")
    ax.set_title("Pipeline Bathymetry Profile — Spirit Pipeline Network")
    ax.axhline(0, color="black", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.set_ylim(min(depths) - 5, 5)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"Plot saved: {path}")


def main():
    print(f"Reading: {DATA_FILE}\n")
    points = parse_waypoints(DATA_FILE)
    print(f"Parsed {len(points)} waypoints\n")

    segments = compute_segments(points)

    # Print summary table
    header = f"{'Segment':>10} | {'Length (m)':>11} | {'Length (km)':>11} | {'Start Depth':>12} | {'End Depth':>10} | {'dElev (m)':>10} | {'Cum. KP':>8}"
    print(header)
    print("-" * len(header))
    for s in segments:
        print(
            f"{s['segment']:>10} | {s['length_m']:11.1f} | {s['length_km']:11.3f} | {s['start_depth_m']:12.1f} | {s['end_depth_m']:10.1f} | {s['elev_change_m']:10.1f} | {s['cumulative_km_end']:8.2f}"
        )
    total = sum(s["length_m"] for s in segments)
    print("-" * len(header))
    print(f"{'TOTAL':>10} | {total:11.1f} | {total / 1000:11.3f} |")
    print()

    export_csv(segments, OUTPUT_CSV)
    plot_profile(points, segments, OUTPUT_PLOT)


if __name__ == "__main__":
    main()
