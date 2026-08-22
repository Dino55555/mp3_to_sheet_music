from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import Optional
from models.signaling import Signaling

@dataclass
class Note:
    pitch: int
    onset: float
    offset: float
    magnitude: float

    voice: Optional["Voice"] = None
    is_ornament: bool = False
    vocal_origin_identified: bool = False
    staccato: bool = False
    graphy: Optional[object] = None
    signal: Optional["Signaling"] = None

    raw_onset: Optional[float] = None
    raw_offset: Optional[float] = None

    reliability_existence: float = 1.0
    reliability_highness: float = 1.0
    reliability_duration: float = 1.0
    reliability_voice: float = 1.0

    def __post_init__(self) -> None:
        self._validate_temporal_pair(self.onset, self.offset)

    def _validate_temporal_pair(self, onset: float, offset: float) -> None:
        if offset <= onset:
            raise ValueError(
                f"Offset ({offset}) deve ser maior que onset ({onset})."
            )

    def redefine_time(self, onset: float, offset: float) -> None:
        #Atribui onset/offset juntos, atomicamente, validando o par completo
        #antes de aplicar - evita estados intermediarios invalidos que uma
        #atribuicao de campo isolada poderia produzir
        self._validate_temporal_pair(onset, offset)
        self.onset = onset
        self.offset = offset

    def duration(self) -> float:
        #Retorna a duração da nota
        return self.offset - self.onset

    def transpose(self, semitones: int) -> "Note":
        #Transpõe a nota em semitons
        self.pitch += semitones
        return self

    def overlap(self, other: "Note") -> bool:
        #Verifica se os intervalos das duas notas se sobrepõem
        return self.onset < other.offset and other.onset < self.offset

    def interval_in_semitones(self, other: "Note") -> int:
        #Retorna o valor do intervalo entre duas notas
        return abs(self.pitch - other.pitch)

    def clone(self) -> "Note":
        #Retorna uma cópia da nota
        return deepcopy(self)