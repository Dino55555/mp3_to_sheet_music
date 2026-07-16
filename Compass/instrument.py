from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from models.voice import Clef


@dataclass
class Instrument:
    name: str
    range_min: int
    range_max: int
    clefs: list[Clef]


    def is_in_range(self, pitch: int) -> bool:
        return (self.range_min <= pitch <= self.range_max)
    

    @classmethod
    def piano(cls) -> "Instrument":
        return cls(
            name="Piano",
            range_min=21,
            range_max=108,
            clefs=[Clef.SOL, Clef.FA]
        )