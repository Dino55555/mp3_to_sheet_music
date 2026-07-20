from __future__ import annotations
from models.note import Note
from Compass.piece import Piece
from config import Config
from signaling.signaler import Signaler

HARMONIC_INTERVALS: tuple[int, int] = (7, 12)
HARMONIC_PENALTY: float = 0.2
TIME_TOLERANCE: float = 0.05


class Cleaner:

    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        #executa a limpeza da peça
        self._mark_harmonics(piece)
        self._remove_low_confidence_notes(piece, config.sensivity)
        return piece
    
    def _mark_harmonics(self, piece: Piece) -> None:
        #Marca notas que aparentam ser harmônicos
        notes = piece.all_notes()
        for i in range(len(notes)):
            for j in range(len(notes)):
                if i == j:
                    continue

                candidate = notes[i]
                other = notes[j]
                if self._is_harmonic_of(candidate, other):
                    candidate.reliability_existence = HARMONIC_PENALTY
    
    def _is_harmonic_of(self, candidate: Note, other: Note) -> bool:
        #Verifica se a nota candidata parece ser um harmônico da outra nota

        if not candidate.overlaps(other):
            return False
        
        interval = candidate.interval_in_semitones(other)
        if interval not in HARMONIC_INTERVALS:
            return False
    
        if candidate.magnitude >= other.magnitude:
            return False
        
        if (abs(candidate.onset - other.onset) > TIME_TOLERANCE):
            return False
        
        if (abs(candidate.offset - other.offset) > TIME_TOLERANCE):
            return False
        
        return True
    
    def _remove_low_confidence_notes(self, piece: Piece, threshold: float) -> None:
        #remove as notas com baixa confiabilidade
        for voice in piece.voices:
            voice.notes = [
                note 
                for note in voice.notes
                if note.reliability_existence >= threshold
            ]