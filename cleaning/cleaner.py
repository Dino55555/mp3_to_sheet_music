from __future__ import annotations
from models.note import Note
from models.voice import Voice
from models.compass import TonalMode
from Compass.piece import Piece
from config import Config
from signaling.signaler import Signaler
from music_theory import (PitchClassHistogram, most_likely_major_tonic, choose_mode, MAJOR_SCALE_STEPS, NATURAL_MINOR_SCALE_STEPS)

HARMONIC_INTERVALS: tuple[int, int] = (7, 12)
HARMONIC_PENALTY: float = 0.2
TIME_TOLERANCE: float = 0.05
SHORT_NOTE_DURATION_THRESHOLD_SECONDS: float = 0.15


class Cleaner:

    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        #executa a limpeza da peça
        self._mark_harmonics(piece)

        all_notes = piece.all_notes()
        tonic, mode = self._estimate_rough_tonality(all_notes)
        for voice in piece.voices:
            for note in voice.notes:
                if note.duration() >= SHORT_NOTE_DURATION_THRESHOLD_SECONDS:
                    continue
                if not self._is_out_of_key(note, tonic, mode):
                    continue
                if not self._is_isolated_without_melodic_connection(note, voice):
                    continue
                note.reliability_existence = HARMONIC_PENALTY

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

        if not candidate.overlap(other):
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

    def _estimate_rough_tonality_(self, notes: list[Note]) -> tuple[int, TonalMode]:
        histogram = PitchClassHistogram.from_notes(notes)
        major_tonic = most_likely_major_tonic(histogram)
        last_note_pitch = notes[-1].pitch if notes else None
        result = choose_mode(histogram, major_tonic, last_note_pitch)
        if result is None:
            return (0, TonalMode.MAJOR)
        return result

    def _is_out_of_key(self, note: Note, tonic: int, mode: TonalMode) -> bool:
        scale_steps = (MAJOR_SCALE_STEPS if mode is TonalMode.MAJOR else NATURAL_MINOR_SCALE_STEPS)
        degree = (note.pitch - tonic) % 12

        return degree not in scale_steps

    def _is_isolated_without_melodic_connection(self, note: Note, voice: Voice) -> bool:
        #True quando nehuma nota vizinha esta a 1 ou 2 semitons de distancia
        previous, following = voice.neighbour(note)

        close_to_previous = (previous is not None and note.interval_in_semitones(previous) in (1, 2))
        close_to_following = (following is not None and note.interval_in_semitones(following) in (1, 2))

        return not (close_to_previous or close_to_following)        