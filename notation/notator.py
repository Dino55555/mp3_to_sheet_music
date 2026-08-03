from __future__ import annotations
from typing import Optional
from models.note import Note
from models.voice import Voice
from Compass.piece import Piece
from config import Config
from signaling.signaler import Signaler
from music_theory import spell_pitch

MERGE_GAP_TOLERANCE_SECONDS: float = 0.03
INTENSITY_PEAK_THRESHOLD: float = 0.3


class Notator:

    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        for voice in piece.voices:
            self._merge_rearticulations(voice)
            for note in voice.notes:
                self._spell_note(note, voice, piece)
        return piece

    def _should_merge(self, current: Note, following: Note) -> bool:
        if current.pitch != following.pitch:
            return False
        if following.onset - current.offset > MERGE_GAP_TOLERANCE_SECONDS:
            return False
        if current.is_ornament or following.is_ornament:
            return False
        if following.magnitude > current.magnitude * (1 + INTENSITY_PEAK_THRESHOLD):
            return False
        return True

    def _merge_group(self, group: list[Note]) -> Note:
        return Note(
            pitch=group[0].pitch,
            onset=group[0].onset,
            offset=group[-1].offset,
            magnitude=max(n.magnitude for n in group),
            reliability_existence=min(n.reliability_existence for n in group),
            reliability_highness=min(n.reliability_highness for n in group),
            reliability_duration=min(n.reliability_duration for n in group),
            reliability_voice=min(n.reliability_voice for n in group),
        )

    def _merge_rearticulations(self, voice: Voice) -> None:
        notes = voice.notes
        if not notes:
            return

        groups: list[list[Note]] = [[notes[0]]]
        for note in notes[1:]:
            if self._should_merge(groups[-1][-1], note):
                groups[-1].append(note)
            else:
                groups.append([note])

        new_notes = [
            self._merge_group(group) if len(group) >= 2 else group[0]
            for group in groups
        ]
        voice.replace_notes(new_notes)

    def _melodic_direction(self, note: Note, voice: Voice) -> Optional[str]:
        previous, following = voice.neighbour(note)
        reference = previous if previous is not None else following

        if reference is None:
            return None
        if note.pitch == reference.pitch:
            return None

        return 'ascending' if note.pitch > reference.pitch else 'descending'

    def _spell_note(self, note: Note, voice: Voice, piece: Piece) -> None:
        compass = piece.compass_at_instant(note.onset)
        direction = self._melodic_direction(note, voice)
        note.graphy = spell_pitch(note.pitch, compass.armor, direction)