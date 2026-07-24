from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from models.compass import TonalMode
from models.note import Note


TIE_TOLERANCE_RELATIVE: float = 0.05
MAJOR_SCALE_STEPS: tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)
NATURAL_MINOR_SCALE_STEPS: tuple[int, ...] = (0, 2, 3, 5, 7, 8, 10)
TONIC_NAMES: tuple[str, ...] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

#IMPORTANTE: 
#Positivo = sutenidos; negativo = bemóis;


_MAJOR_TONIC_ACCIDENTS: dict[int, int] = {
    0: 0,     # C
    7: 1,     # G
    2: 2,     # D
    9: 3,     # A
    4: 4,     # E
    11: 5,    # B
    6: 6,     # F#
    1: -5,    # Db
    8: -4,    # Ab
    3: -3,    # Eb
    10: -2,   # Bb
    5: -1,    # F,
}


@dataclass
class PitchClassHistogram:
    weights: list[float]

    def __post_init__(self) -> None:
        if len(self.weights) != 12:
            raise ValueError("O histograma deve ter exatamente 12 posições")

    def weight_of(self, pitch_class: int) -> float:
        return self.weights[pitch_class % 12]

    @staticmethod
    def from_notes(notes: list[Note]) -> "PitchClassHistogram":
        #Soma a duração de cada nota do índice correspondente
        weights = [0.0] * 12
        for note in notes:
            weights[note.pitch % 12] += note.duration()
        return PitchClassHistogram(weights)

def most_likely_major_tonic(histogram: PitchClassHistogram) -> int:
    best_tonic = 0
    best_score = -1.0
    for tonic in range(12):
        score = sum(
            histogram.weight_of(tonic + step)
            for step in MAJOR_SCALE_STEPS
        )
        if score > best_score:
            best_score = score
            best_tonic = tonic
    return best_tonic

def choose_mode(histogram: PitchClassHistogram, major_tonic: int, last_significant_note: Optional[int]) -> Optional[tuple[int, TonalMode]]:
    total_weight = sum(histogram.weights)
    minor_tonic = (major_tonic - 3) % 12
    raised_leading_tone = (minor_tonic + 11) % 12

    major_weight = 0.0
    minor_weight = 0.0

    if last_significant_note is not None:
        last_significant_note = last_significant_note % 12
        if last_significant_note == major_tonic:
            major_weight += total_weight
        elif last_significant_note == minor_tonic:
            minor_weight += total_weight

    minor_weight += histogram.weight_of(raised_leading_tone)
    if total_weight == 0.0:
        return None

    if abs(major_weight - minor_weight) < TIE_TOLERANCE_RELATIVE * total_weight:
        return None

    if major_weight > minor_weight:
        return (major_tonic, TonalMode.MAJOR)

    return (minor_tonic, TonalMode.MINOR)

def accidents_of_major_tonic(major_tonic: int) -> int:
    return _MAJOR_TONIC_ACCIDENTS[major_tonic % 12]