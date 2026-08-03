from __future__ import annotations
from dataclasses import dataclass


@dataclass
class PitchSpelling:
    letter_class: str
    alteration: int
    octave: int