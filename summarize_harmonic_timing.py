from __future__ import annotations
import csv
from collections import defaultdict

CSV_PATH = "harmonic_timing_data.csv"


def main() -> None:
    rows_by_position: dict[str, list[dict]] = defaultdict(list)

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_by_position[row["harmonic_position"]].append(row)

    print(f"{'Posição':<16} {'N':>5} {'dist_media(s)':>14} {'dist_mediana(s)':>16} "
          f"{'dist/dur_harm (media)':>22} {'% já dentro de 0.05s':>22}")

    for position in ("2nd (oitava)", "3rd (reduzido)", "3rd", "4th", "5th", "6th"):
        rows = rows_by_position.get(position, [])
        if not rows:
            continue

        distances = [float(r["onset_distance_seconds"]) for r in rows]
        ratios = [float(r["onset_distance_over_harmonic_duration"]) for r in rows if r["onset_distance_over_harmonic_duration"]]

        distances_sorted = sorted(distances)
        n = len(distances_sorted)
        median = distances_sorted[n // 2] if n % 2 == 1 else (distances_sorted[n // 2 - 1] + distances_sorted[n // 2]) / 2

        within_current_tolerance = sum(1 for d in distances if d <= 0.05) / len(distances) * 100

        mean_ratio = sum(ratios) / len(ratios) if ratios else float('nan')

        print(f"{position:<16} {len(rows):>5} {sum(distances)/len(distances):>14.4f} {median:>16.4f} "
              f"{mean_ratio:>22.4f} {within_current_tolerance:>21.1f}%")

    print(f"\nTotal de pares coletados: {sum(len(v) for v in rows_by_position.values())}")
    print(f"Músicas distintas na base: {len(set(r['song'] for rows in rows_by_position.values() for r in rows))}")


if __name__ == "__main__":
    main()