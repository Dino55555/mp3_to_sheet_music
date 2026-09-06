from __future__ import annotations
import sys
import csv
import os
from signal_extractor.note_extraction import NoteExtractor

HARMONIC_POSITIONS: dict[int, str] = {
    7: "3rd (reduzido)",
    12: "2nd (oitava)",
    19: "3rd",
    24: "4th",
    28: "5th",
    31: "6th",
}

#janela de busca generosa - bem mais ampla que a tolerancia atual (0.05s),
#para capturar a distribuicao real de distancias, nao so o que ja
#sobrevive ao filtro de hoje
SEARCH_WINDOW_SECONDS: float = 0.3

CSV_PATH = "harmonic_timing_data.csv"
CSV_COLUMNS = [
    "song", "harmonic_position", "interval_semitones",
    "fundamental_pitch", "fundamental_onset", "fundamental_duration", "fundamental_magnitude",
    "harmonic_pitch", "harmonic_onset", "harmonic_duration", "harmonic_magnitude",
    "onset_distance_seconds",
    "onset_distance_over_harmonic_duration",
    "onset_distance_over_fundamental_duration",
    "magnitude_ratio",
    "overlaps_original_definition",
]


def find_candidate_pairs(notes: list) -> list[dict]:
    rows = []
    for i, a in enumerate(notes):
        for b in notes[i + 1:]:
            lower, higher = (a, b) if a.pitch < b.pitch else (b, a)
            interval = higher.pitch - lower.pitch
            if interval not in HARMONIC_POSITIONS:
                continue
            if higher.magnitude >= lower.magnitude:
                continue  # harmonico deveria ser mais fraco que a fundamental
            onset_distance = abs(higher.onset - lower.onset)
            if onset_distance > SEARCH_WINDOW_SECONDS:
                continue

            overlaps = lower.onset < higher.offset and higher.onset < lower.offset

            rows.append({
                "harmonic_position": HARMONIC_POSITIONS[interval],
                "interval_semitones": interval,
                "fundamental_pitch": lower.pitch,
                "fundamental_onset": round(lower.onset, 4),
                "fundamental_duration": round(lower.duration(), 4),
                "fundamental_magnitude": round(lower.magnitude, 4),
                "harmonic_pitch": higher.pitch,
                "harmonic_onset": round(higher.onset, 4),
                "harmonic_duration": round(higher.duration(), 4),
                "harmonic_magnitude": round(higher.magnitude, 4),
                "onset_distance_seconds": round(onset_distance, 4),
                "onset_distance_over_harmonic_duration": round(onset_distance / higher.duration(), 4) if higher.duration() > 0 else None,
                "onset_distance_over_fundamental_duration": round(onset_distance / lower.duration(), 4) if lower.duration() > 0 else None,
                "magnitude_ratio": round(higher.magnitude / lower.magnitude, 4) if lower.magnitude > 0 else None,
                "overlaps_original_definition": overlaps,
            })
    return rows


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python survey_harmonic_timing.py caminho_do_vocals.wav [nome_da_musica]", file=sys.stderr)
        sys.exit(1)

    audio_path = sys.argv[1]
    song_name = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(audio_path)

    notes = NoteExtractor().extract(audio_path)
    print(f"Notas extraídas de '{song_name}': {len(notes)}")

    pairs = find_candidate_pairs(notes)
    print(f"Pares candidatos a fundamental/harmônico encontrados: {len(pairs)}")

    file_exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for row in pairs:
            row_with_song = {"song": song_name, **row}
            writer.writerow(row_with_song)

    print(f"Dados acrescentados a '{CSV_PATH}' (total acumulado ao longo de todas as músicas rodadas até agora)")


if __name__ == "__main__":
    main()