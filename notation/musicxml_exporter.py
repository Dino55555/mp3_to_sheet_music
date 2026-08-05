from __future__ import annotations
from music21 import stream as m21_stream
from music21 import note as m21_note_module
from music21 import meter as m21_meter
from music21 import key as m21_key
from music21 import pitch as m21_pitch_module
from music21 import clef as m21_clef
from music21 import articulations as m21_articulations

from models.note import Note
from models.voice import (Voice, Clef)
from models.compass import Compass
from Compass.piece import Piece


class MusicXMLExporter:

    def export(self, piece: Piece, path: str) -> None:
        score = self._build_score(piece)
        score.write('musicxml', fp=path)

    def _quarterlength_factor_per_second(self, compass: Compass) -> float:
        quarterlength_per_group = 1.5 if compass.formula.is_compound else 1.0
        seconds_per_group = compass.duration() / compass.formula.beat_groups()
        return quarterlength_per_group / seconds_per_group

    def _cumulative_offsets(self, piece: Piece) -> dict[int, float]:
        offsets: dict[int, float] = {}
        cumulative = 0.0
        for compass in piece.compasses:
            offsets[compass.index] = cumulative
            cumulative += compass.duration() * self._quarterlength_factor_per_second(compass)
        return offsets

    def _m21_pitch(self, spelling) -> m21_pitch_module.Pitch:
        return m21_pitch_module.Pitch(
            step=spelling.letter_class,
            accidental=spelling.alteration,
            octave=spelling.octave,
        )

    def _m21_note(self, note: Note, factor: float) -> m21_note_module.Note:
        m21_note_obj = m21_note_module.Note(self._m21_pitch(note.graphy))
        m21_note_obj.quarterLength = note.duration() * factor
        if note.staccato:
            m21_note_obj.articulations.append(m21_articulations.Staccato())
        return m21_note_obj

    def _build_part(self, voice: Voice, piece: Piece, offsets: dict[int, float]) -> m21_stream.Part:
        part = m21_stream.Part()

        m21_clef_obj = m21_clef.TrebleClef() if voice.clef is Clef.SOL else m21_clef.BassClef()
        part.insert(0, m21_clef_obj)

        previous_compass: Compass | None = None
        for compass in piece.compasses:
            offset = offsets[compass.index]
            factor = self._quarterlength_factor_per_second(compass)

            if previous_compass is None or compass.formula != previous_compass.formula:
                part.insert(
                    offset,
                    m21_meter.TimeSignature(f"{compass.formula.numerator}/{compass.formula.denominator}")
                )
            if previous_compass is None or compass.armor != previous_compass.armor:
                part.insert(offset, m21_key.KeySignature(compass.armor.accidents_qunatity))

            for note in voice.notes_on_interval(compass.begin_time, compass.end_time):
                note_offset = offset + (note.onset - compass.begin_time) * factor
                part.insert(note_offset, self._m21_note(note, factor))

            previous_compass = compass

        part.makeNotation(inPlace=True)
        return part

    def _build_score(self, piece: Piece) -> m21_stream.Score:
        offsets = self._cumulative_offsets(piece)
        score = m21_stream.Score()
        for voice in piece.voices:
            score.insert(0, self._build_part(voice, piece, offsets))
        return score