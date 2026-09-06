from __future__ import annotations
from typing import Optional
from basic_pitch.inference import predict
from models.note import Note
from models.voice import Voice
from Compass.instrument import Instrument
from Compass.piece import Piece


class NoteExtractor:

    def extract(
        self,
        audio_path: str,
        onset_threshold: Optional[float] = None,
        frame_threshold: Optional[float] = None,
    ) -> list[Note]:
        #onset_threshold/frame_threshold: None preserva exatamente o
        #comportamento padrao da biblioteca (0.5/0.3) - so repassados
        #quando explicitamente fornecidos, para experimentos de
        #calibracao (Fase 19 nunca tocou nesses limiares; reaberto pela
        #evidencia real de baixa densidade de deteccao em material vocal
        #legato)
        predict_kwargs = {}
        if onset_threshold is not None:
            predict_kwargs['onset_threshold'] = onset_threshold
        if frame_threshold is not None:
            predict_kwargs['frame_threshold'] = frame_threshold

        _, midi_data, _ = predict(audio_path, **predict_kwargs)
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