from __future__ import annotations
from models.note import Note
from models.voice import Voice
from Compass.piece import Piece
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)

CHORD_REACH_LIMIT_SEMITONES: int = 16
BASE_LEAP_TIME_SECONDS: float = 0.05
TIME_PER_SEMITONE_SECONDS: float = 0.008


class PlayabilityChecker:

    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        #Componente exclusivamente de verificacao - nunca muta nenhuma Nota
        for voice in piece.voices:
            self._check_chord_reach(voice, piece, signaler)
            self._check_leap_speed(voice, piece, signaler)
        return piece

    def _group_into_chords(self, voice: Voice) -> list[list[Note]]:
        #Agrupa notas simultaneas; deduplica via id() (Note nao e hashable)
        #para impedir que a mesma tríade gere grupos sobrepostos
        assigned_ids: set[int] = set()
        groups: list[list[Note]] = []

        for note in voice.notes:
            if id(note) in assigned_ids:
                continue

            simultaneous = voice.simultaneous_of(note)
            group = [note] + [n for n in simultaneous if id(n) not in assigned_ids]

            if len(group) < 2:
                assigned_ids.add(id(note))
                continue

            for grouped_note in group:
                assigned_ids.add(id(grouped_note))
            groups.append(group)

        return groups

    def _check_chord_reach(self, voice: Voice, piece: Piece, signaler: Signaler) -> None:
        for group in self._group_into_chords(voice):
            pitches = [note.pitch for note in group]
            reach = max(pitches) - min(pitches)
            if reach > CHORD_REACH_LIMIT_SEMITONES:
                lowest_note = min(group, key=lambda n: n.pitch)
                compass = piece.compass_at_instant(lowest_note.onset)
                signaler.register(
                    SignalingCategory.IMPOSSIBLE_PASSAGE,
                    SeverityLevel.REQUIRES_DECISION,
                    "Acorde com alcance maior do que uma mão consegue cobrir",
                    compass.index,
                    lowest_note,
                )

    def _check_leap_speed(self, voice: Voice, piece: Piece, signaler: Signaler) -> None:
        for note in voice.notes:
            _, following = voice.neighbour(note)
            if following is None:
                continue

            distance = note.interval_in_semitones(following)
            available_time = following.onset - note.offset
            minimum_time = BASE_LEAP_TIME_SECONDS + distance * TIME_PER_SEMITONE_SECONDS

            if available_time < minimum_time:
                compass = piece.compass_at_instant(following.onset)
                signaler.register(
                    SignalingCategory.IMPOSSIBLE_PASSAGE,
                    SeverityLevel.REQUIRES_DECISION,
                    "Salto melódico rápido demais para a mão se reposicionar a tempo",
                    compass.index,
                    following,
                )