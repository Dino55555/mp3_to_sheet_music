from __future__ import annotations
from models.note import Note
from models.voice import Voice
from Compass.piece import Piece
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)
from cleaning.cleaner import SHORT_NOTE_DURATION_THRESHOLD_SECONDS

OSCILLATION_MIN_SEQUENCE_LENGTH: int = 3
OSCILLATION_MAX_GAP_SECONDS: float = 0.05
OSCILLATION_MAX_RANGE_SEMITONES: int = 4


class VibratoDetector:
    #Roda entre DetectorEstrutural e SeparadorDeVozes: precisa de
    #compassos (para numero_do_compasso na sinalizacao) mas precisa
    #operar sobre a peca ainda como uma unica linha coerente, antes da
    #separacao em vozes - vibrato so faz sentido como conceito dentro de
    #uma melodia unica

    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        for voice in piece.voices:
            self._detect_oscillating_fragmentation(voice, piece, signaler)
        return piece

    def _detect_oscillating_fragmentation(self, voice: Voice, piece: Piece, signaler: Signaler) -> None:
        notes = voice.notes
        i = 0
        while i < len(notes):
            if notes[i].duration() >= SHORT_NOTE_DURATION_THRESHOLD_SECONDS:
                i += 1
                continue

            j = i
            while (
                j + 1 < len(notes)
                and notes[j + 1].duration() < SHORT_NOTE_DURATION_THRESHOLD_SECONDS
                and (notes[j + 1].onset - notes[j].offset) <= OSCILLATION_MAX_GAP_SECONDS
            ):
                j += 1

            group = notes[i:j + 1]
            if len(group) >= OSCILLATION_MIN_SEQUENCE_LENGTH:
                pitches = [n.pitch for n in group]
                pitch_range = max(pitches) - min(pitches)
                differences = [pitches[k + 1] - pitches[k] for k in range(len(pitches) - 1)]
                has_ascent = any(d > 0 for d in differences)
                has_descent = any(d < 0 for d in differences)

                #assinatura de oscilacao (vai e volta em torno de um
                #centro), nao de movimento (so sobe ou so desce) - a
                #distincao que uma regra pareada nao enxergaria
                if pitch_range <= OSCILLATION_MAX_RANGE_SEMITONES and has_ascent and has_descent:
                    first_note = group[0]
                    compass = piece.compass_at_instant(first_note.onset)
                    signaler.register(
                        SignalingCategory.POSSIBLE_VIBRATO_FRAGMENTATION,
                        SeverityLevel.VERIFY,
                        "Possível fragmentação por vibrato: sequência de notas curtas oscilando em torno de um centro",
                        compass.index,
                        first_note,
                    )

            i = j + 1