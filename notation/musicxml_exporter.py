from __future__ import annotations
from music21 import stream as m21_stream
from music21 import note as m21_note_module
from music21 import meter as m21_meter
from music21 import key as m21_key
from music21 import pitch as m21_pitch_module
from music21 import clef as m21_clef
from music21 import articulations as m21_articulations
from music21 import expressions as m21_expressions

from models.note import Note
from models.voice import (Voice, Clef)
from models.compass import Compass
from models.signaling import (Signaling, SeverityLevel)
from Compass.piece import Piece
from config import Config
from signaling.signaler import Signaler
from signaling.report_generator import ReportGenerator

FREE_TIME_TEXT: str = "rubato"
SEVERITY_COLORS: dict[SeverityLevel, str] = {
    SeverityLevel.REQUIRES_DECISION: "#D32F2F",
    SeverityLevel.VERIFY: "#F57C00",
    SeverityLevel.INFORMATIONAL: "#1976D2",
}


class MusicXMLExporter:

    def export(self, piece: Piece, score_path: str, signaler: Signaler, report_path: str, config: Config) -> None:
        score, note_map = self._build_score(piece, config)
        self._apply_visual_marking(note_map, signaler.ordered_report())
        score.write('musicxml', fp=score_path)
        ReportGenerator().generate(signaler, report_path)

    def _quarterlength_factor_per_second(self, compass: Compass) -> float:
        quarterlength_per_group = 1.5 if compass.formula.is_compound else 1.0
        seconds_per_group = compass.duration() / compass.formula.beat_groups()
        return quarterlength_per_group / seconds_per_group

    def _round_to_grid_step(self, value_ql: float, config: Config, is_compound: bool) -> float:
        step = (1.5 if is_compound else 1.0) / config.divisions_per_beat
        return round(value_ql / step) * step

    def _cumulative_offsets(self, piece: Piece) -> dict[int, float]:
        offsets: dict[int, float] = {}
        cumulative = 0.0
        for compass in piece.compasses:
            offsets[compass.index] = cumulative
            quarterlength_per_group = 1.5 if compass.formula.is_compound else 1.0
            cumulative += quarterlength_per_group * compass.formula.beat_groups()
        return offsets

    def _m21_pitch(self, spelling) -> m21_pitch_module.Pitch:
        return m21_pitch_module.Pitch(
            step=spelling.letter_class,
            accidental=spelling.alteration,
            octave=spelling.octave,
        )

    def _m21_note(self, note: Note, factor: float, config: Config, is_compound: bool) -> m21_note_module.Note:
        m21_note_obj = m21_note_module.Note(self._m21_pitch(note.graphy))
        if note.staccato:
            m21_note_obj.articulations.append(m21_articulations.Staccato())

        if note.is_ornament:
            #Grace note: nao ocupa quarterLength no fluxo temporal do
            #compasso - "quanto tempo isso ocupa?" nao se aplica, entao
            #nenhum arredondamento de grid acontece para ornamentos
            return m21_note_obj.getGrace()

        raw_ql = note.duration() * factor
        m21_note_obj.quarterLength = self._round_to_grid_step(raw_ql, config, is_compound)
        return m21_note_obj

    def _build_part(
        self, voice: Voice, piece: Piece, offsets: dict[int, float], config: Config
    ) -> tuple[m21_stream.Part, dict[int, m21_note_module.Note]]:
        part = m21_stream.Part()
        note_map: dict[int, m21_note_module.Note] = {}
        note_offsets: dict[int, float] = {}
        pending_ornaments: list[tuple[Note, float, float, bool]] = []

        m21_clef_obj = m21_clef.TrebleClef() if voice.clef is Clef.SOL else m21_clef.BassClef()
        part.insert(0, m21_clef_obj)

        previous_compass: Compass | None = None
        for compass in piece.compasses:
            offset = offsets[compass.index]
            factor = self._quarterlength_factor_per_second(compass)
            is_compound = compass.formula.is_compound

            if previous_compass is None or compass.formula != previous_compass.formula:
                part.insert(
                    offset,
                    m21_meter.TimeSignature(f"{compass.formula.numerator}/{compass.formula.denominator}")
                )
            if previous_compass is None or compass.armor != previous_compass.armor:
                part.insert(offset, m21_key.KeySignature(compass.armor.accidents_qunatity))

            for note in voice.notes_on_interval(compass.begin_time, compass.end_time):
                if note.is_ornament:
                    #Adiada para a segunda passada: precisa do offset ja
                    #calculado da nota principal, que pode nao ter sido
                    #processada ainda nesta passada
                    pending_ornaments.append((note, offset, factor, is_compound))
                    continue

                raw_position = (note.onset - compass.begin_time) * factor
                note_offset = offset + self._round_to_grid_step(raw_position, config, is_compound)
                m21_note_obj = self._m21_note(note, factor, config, is_compound)
                note_map[id(note)] = m21_note_obj
                note_offsets[id(note)] = note_offset
                part.insert(note_offset, m21_note_obj)

            previous_compass = compass

        #Segunda passada: grace notes vao no mesmo offset da nota principal
        #(Voz.ornamento_de, Fase 12) - nunca deslocam as notas seguintes,
        #ja que nao ocupam quarterLength
        for note, fallback_offset, factor, is_compound in pending_ornaments:
            m21_note_obj = self._m21_note(note, factor, config, is_compound)
            note_map[id(note)] = m21_note_obj

            principal_offset = note_offsets.get(note.ornament_of)
            if principal_offset is None:
                #Nota principal nao encontrada (nao deveria acontecer em
                #uso normal) - usa a propria posicao quantizada da nota
                #como salvaguarda, para nao perder a nota silenciosamente
                compass = piece.compass_at_instant(note.onset)
                raw_position = (note.onset - compass.begin_time) * factor
                principal_offset = fallback_offset + self._round_to_grid_step(raw_position, config, is_compound)

            part.insert(principal_offset, m21_note_obj)

        part.makeNotation(inPlace=True)
        return part, note_map

    def _insert_feel_indications(self, part: m21_stream.Part, piece: Piece, offsets: dict[int, float]) -> None:
        measures_by_offset = {
            measure.offset: measure for measure in part.getElementsByClass(m21_stream.Measure)
        }
        for compass in piece.compasses:
            offset = offsets[compass.index]
            measure = measures_by_offset.get(offset)
            if measure is None:
                continue
            if compass.free_time:
                measure.insert(0.0, m21_expressions.TextExpression(FREE_TIME_TEXT))
            elif compass.feel_indication is not None:
                measure.insert(0.0, m21_expressions.TextExpression(compass.feel_indication))

    def _color_for_severity(self, level: SeverityLevel) -> str:
        return SEVERITY_COLORS[level]

    def _apply_visual_marking(
        self, note_map: dict[int, m21_note_module.Note], signalings: list[Signaling]
    ) -> None:
        for signaling in signalings:
            if signaling.note is None:
                continue
            m21_note_obj = note_map.get(id(signaling.note))
            if m21_note_obj is None:
                continue
            m21_note_obj.style.color = self._color_for_severity(signaling.level)
            m21_note_obj.noteheadParenthesis = True

    def _build_score(self, piece: Piece, config: Config) -> tuple[m21_stream.Score, dict[int, m21_note_module.Note]]:
        offsets = self._cumulative_offsets(piece)
        score = m21_stream.Score()
        combined_note_map: dict[int, m21_note_module.Note] = {}
        for voice in piece.voices:
            part, note_map = self._build_part(voice, piece, offsets, config)
            self._insert_feel_indications(part, piece, offsets)
            score.insert(0, part)
            combined_note_map.update(note_map)
        return score, combined_note_map