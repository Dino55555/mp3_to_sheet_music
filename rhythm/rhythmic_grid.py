from __future__ import annotations
from models.compass import Compass


def build_grid(compass: Compass, divisions_per_beat: int) -> list[float]:
    point_count = compass.formula.beat_groups() * divisions_per_beat + 1
    duration = compass.end_time - compass.begin_time
    step = duration / (point_count - 1)

    return [compass.begin_time + i * step for i in range(point_count)]

def closest_index(instant: float, grid: list[float]) -> int:
    return min(range(len(grid)), key=lambda i: abs(instant - grid[i]))