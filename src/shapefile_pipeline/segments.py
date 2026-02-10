"""Segment computation between consecutive coordinate points."""

import math

from .models import CoordinatePoint, Segment


def compute_segments(points: list[CoordinatePoint]) -> list[Segment]:
    """Compute segments between consecutive points with distances and cumulative KP."""
    segments: list[Segment] = []
    cumulative_km = 0.0

    for i in range(1, len(points)):
        p1, p2 = points[i - 1], points[i]
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        length_m = math.hypot(dx, dy)
        length_km = length_m / 1000

        z_change = None
        if p1.z is not None and p2.z is not None:
            z_change = p2.z - p1.z

        seg = Segment(
            segment=f"{p1.index} -> {p2.index}",
            start_point=p1.index,
            end_point=p2.index,
            start_x=p1.x,
            start_y=p1.y,
            end_x=p2.x,
            end_y=p2.y,
            start_z=p1.z,
            end_z=p2.z,
            z_change=z_change,
            length_m=length_m,
            length_km=length_km,
            cumulative_km_start=cumulative_km,
            cumulative_km_end=cumulative_km + length_km,
        )
        segments.append(seg)
        cumulative_km += length_km

    return segments
