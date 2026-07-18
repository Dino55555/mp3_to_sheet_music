from __future__ import annotations
from models.note import Note
from models.signaling import(Signaling, SignalingCategory, SeverityLevel)


class Signaler:
    def __init__(self):
        self._signals: list[Signaling] = []
    
    def register    (
        self,
        category: SignalingCategory,
        level: SeverityLevel,
        description: str,
        compass_number: int,
        note: Note | None = None
    ) -> None:
        
        self._signals.append(
            Signaling(
                category=category,
                level=level,
                description=description,
                compass_number=compass_number,
                note=note
            )
        )

    
    def all(self) -> list[Signaling]:
        return list(self._signals)
    
    def ordered_report(self) -> list[Signaling]:
        return sorted(
            self._signals,
            key=lambda s: (s.level, s.compass_number)
        )
