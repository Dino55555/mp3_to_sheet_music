from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.note import Note


class SignalingCategory(Enum):
    INFERRED_NOTE = "inferred_note"
    POSSIBLE_MISSING_NOTE = "possible_missing_note"
    AMBIGUOUS_KEY = "ambiguous_key"
    LOW_CONFIDENCE_QUANTIZATION = "low_confidence_quantization"
    UNRESOLVED_COUNTERPOINT = "unresolved_counterpoint"
    IMPOSSIBLE_PASSAGE = "impossible_passage"
    FREE_TIME_APPROXIMATION = "free_time_approximation"

class SeverityLevel(IntEnum):
    REQUIRES_DECISION = 0
    VERIFY = 1
    INFORMATIONAL = 2


@dataclass
class Signaling:
    category: SignalingCategory
    level: SeverityLevel
    description: str
    compass_number: int
    note: "Note | None" = None
    