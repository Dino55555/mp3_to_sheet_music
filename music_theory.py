from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from models.note import Note
from models.compass import (TonalMode, KeySignature)
from models.pitch_spelling import PitchSpelling

TIE_TOLERANCE_RELATIVE: float = 0.05

MAJOR_SCALE_STEPS: tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)
NATURAL_MINOR_SCALE_STEPS: tuple[int, ...] = (0, 2, 3, 5, 7, 8, 10)

TONIC_NAMES: tuple[str, ...] = (
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
)

# Círculo de quintas: quantidade de acidentes por tônica maior.
# Positivo = sustenidos, negativo = bemóis, zero = nenhum acidente
# (convenção MusicXML, fixada no Documento 7 da Fase 7).
# Índice 6 (Fá#/Solb) é o único empate exato do círculo (6 sustenidos
# vs. 6 bemóis); resolvido para o lado dos sustenidos (Fá#).
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
    5: -1,    # F
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
        #Soma a duração de cada nota no índice correspondente (pitch % 12)
        weights = [0.0] * 12
        for note in notes:
            weights[note.pitch % 12] += note.duration()
        return PitchClassHistogram(weights)


def most_likely_major_tonic(histogram: PitchClassHistogram) -> int:
    #Testa as 12 rotações da coleção diatônica maior contra o histograma
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


def choose_mode(
    histogram: PitchClassHistogram,
    major_tonic: int,
    last_significant_note: Optional[int],
) -> Optional[tuple[int, TonalMode]]:
    #Implementa B5+B7: pondera nota final e peso real da sensível elevada
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

    #Peso real da sensível no histograma - nunca presumido
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


# --- Fase 15: grafia de altura (C1/C4/C5) ---

NATURAL_PITCH_CLASS: dict[str, int] = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
}

SHARP_ORDER: tuple[str, ...] = ('F', 'C', 'G', 'D', 'A', 'E', 'B')
FLAT_ORDER: tuple[str, ...] = ('B', 'E', 'A', 'D', 'G', 'C', 'F')

#As 5 classes de altura "pretas", mapeadas para a letra natural imediatamente
#abaixo (uso em contexto ascendente / sem direção) e imediatamente acima
#(uso em contexto descendente)
SHARP_LETTER: dict[int, str] = {
    1: 'C', 3: 'D', 6: 'F', 8: 'G', 10: 'A',
}
FLAT_LETTER: dict[int, str] = {
    1: 'D', 3: 'E', 6: 'G', 8: 'A', 10: 'B',
}


def key_signature_alterations(key_signature: KeySignature) -> dict[str, int]:
    #As 7 letras com sua alteração conforme a quantidade de acidentes da armadura
    alterations = {letter: 0 for letter in NATURAL_PITCH_CLASS}
    quantity = key_signature.accidents_qunatity

    if quantity > 0:
        for letter in SHARP_ORDER[:quantity]:
            alterations[letter] = 1
    elif quantity < 0:
        for letter in FLAT_ORDER[:abs(quantity)]:
            alterations[letter] = -1

    return alterations


def diatonic_letter_for(pitch_class: int, alterations: dict[str, int]) -> Optional[str]:
    #Testa exatamente as 7 letras (nunca as 12 classes de altura diretamente)
    target = pitch_class % 12
    for letter, natural_class in NATURAL_PITCH_CLASS.items():
        if (natural_class + alterations.get(letter, 0)) % 12 == target:
            return letter
    return None


def spell_pitch(
    pitch: int, key_signature: KeySignature, melodic_direction: Optional[str]
) -> PitchSpelling:
    pitch_class = pitch % 12
    octave = pitch // 12 - 1
    alterations = key_signature_alterations(key_signature)

    letter = diatonic_letter_for(pitch_class, alterations)
    if letter is not None:
        return PitchSpelling(letter, alterations.get(letter, 0), octave)

    #C4/C5: nota cromática - direção melódica decide entre sustenido e bemol
    if melodic_direction == 'descending':
        letter = FLAT_LETTER[pitch_class]
        alteration = -1
    else:
        letter = SHARP_LETTER[pitch_class]
        alteration = 1

    return PitchSpelling(letter, alteration, octave)