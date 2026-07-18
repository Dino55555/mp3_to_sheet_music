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
    graphy: Optional[object] = None
    signal: Optional["Signaling"] = None

    reliability_existence: float = 1.0
    reliability_highness: float = 1.0
    reliability_duration: float = 1.0
    reliability_voice: float = 1.0

    def __post_init__(self) -> None:
        if self.offset <= self.onset:
            raise ValueError(
                f"Offset ({self.offset}) deve ser maior que onset ({self.onset})."
            )
    
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

