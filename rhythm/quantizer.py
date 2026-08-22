from __future__ import annotations
from typing import Optional
from models.note import Note
from models.voice import Voice
from models.compass import Compass
from Compass.piece import Piece
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)
from structure.structural_detector import (StructuralDetector, STRUCTURAL_SUSTAIN_LIMIT)
from rhythm.rhythmic_grid import (build_grid, closest_index)

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

TERNARY_DIVISIONS: int = 3
TERNARY_BETTER_ERROR_THRESHOLD: float = 0.6
MIN_NOTES_PER_BEAT_GROUP: int = 2
MIN_TERNARY_GROUPS_PROPORTION: float = 0.6


class Quantizer:
    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        for voice in piece.voices:
            self._capture_raw_values(voice)

        for voice in piece.voices:
            for note in voice.notes:
                self._quantize_note(note, piece, config.divisions_per_beat, signaler)

        self._resolve_compound_meter(piece, config, signaler)

        for voice in piece.voices:
            self._classify_ornaments(voice, piece, config.divisions_per_beat)
            self._detect_trills(voice)
            self._process_gaps(voice, piece, config.divisions_per_beat)
            patterns = self._detect_groove_patterns(voice, piece, config.divisions_per_beat)
            self._apply_groove(voice, piece, patterns, config.divisions_per_beat, signaler)

        return piece

    def _capture_raw_values(self, voice: Voice) -> None:
        for note in voice.notes:
            if note.raw_onset is None:
                note.raw_onset, note.raw_offset = note.onset, note.offset

    def _two_closest(self, instant: float, grid: list[float]) -> tuple[int, int]:
        closest = closest_index(instant, grid)
        remaining_indices = [i for i in range(len(grid)) if i != closest]
        second_closest = min(remaining_indices, key=lambda i: abs(instant - grid[i]))
        return closest, second_closest

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
        grid = build_grid(compass, divisions_per_beat)
        grid_spacing = grid[1] - grid[0]

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

        if new_offset <= new_onset:
            #Colisao: dois arredondamentos independentes (onset e offset)
            #caem no mesmo ponto do grid, ou o offset ficou antes do onset -
            #nao e evidencia acustica de espuriedade (essa avaliacao ja
            #aconteceu no Limpador, A1-A3), so um artefato aritmetico da
            #quantizacao independente dos dois extremos
            _, spacing = self._compass_and_spacing(piece, new_onset, divisions_per_beat)
            new_offset = new_onset + spacing
            note.reliability_duration = AMBIGUOUS_TIME_CONFIDENCE
            measure = piece.compass_at_instant(new_onset)
            signaler.register(
                SignalingCategory.LOW_CONFIDENCE_QUANTIZATION,
                SeverityLevel.INFORMATIONAL,
                "Duração ajustada após colisão de quantização",
                measure.index,
                note
            )
            note.redefine_time(new_onset, new_offset)
            return

        note.redefine_time(new_onset, new_offset)
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
        grid = build_grid(compass, divisions_per_beat)
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
                n1.redefine_time(n1.onset, n2.onset)
            elif gap <= MAX_STACCATO_GAP_FRACTION * spacing:
                candidate_flags[i] = True

        i = 0
        total = len(candidate_flags)
        while i < total:
            if not candidate_flags[i]:
                i += 1
                continue
            j = i
            while j < total and candidate_flags[j]:
                j += 1
            if j - i >= MIN_STACCATO_REPETITIONS:
                for k in range(i, j):
                    notes[k].staccato = True
            i = j

    def _detect_groove_patterns(self, voice: Voice, piece: Piece, divisions_per_beat: int) -> dict[int, float]:
        groups: dict[int, list[Note]] = {}
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
            variance = sum((d - mean_deviation) ** 2 for d in deviations) / len(deviations)
            std_dev = variance ** 0.5
            coefficient_of_variation = abs(std_dev / mean_deviation)
            if coefficient_of_variation < GROOVE_CONSISTENCY_THRESHOLD:
                patterns[position] = mean_deviation
        return patterns

    def _apply_groove(
        self,
        voice: Voice,
        piece: Piece,
        patterns: dict[int, float],
        divisions_per_beat: int,
        signaler: Signaler,
    ) -> None:
        for note in voice.notes:
            if note.is_ornament:
                continue
            compass, spacing = self._compass_and_spacing(piece, note.onset, divisions_per_beat)
            index_in_grid = self._grid_index(note.onset, compass, spacing)
            local_position = index_in_grid % divisions_per_beat
            if local_position in patterns:
                note.reliability_duration = 1.0
                compass.feel_indication = "swing"

    def _total_fit_error(self, raw_onsets: list[float], grid: list[float]) -> float:
        return sum(abs(onset - grid[closest_index(onset, grid)]) for onset in raw_onsets)

    def _subdivision_grid(self, start: float, end: float, subdivisions: int) -> list[float]:
        step = (end - start) / subdivisions
        return [start + i * step for i in range(subdivisions + 1)]

    def _compass_beat_groups(self, compass: Compass) -> list[tuple[float, float]]:
        group_count = compass.formula.beat_groups()
        duration = compass.end_time - compass.begin_time
        group_duration = duration / group_count
        return [
            (compass.begin_time + i * group_duration, compass.begin_time + (i + 1) * group_duration)
            for i in range(group_count)
        ]

    def _classify_compass_meter(self, compass: Compass, piece: Piece, divisions_per_beat: int) -> Optional[bool]:
        groups = self._compass_beat_groups(compass)
        all_notes = piece.all_notes()
        evaluations: list[bool] = []
        for start, end in groups:
            raw_onsets = [
                note.raw_onset for note in all_notes
                if note.raw_onset is not None and start <= note.raw_onset < end
            ]
            if len(raw_onsets) < MIN_NOTES_PER_BEAT_GROUP:
                continue
            binary_grid = self._subdivision_grid(start, end, divisions_per_beat)
            ternary_grid = self._subdivision_grid(start, end, TERNARY_DIVISIONS)
            binary_error = self._total_fit_error(raw_onsets, binary_grid)
            ternary_error = self._total_fit_error(raw_onsets, ternary_grid)
            evaluations.append(ternary_error < TERNARY_BETTER_ERROR_THRESHOLD * binary_error)
        if not evaluations:
            return None
        proportion = sum(evaluations) / len(evaluations)
        return proportion >= MIN_TERNARY_GROUPS_PROPORTION

    def _resolve_compound_meter(self, piece: Piece, config: Config, signaler: Signaler) -> None:
        evaluable_compasses = [c for c in piece.compasses if not c.free_time]
        if not evaluable_compasses:
            return
        raw_candidates: list[bool] = []
        exclude_flags: list[bool] = []
        for compass in evaluable_compasses:
            result = self._classify_compass_meter(compass, piece, config.divisions_per_beat)
            if result is None:
                raw_candidates.append(False)
                exclude_flags.append(True)
            else:
                raw_candidates.append(result)
                exclude_flags.append(False)
        structural_detector = StructuralDetector()
        resolved = structural_detector._resolve_sustained_changes(
            raw_candidates, STRUCTURAL_SUSTAIN_LIMIT, exclude_flags
        )
        for compass, is_compound in zip(evaluable_compasses, resolved):
            if is_compound and not compass.formula.is_compound:
                compass.formula = compass.formula.convert_to_compound()
                self._requantize_compass(compass, piece, TERNARY_DIVISIONS, signaler)

    def _requantize_compass(self, compass: Compass, piece: Piece, divisions_per_beat: int, signaler: Signaler) -> None:
        for voice in piece.voices:
            for note in voice.notes:
                if note.raw_onset is None or not compass.has_time(note.raw_onset):
                    continue
                note.onset, note.offset = note.raw_onset, note.raw_offset
                self._quantize_note(note, piece, divisions_per_beat, signaler)