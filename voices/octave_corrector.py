from __future__ import annotations
from models.note import Note
from models.voice import (Voice, PaperVoice)
from Compass.instrument import Instrument
from Compass.piece import Piece
from config import Config
from signaling.signaler import Signaler

OCTAVE_TOLERANCE_SEMITONES: int = 1
CONTOUR_WINDOW_SIZE: int = 2
STEPWISE_MOTION_THRESHOLD_SEMITONES: float = 2.5
MAX_SUM_AFTER_CORRECTION_THRESHOLD_SEMITONES: float = 5.0
CENTER_DISTANCE_THRESHOLD_SEMITONES: float = 9.0
CONSISTENT_PATTERN_PROPORTION_THRESHOLD: float = 0.4
CONFIDENCE_AFTER_CORRECTION: float = 1.0


class OctaveCorrector:

    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        for voice in piece.voices:
            self._correct_implausible_leap(voice)
            if voice.paper is PaperVoice.ACCOMPANIMENT:
                self._correct_accompaniment_register(voice)
            self._correct_out_of_range(voice, piece.instrument)

        return piece

    def _contour_window(self, voice: Voice, index: int) -> list[Note]:
        notes = voice.notes
        current = notes[index]

        before: list[Note] = []
        node = current
        for _ in range(CONTOUR_WINDOW_SIZE):
            previous, _ = voice.neighbour(node)
            if previous is None:
                break
            before.insert(0, previous)
            node = previous

        after: list[Note] = []
        node = current
        for _ in range(CONTOUR_WINDOW_SIZE):
            _, following = voice.neighbour(node)
            if following is None:
                break
            after.append(following)
            node = following

        return before + after

    def _average_jump(self, notes: list[Note]) -> float:
        if len(notes) < 2:
            return 0.0
        jumps = [
            notes[i].interval_in_semitones(notes[i + 1])
            for i in range(len(notes) - 1)
        ]

        return sum(jumps) / len(jumps)

    def _is_approximately_octave(self, interval: int) -> bool:
        return abs(interval - 12) <= OCTAVE_TOLERANCE_SEMITONES

    def _correct_implausible_leap(self, voice: Voice) -> None:
        notes = voice.notes
        for index in range(1, len(notes) - 1):
            note = notes[index]
            previous, following = voice.neighbour(note)
            if previous is None or following is None:
                continue

            leap_to = note.interval_in_semitones(previous)
            leap_from = following.interval_in_semitones(note)
            if not (
                self._is_approximately_octave(leap_to)
                and self._is_approximately_octave(leap_from)
            ):
                continue

            window = self._contour_window(voice, index)
            if self._average_jump(window) >= STEPWISE_MOTION_THRESHOLD_SEMITONES:
                continue

            best_shift = None
            best_sum = None
            for shift in (-12, 12):
                candidate_pitch = note.pitch + shift
                new_leap_to = abs(candidate_pitch - previous.pitch)
                new_leap_from = abs(following.pitch - candidate_pitch)
                total = new_leap_to + new_leap_from
                if best_sum is None or total < best_sum:
                    best_sum = total
                    best_shift = shift

            if best_shift is not None and best_sum < MAX_SUM_AFTER_CORRECTION_THRESHOLD_SEMITONES:
                note.transpose(best_shift)
                note.reliability_highness = CONFIDENCE_AFTER_CORRECTION

    def _median(self, values: list[int]) -> float:
        ordered = sorted(values)
        count = len(ordered)
        middle = count // 2
        if count % 2 == 1:
            return float(ordered[middle])
        return (ordered[middle - 1] + ordered[middle]) / 2.0

    def _correct_accompaniment_register(self, voice: Voice) -> None:
        if not voice.notes:
            return

        corrections: dict[int, int] = {}
        for position, note in enumerate(voice.notes):
            simultaneous = voice.simultaneous_of(note)
            if not simultaneous:
                continue

            center = self._median([n.pitch for n in simultaneous])
            distance = abs(note.pitch - center)
            if distance <= CENTER_DISTANCE_THRESHOLD_SEMITONES:
                continue

            shift = -12 if note.pitch > center else 12
            candidate_distance = abs((note.pitch + shift) - center)
            if candidate_distance < distance:
                corrections[position] = shift

        proportion = len(corrections) / len(voice.notes)
        if proportion < CONSISTENT_PATTERN_PROPORTION_THRESHOLD:
            for position, shift in corrections.items():
                note = voice.notes[position]
                note.transpose(shift)
                note.reliability_highness = CONFIDENCE_AFTER_CORRECTION

    def _correct_out_of_range(self, voice: Voice, instrument: Instrument) -> None:
        for note in voice.notes:
            if instrument.is_in_range(note.pitch):
                continue

            previous, following = voice.neighbour(note)
            existing_neighbours = [n for n in (previous, following) if n is not None]
            if existing_neighbours and all(
                not instrument.is_in_range(n.pitch) for n in existing_neighbours
            ):
                continue

            shift = 12 if note.pitch < instrument.range_min else -12
            while not instrument.is_in_range(note.pitch):
                note.transpose(shift)
            note.reliability_highness = CONFIDENCE_AFTER_CORRECTION