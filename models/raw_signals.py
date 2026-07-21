from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(slots=True)
class Beat:
    instant: float
    is_strong_beat: bool
    confidence: float

@dataclass(slots=True)
class RawSignals:
    beats: list[Beat] = field(default_factory=list)