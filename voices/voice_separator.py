from __future__ import annotations
from collections import Counter
from typing import Optional
from models.note import Note
from models.voice import (Voice, PaperVoice)
from config import Config
from Compass.piece import Piece
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)

SMALL_INTERVAL_THRESHOLD_SEMITONES: float = 4.0
RHYTHMIC_VARIETY_THRESHOLD: float = 0.3
PATTERN_REPETITION_THRESHOLD: float = 0.6
SIGNAL_WEIGHT: float = 1.0
HIGH_SCORE_THRESHOLD: float = 1.0


class VoiceSeparator:

    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        notes = piece.all_notes()

        vocal_result = self._apply_vocal_line_if_available(notes)
        if vocal_result is not None:
            melody_notes, accompaniment_notes = vocal_result
        else:
            melody_candidates, accompaniment_candidates = self._classify_by_register(notes)
            melody_notes, accompaniment_notes = self._resolve_by_contour(
                melody_candidates, accompaniment_candidates, signaler
            )

        melody_voice = Voice(paper=PaperVoice.MELODY)
        for note in melody_notes:
            melody_voice.add_note(note)

        accompaniment_voice = Voice(paper=PaperVoice.ACCOMPANIMENT)
        for note in accompaniment_notes:
            accompaniment_voice.add_note(note)

        piece.replace_voices([melody_voice, accompaniment_voice])
        return piece

    def _classify_by_register(self, notes: list[Note]) -> tuple[list[Note], list[Note]]:
        melody_candidates: list[Note] = []
        accompaniment_candidates: list[Note] = []

        for note in notes:
            simultaneous = [
                other for other in notes if other is not note and note.overlap(other)
            ]
            group_pitches = [n.pitch for n in simultaneous] + [note.pitch]
            if note.pitch == max(group_pitches):
                melody_candidates.append(note)
            else:
                accompaniment_candidates.append(note)

        melody_candidates.sort(key=lambda n: n.onset)
        accompaniment_candidates.sort(key=lambda n: n.onset)
        return melody_candidates, accompaniment_candidates

    def _average_interval(self, flow: list[Note]) -> float:
        if len(flow) < 2:
            return 0.0
        intervals = [
            flow[i].interval_in_semitones(flow[i + 1]) for i in range(len(flow) - 1)
        ]
        return sum(intervals) / len(intervals)

    def _rhythmic_variety(self, flow: list[Note]) -> float:
        if len(flow) < 2:
            return 0.0
        durations = [note.duration() for note in flow]
        mean = sum(durations) / len(durations)
        if mean == 0.0:
            return 0.0
        variance = sum((d - mean) ** 2 for d in durations) / len(durations)
        return (variance ** 0.5) / mean

    def _pattern_repetition(self, flow: list[Note]) -> float:
        if len(flow) < 2:
            return 0.0
        pairs = [
            (flow[i].interval_in_semitones(flow[i + 1]), round(flow[i].duration(), 1))
            for i in range(len(flow) - 1)
        ]
        if not pairs:
            return 0.0
        most_common_count = Counter(pairs).most_common(1)[0][1]
        return most_common_count / len(pairs)

    def _melodic_score(self, flow: list[Note]) -> float:
        score = 0.0
        if self._average_interval(flow) < SMALL_INTERVAL_THRESHOLD_SEMITONES:
            score += SIGNAL_WEIGHT
        if self._rhythmic_variety(flow) > RHYTHMIC_VARIETY_THRESHOLD:
            score += SIGNAL_WEIGHT
        if self._pattern_repetition(flow) > PATTERN_REPETITION_THRESHOLD:
            score -= SIGNAL_WEIGHT
        return score

    def _resolve_by_contour(
        self,
        melody_candidates: list[Note],
        accompaniment_candidates: list[Note],
        signaler: Signaler,
    ) -> tuple[list[Note], list[Note]]:
        if not melody_candidates or not accompaniment_candidates:
            return melody_candidates, accompaniment_candidates

        melody_score = self._melodic_score(melody_candidates)
        accompaniment_score = self._melodic_score(accompaniment_candidates)

        if melody_score >= HIGH_SCORE_THRESHOLD and accompaniment_score >= HIGH_SCORE_THRESHOLD:
            signaler.register(
                SignalingCategory.UNRESOLVED_COUNTERPOINT,
                SeverityLevel.REQUIRES_DECISION,
                "Contraponto não resolvido: duas linhas com comportamento melódico igualmente forte",
                1,
            )
            return melody_candidates, accompaniment_candidates

        if accompaniment_score > melody_score:
            return accompaniment_candidates, melody_candidates

        return melody_candidates, accompaniment_candidates

    def _apply_vocal_line_if_available(
        self, notes: list[Note]
    ) -> Optional[tuple[list[Note], list[Note]]]:
        if not any(note.vocal_origin_identified for note in notes):
            return None

        vocal_notes = [note for note in notes if note.vocal_origin_identified]
        other_notes = [note for note in notes if not note.vocal_origin_identified]
        vocal_notes.sort(key=lambda n: n.onset)
        other_notes.sort(key=lambda n: n.onset)
        return vocal_notes, other_notes