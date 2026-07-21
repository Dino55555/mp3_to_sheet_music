from __future__ import annotations
from models.compass import (Compass, KeySignature, TimeSignature, TonalMode)
from models.voice import (Voice, Clef)
from config import Config
from Compass.piece import Piece
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)
from models.raw_signals import Beat

COMPASS_SUSTAIN_LIMIT = 2
CONFIDENCE_BEAT_LIMIT = 0.5
MIN_PROPORTION_CONFIABLE_BEAT = 0.5


class StructuralDetector:
    
    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        if (piece.raw_signals is None or len(piece.raw_signals.beats) == 0):
            raise ValueError("Peça não tem sinais brutos")

        groups = self._group_candidate_measures(piece.raw_signals.beats)
        raw_formulas = [self._formula_from_group(group) for group in groups]
        free_time_flags = [self._group_is_free_time(group) for group in groups]
        formulas = self._resolve_formula_changes(raw_formulas, free_time_flags)
        measures = self._build_measures(groups, formulas, free_time_flags)
        measures = self._detect_and_adjust_pickup(piece, measures)
        piece.compasses.clear()
        for measure in measures:
            piece.add_compass(measure)
            if measure.free_time:
                signaler.register(
                    SignalingCategory.FREE_TIME_APPROXIMATION,
                    SeverityLevel.INFORMATIONAL,
                    "Trecho aproximado como tempo livre",
                    measure.number
                )
        return piece 
    
    def _group_candidate_measures(self, beats: list[Beat]) -> list[list[Beat]]:
        if not beats:
            return []
        groups: list[list[Beat]] = []
        current_group: list[Beat] = []
        for beat in beats:
            if beat.is_strong_beat and current_group:
                groups.append(current_group)
                current_group = []
            current_group.append(beat)
        if current_group:
            groups.append(current_group)
        return groups

    def _formula_from_group(self, group: list[Beat]) -> TimeSignature:
        return TimeSignature(numerator=len(group), denominator=4)

    def _group_is_free_time(self, group: list[Beat]) -> bool:
        pass

    def _resolve_formula_changes(self, raw_formulas: list[TimeSignature], free_time_flags: list[bool]) -> list[TimeSignature]:
        pass

    def _build_measures(self, groups: list[list[Beat]], formulas: list[TimeSignature], free_time_flags: list[bool]) -> list[Compass]:
        pass

    def _detect_and_adjust_pickup(self, piece: Piece, measures: list[Compass]) -> list[Compass]:
        pass