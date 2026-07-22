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
            else:
                current_group.append(beat)
        if current_group and len(current_group) > 1:
            groups.append(current_group)
        return groups

    def _formula_from_group(self, group: list[Beat]) -> TimeSignature:
        return TimeSignature(numerator=len(group), denominator=4)

    def _group_is_free_time(self, group: list[Beat]) -> bool:
        if not group:
            return True
        reliable_beats = sum(1 for beat in group if beat.confidence >= CONFIDENCE_BEAT_LIMIT)
        proportion = reliable_beats/len(group)
        return (proportion < MIN_PROPORTION_CONFIABLE_BEAT)

    def _resolve_formula_changes(self, raw_formulas: list[TimeSignature], free_time_flags: list[bool]) -> list[TimeSignature]:
        if not raw_formulas:
            return []
        resolved = [raw_formulas[0]]
        current_formula = raw_formulas[0]
        i = 1
        while i < len(raw_formulas):
            candidate = raw_formulas[i]
            if free_time_flags[i]:
                resolved.append(current_formula)
                i += 1
                continue
            if candidate == current_formula:
                resolved.append(current_formula)
                i+=1
                continue
            sustained = 0
            j = i
            while j < len(raw_formulas):
                if free_time_flags[j]:
                    j += 1
                    continue
                if raw_formulas[j] == candidate:
                    sustained += 1
                else:
                    break
                j += 1
            if sustained >= COMPASS_SUSTAIN_LIMIT:
                current_formula = candidate
            resolved.append(current_formula)
            i += 1
        return resolved

    def _build_measures(self, groups: list[list[Beat]], formulas: list[TimeSignature], free_time_flags: list[bool]) -> list[Compass]:
        measures: list[Compass] = []
        for index, group in enumerate(groups):
            begin = group[0].instant
            if index < len(groups) - 1:
                end = groups[index + 1][0].instant
            else:
                if len(group) > 1:
                    intervals = [
                        group[i + 1].instant - group[i].instant
                        for i in range(len(group) - 1)
                    ]
                    average_duration = sum(intervals) / len(intervals)
                else:
                    average_duration = 1.0
                end = group[-1].instant + average_duration
            measure = Compass(
                index + 1,
                begin,
                end,
                formulas[index],
                KeySignature(0, "C", TonalMode.MAJOR),
                free_time_flags[index]
            )
            measures.append(measure)
        return measures

    def _detect_and_adjust_pickup(self, piece: Piece, measures: list[Compass]) -> list[Compass]:
        if not measures:
            return measures
        
        notes = piece.all_notes()
        if not notes:
            return measures
        
        first_note = min(note.onset for note in notes)
        first_measure = measures[0]
        if first_note >= first_measure.begin_time:
            return measures
        
        pickup_duration = (first_measure.begin_time - first_note)
        pickup = Compass(
            1,
            first_note,
            first_measure.begin_time,
            first_measure.formula,
            first_measure.KeySignature,
            first_measure.free_time
        )
        new_measures = [pickup]
        for index, measure in enumerate(measures, start=2):
            measure.number = index
            new_measures.append(measure)
        last_measure = new_measures[-1]
        last_measure.end_time -= pickup_duration
        return new_measures