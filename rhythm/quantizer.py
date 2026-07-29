from __future__ import annotations
from models.note import Note
from models.voice import Voice
from models.compass import Compass
from Compass.piece import Piece
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)

SMALL_THRESHOLD_FRACTION: float = 0.15
AMBIGUITY_TOLERANCE_FRACTION: float = 0.2
MODERATE_DEVIATION_CONFIDENCE: float = 0.7
AMBIGUOUS_TIME_CONFIDENCE: float = 0.3

ORNAMENT_THRESHOLD_FRACTION: float = 0.5
ORNAMENT_INTERVAL_THRESHOLD_SEMITONES: int = 2
MIN_TRILL_REPETITIONS: int = 3
SMALL_GAP_FRACTION: float = 0.15
MAX_STACCATO_GAP_FRACTION: float = 0.5
MIN_STACCATO_REPETITIONS: int = 3
MIN_NOTES_FOR_GROOVE_PATTERN: int = 4
GROOVE_CONSISTENCY_THRESHOLD: float = 0.3


class Quantizer:
    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        for voice in piece.voices:
            for note in voice.notes:
                self._quantize_note(note, piece, config.divisions_per_beat, signaler)

            self._classify_ornaments(voice, piece, config.divisions_per_beat)
            self._detect_trills(voice)
            self._process_gaps(voice, piece, config.divisions_per_beat)
            patterns = self._detect_groove_patterns(voice, piece, config.divisions_per_beat)
            self._apply_groove(voice, piece, patterns, config.divisions_per_beat, signaler)

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

        return grid[index_a], MODERATE_DEVIATION_CONFIDENCE, False

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

    def _compass_and_spacing(self, piece: Piece, instant: float, divisions_per_beat: int) -> tuple[Compass, float]:
        compass = piece.compass_at_instant(instant)
        grid = self._build_grid(compass, divisions_per_beat)
        spacing = grid[1] - grid[0]

        return compass, spacing

    def _grid_index(self, instant: float, compass: Compass, spacing: float) -> int:
        return round((instant - compass.begin_time) / spacing)

    def _classify_ornaments(self, voice: Voice, piece: Piece, divisions_per_beat: int) -> None:
        for note in voice.notes:
            _, spacing = self._compass_and_spacing(piece, note.onset, divisions_per_beat)
            if note.duration() >= ORNAMENT_THRESHOLD_FRACTION * spacing:
                continue

            previous, following = voice.neighbour(note)
            candidates = [n for n in (previous, following) if n is not None]
            if not candidates:
                continue

            closest = min(candidates, key=lambda n: note.interval_in_semitones(n))
            if note.interval_in_semitones(closest) <= ORNAMENT_INTERVAL_THRESHOLD_SEMITONES:
                note.is_ornament = True

    def _detect_trills(self, voice: Voice) -> None:
        return

    def _process_gaps(self, voice: Voice, piece: Piece, divisions_per_beat: int) -> None:
        notes = voice.notes
        candidate_flags = [False] * len(notes)

        for i in range(len(notes) - 1):
            n1 = notes[i]
            n2 = notes[i + 1]
            if n1.is_ornament or n2.is_ornament:
                continue

            gap = n2.onset - n1.offset
            _, spacing = self._compass_and_spacing(piece, n1.onset, divisions_per_beat)

            if gap <= SMALL_GAP_FRACTION * spacing:
                n1.offset = n2.onset
            elif gap <= MAX_STACCATO_GAP_FRACTION * spacing:
                candidate_flags[i] = True

        i = 0
        total = len(candidate_flags)
        while i < total:
            if not candidate_flags[i]:
                i += 1
                continue
            j = 1
            while j < total and candidate_flags[j]:
                j += 1
            if j - 1 >= MIN_STACCATO_REPETITIONS:
                for k in range(i, j):
                    notes[k].staccato = True
            i = j

    def _detect_groove_patterns(self, voice: Voice, piece: Piece, divisions_per_beat: int) -> dict[int, float]:
        groups: dict[int, list[None]] = {}
        for note in voice.notes:
            if note.is_ornament or note.raw_onset is None:
                continue

            compass, spacing = self._compass_and_spacing(piece, note.onset, divisions_per_beat)
            index_in_grid = self._grid_index(note.onset, compass, spacing)
            local_position = index_in_grid % divisions_per_beat
            if local_position == 0:
                continue
            groups.setdefault(local_position, []).append(note)

        patterns: dict[int, float] = {}
        for position, notes in groups.items():
            if len(notes) < MIN_NOTES_FOR_GROOVE_PATTERN:
                continue

            deviations = [note.raw_onset - note.onset for note in notes]
            mean_deviation = sum(deviations) / len(deviations)

            _, spacing = self._compass_and_spacing(piece, notes[0].onset, divisions_per_beat)
            if abs(mean_deviation) <= SMALL_THRESHOLD_FRACTION * spacing:
                continue
            if mean_deviation == 0:
                continue

            variance = sum((d - mean_deviation) ** 2 for d in deviations) /len(deviations)
            std_dev = variance ** 0.5
            coefficient_of_variation = abs(std_dev / mean_deviation)

            if coefficient_of_variation < GROOVE_CONSISTENCY_THRESHOLD:
                patterns[position] = mean_deviation

        return patterns

    def _apply_groove(self, voice: Voice, piece: Piece, patterns: dict[int, float], divisions_per_beat: int, signaler: Signaler) -> None:
        for note in voice.notes:
            if note.is_ornament:
                continue
            compass, spacing = self._compass_and_spacing(piece, note.onset, divisions_per_beat)
            index_in_grid = self._grid_index(note.onset, compass, spacing)
            local_position = index_in_grid % divisions_per_beat
            if local_position in patterns:
                note.reliability_duration = 1.0
                compass.feel_indication = 'swing'