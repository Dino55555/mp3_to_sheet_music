from __future__ import annotations
from dataclasses import dataclass, field
from models.compass import KeySignature
from Compass.instrument import Instrument

@dataclass(frozen=True)
class Config:
    instrument: Instrument = field(default_factory=Instrument.piano)
    sensivity: float = 0.5
    manual_key: KeySignature | None = None
    manual_bpm: float | None = None