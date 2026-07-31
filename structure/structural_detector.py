from __future__ import annotations
from typing import Optional, TypeVar
from models.compass import (Compass, KeySignature, TimeSignature, TonalMode)
from models.voice import (Voice, Clef)
from config import Config
from Compass.piece import Piece
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)
from models.raw_signals import Beat
from music_theory import (PitchClassHistogram, most_likely_major_tonic, choose_mode, accidents_of_major_tonic, TONIC_NAMES)

STRUCTURAL_SUSTAIN_LIMIT = 2
CONFIDENCE_BEAT_LIMIT = 0.5
MIN_PROPORTION_CONFIABLE_BEAT = 0.5

T = TypeVar("T")


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
                    measure.index
                )
        candidate_armors = self._detect_armors_by_measure(piece, signaler)
        armors = self._resolve_modulations(candidate_armors)
        for measure, armor in zip(piece.compasses, armors):
            measure.armor = armor
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

    def _resolve_sustained_changes(self, candidates: list[T], sustained_threshold: int, exclude_as_evidence: Optional[list[bool]] = None) -> list[T]:
        if not candidates:
            return []

        exclusions = (
            exclude_as_evidence if exclude_as_evidence is not None
            else [False] * len(candidates)
        )

        resolved = [candidates[0]]
        current_value = candidates[0]
        i = 1
        while i < len(candidates):
            candidate = candidates[i]
            if exclusions[i]:
                resolved.append(current_value)
                i += 1
                continue
            if candidate == current_value:
                resolved.append(current_value)
                i+=1
                continue
            sustained = 0
            j = i
            while j < len(candidates):
                if exclusions[j]:
                    j += 1
                    continue
                if candidates[j] == candidate:
                    sustained += 1
                else:
                    break
                j += 1
            if sustained >= sustained_threshold:
                current_value = candidate
            resolved.append(current_value)
            i += 1
        return resolved

    def _resolve_formula_changes(self, raw_formulas: list[TimeSignature], free_time_flags: list[bool]) -> list[TimeSignature]:
        return self._resolve_sustained_changes(raw_formulas, STRUCTURAL_SUSTAIN_LIMIT, free_time_flags)

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
            first_measure.armor,
            first_measure.free_time
        )
        new_measures = [pickup]
        for index, measure in enumerate(measures, start=2):
            measure.index = index
            new_measures.append(measure)
        last_measure = new_measures[-1]
        last_measure.end_time -= pickup_duration
        return new_measures

    def _detect_armors_by_measure(self, piece: Piece, signaler: Signaler) -> list[KeySignature]:
        armors: list[KeySignature] = []
        previous_armor: Optional[KeySignature] = None

        for measure in piece.compasses:
            notes = piece.notes_in_compass(measure.index)
            histogram = PitchClassHistogram.from_notes(notes)
            major_tonic = most_likely_major_tonic(histogram)
            last_note_pitch = notes[-1].pitch if notes else None

            result = choose_mode(histogram, major_tonic, last_note_pitch)

            if result is None:
                if previous_armor is not None:
                    armor = previous_armor
                else:
                    armor = KeySignature(0, "C", TonalMode.MAJOR)
                signaler.register(
                    SignalingCategory.AMBIGUOUS_KEY,
                    SeverityLevel.VERIFY,
                    "Tonalidade ambígua: mantida a armadura do compasso anterior",
                    measure.index
                )
            else:
                tonic, mode = result
                if mode is TonalMode.MAJOR:
                    accidents = accidents_of_major_tonic(tonic)
                else:
                    major_relative = (tonic + 3) % 12
                    accidents = accidents_of_major_tonic(major_relative)
                armor = KeySignature(accidents, TONIC_NAMES[tonic], mode)

            armors.append(armor)
            previous_armor = armor

        return armors

    def _resolve_modulations(self, candidate_armors: list[KeySignature]) -> list[KeySignature]:
        return self._resolve_sustained_changes(candidate_armors, STRUCTURAL_SUSTAIN_LIMIT)
