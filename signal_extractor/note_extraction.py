from __future__ import annotations
from basic_pitch.inference import predict
from models.note import Note
from models.voice import Voice
from Compass.instrument import Instrument
from Compass.piece import Piece


class NoteExtractor:
    #Nao implementa PipelineStage: e uma fonte, nao um estagio - produz a
    #primeira Peca em vez de receber uma ja existente

    def extract(self, audio_path: str) -> list[Note]:
        _, midi_data, _ = predict(audio_path)
        if not midi_data.instruments:
            return []
        return [self._note_from(midi_note) for midi_note in midi_data.instruments[0].notes]

    def _note_from(self, midi_note) -> Note:
        return Note(
            pitch=midi_note.pitch,
            onset=midi_note.start,
            offset=midi_note.end,
            magnitude=midi_note.velocity / 127.0,
        )


def build_initial_piece(notes: list[Note], instrument: Instrument) -> Piece:
    piece = Piece(instrument=instrument)
    voice = Voice()
    for note in notes:
        voice.add_note(note)
    piece.add_voice(voice)
    return piece