from __future__ import annotations
from models.note import Note
from models.compass import Compass
from Compass.piece import Piece
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)

SMALL_THRESHOLD_FRACTION: float = 0.15
AMBIGUITY_TOLERANCE_FRACTION: float = 0.2
MODERATE_DEVIATION_CONFIDENCE: float = 0.7
AMBIGUOUS_TIME_CONFIDENCE: float = 0.3


class Quantizer:
    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        for voice in piece.voices:
            for note in voice.notes:
                self._quantize_note(note, piece, config.divisions_per_beat, signaler)

        return piece

    def _build_grid(self, compass: Compass, divisions_per_beat: int) -> list[float]:
        point_count = compass.formula.numerator * divisions_per_beat + 1
        duration = compass.end_time - compass.begin_time
        step = duration / (point_count - 1)
        return [compass.begin_time + i * step for i in range(point_count)]

    def _two_closest(self, instant: float, grid: list[float]) -> tuple[int, int]:
        ordered_indices = sorted(
            range(len(grid)),
            key=lambda i: abs(instant - grid[i])
        )

        return ordered_indices[0], ordered_indices[1]

    def _metric_level(self, index_in_grid: int, divisions_per_beat: int) -> int:
        local_index = index_in_grid % divisions_per_beat
        if local_index == 0:
            return divisions_per_beat.bit_length()

        level = 0
        while local_index % 2 == 0:
            local_index //= 2
            level += 1

        return level

    def _quantize_instant(self, instant: float, piece: Piece, divisions_per_beat: int) -> tuple[float, float, bool]:
        compass = piece.compass_at_instant(instant)
        grid = self._build_grid(compass, divisions_per_beat)
        grid_spacing = (compass.end_time - compass.begin_time) / (compass.formula.numerator * divisions_per_beat)

        index_a, index_b = self._two_closest(instant, grid)
        distance_a = abs(instant - grid[index_a])
        distance_b = abs(instant - grid[index_b])

        if distance_a < SMALL_THRESHOLD_FRACTION * grid_spacing:
            return grid[index_a], 1.0, False

        if abs(distance_a - distance_b) < AMBIGUITY_TOLERANCE_FRACTION * grid_spacing:
            level_a = self._metric_level(index_a, divisions_per_beat)
            level_b = self._metric_level(index_b, divisions_per_beat)
            chosen_index = index_b if level_b > level_a else index_a

            return grid[chosen_index], AMBIGUOUS_TIME_CONFIDENCE, True

        def _quantize_note(self, note: Note, piece: Piece, divisions_per_beat: int, signaler: Signaler) -> None:
            new_onset, onset_confidence, onset_ambiguous = self._quantize_instant(note.onset, piece, divisions_per_beat)
            new_offset, offset_confidence, offset_ambiguous = self._quantize_instant(note.offset, piece, divisions_per_beat)

            note.onset = new_onset
            note.offset = new_offset
            note.reliability_duration = min(onset_confidence, offset_confidence)

            if onset_ambiguous or offset_ambiguous:
                measure = piece.compass_at_instant(note.onset)
                signaler.register(
                    SignalingCategory.LOW_CONFIDENCE_QUANTIZATION,
                    SeverityLevel.VERIFY,
                    "Quantização de baixa confiança: nota entre dois pontos do grid",
                    measure.index,
                    note
                )