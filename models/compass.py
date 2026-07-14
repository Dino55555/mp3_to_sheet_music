from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum


class TonalMode(Enum):
    MAJOR = "major"
    MINOR = "minor"


@dataclass
class TimeSignature:
    numerator: int
    denominator: int

    def __str__(self) -> str:
        return f"{self.numerator}/{self.denominator}"
    

@dataclass
class KeySignature:
    accidents_qunatity: int
    tonic: str
    mode: TonalMode


@dataclass
class Compass:
    index: int
    begin_time: float
    end_time: float
    formula: TimeSignature
    armor: KeySignature
    free_time: bool = False

    def has_time(self, time: float) -> bool:
        #Retorna True se o instante do tempo pertence ao compasso

        return (self.begin_time <= time < self.end_time)
    
    def duration(self) -> float:
        #Retorna a duração do compasso em segundos

        return self.end_time - self.begin_time
    
    def clone(self) -> "Compass":
        #Retorna uma cópia

        return deepcopy(self)
    

    def __post_init__(self):
        if self.numerator <= 0:
            raise ValueError("O numerador deve ser maior que zero")
        
        if self.denominator <= 0:
            raise ValueError("O denominador deve ser maior que 0")