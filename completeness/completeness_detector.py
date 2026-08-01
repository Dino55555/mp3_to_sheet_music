from __future__ import annotations
from typing import Optional
from collections import Counter
from models.note import Note
from models.voice import Voice
from models.compass import Compass
from Compass.piece import Piece
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)
from rhythm.rhythmic_grid import (build_grid, closest_index)

COMPARISON_WINDOW_MEASURES: int = 4
MAX_CONFIRMATIONS_THRESHOLD: int = 3
HIGH_CONFIDENCE_THRESHOLD: float = 0.8
INFERRED_NOTE_EXISTENCE_CONFIDENCE: float = 0.9


class CompletenessDetector:

    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        for voice in piece.voices:
            for compass in piece.compasses:
                if compass.free_time:
                    continue
                self._evaluate_compass(compass, voice, piece, config.divisions_per_beat, signaler)
        return piece

    def _compass_signature(self, compass: Compass, voice: Voice, divisions_per_beat: int) -> dict[int, Note]:
        grid = build_grid(compass, divisions_per_beat)
        notes = voice.notes_on_interval(compass.begin_time, compass.end_time)

        signature: dict[int, Note] = {}
        for note in notes:
            index = closest_index(note.onset, grid)
            signature[index] = note
        return signature

    def _patterns_match(self, target_signature: dict[int, Note], neighbor_signature: dict[int, Note]) -> Optional[int]:
        target_positions = set(target_signature.keys())
        neighbor_positions = set(neighbor_signature.keys())

        if not target_positions.issubset(neighbor_positions):
            return None

        missing = neighbor_positions - target_positions
        if len(missing) != 1:
            return None

        return next(iter(missing))

    def _find_gap_candidates(
        self, target_compass: Compass, voice: Voice, piece: Piece, divisions_per_beat: int
    ) -> list[tuple[int, Note, int]]:
        target_position = target_compass.index - 1
        start = max(0, target_position - COMPARISON_WINDOW_MEASURES)
        end = min(len(piece.compasses), target_position + 1 + COMPARISON_WINDOW_MEASURES)

        neighbors = (
            piece.compasses[start:target_position]
            + piece.compasses[target_position + 1:end]
        )
        neighbors = [
            neighbor for neighbor in neighbors
            if neighbor.formula == target_compass.formula and not neighbor.free_time
        ]

        target_signature = self._compass_signature(target_compass, voice, divisions_per_beat)

        notes_by_position: dict[int, list[Note]] = {}
        for neighbor in neighbors:
            neighbor_signature = self._compass_signature(neighbor, voice, divisions_per_beat)
            gap_index = self._patterns_match(target_signature, neighbor_signature)
            if gap_index is None:
                continue
            notes_by_position.setdefault(gap_index, []).append(neighbor_signature[gap_index])

        candidates: list[tuple[int, Note, int]] = []
        for position, notes in notes_by_position.items():
            pitch_counts = Counter(note.pitch for note in notes)
            most_common_pitch, confirmations = pitch_counts.most_common(1)[0]
            model_note = next(note for note in notes if note.pitch == most_common_pitch)
            candidates.append((position, model_note, confirmations))

        return candidates

    def _create_inferred_note(self, model_note: Note, grid: list[float], index: int) -> Note:
        inferred = model_note.clone()
        duration = model_note.duration()
        inferred.onset = grid[index]
        inferred.offset = inferred.onset + duration
        inferred.reliability_existence = INFERRED_NOTE_EXISTENCE_CONFIDENCE
        return inferred

    def _evaluate_compass(
        self, compass: Compass, voice: Voice, piece: Piece, divisions_per_beat: int, signaler: Signaler
    ) -> None:
        candidates = self._find_gap_candidates(compass, voice, piece, divisions_per_beat)
        if not candidates:
            return

        grid = build_grid(compass, divisions_per_beat)

        for position, model_note, confirmations in candidates:
            confidence = min(1.0, confirmations / MAX_CONFIRMATIONS_THRESHOLD)

            if confidence >= HIGH_CONFIDENCE_THRESHOLD:
                inferred_note = self._create_inferred_note(model_note, grid, position)
                voice.add_note(inferred_note)
                signaler.register(
                    SignalingCategory.INFERRED_NOTE,
                    SeverityLevel.INFORMATIONAL,
                    "Nota inferida a partir de padrão repetitivo",
                    compass.index,
                    inferred_note
                )
            else:
                signaler.register(
                    SignalingCategory.POSSIBLE_MISSING_NOTE,
                    SeverityLevel.VERIFY,
                    "Possível nota faltando: padrão repetitivo com confirmação insuficiente",
                    compass.index
                )