from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TonalMode(Enum):
    MAJOR = "major"
    MINOR = "minor"


@dataclass
class TimeSignature:
    numerator: int
    denominator: int
    is_compound: bool = False

    def __str__(self) -> str:
        return f"{self.numerator}/{self.denominator}"

    def beat_groups(self) -> int:
        return self.numerator // 3 if self.is_compound else self.numerator

    def convert_to_compound(self) -> "TimeSignature":
        return TimeSignature(
            numerator=self.numerator * 3,
            denominator=self.denominator * 2,
            is_compound=True,
        )
    

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
    feel_indication: Optional[str] = None

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
        if self.formula.numerator <= 0:
            raise ValueError("O numerador deve ser maior que zero")
        
        if self.formula.denominator <= 0:
            raise ValueError("O denominador deve ser maior que 0")