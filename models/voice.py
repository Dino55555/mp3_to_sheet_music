from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from models.note import Note

class PaperVoice(Enum):
    MELODY = "melodia"
    ACCOMPANIMENT = "accompaniment"


class Clef(Enum):
    SOL = "sol"
    FA = "fa"


@dataclass
class Voice:
    notes: list[Note] = field(default_factory=list)
    paper: Optional[PaperVoice] = None

    def add_note(self, note: Note) -> None:
        self.notes.append(note)
        self.notes.sort(key=lambda n: n.onset)

        #Mantém o vínculo bidirecional
        note.voice = self


    def neighbour(self, note: Note) -> tuple[Optional[Note], Optional[Note]]:
        if note not in self.notes:
            raise ValueError("A nota não pertence a esta voz")
        
        index = self.notes.index(note)

        prev = self.notes[index - 1] if index > 0 else None

        next = (
            self.notes[index + 1]
            if index < len(self.notes) - 1
            else None
        )

        return prev, next
    

    def notes_on_interval(self, begin: float, end: float) -> list[Note]:
        return [
            note
            for note in self.notes
            if begin <= note.onset < end
        ]
    

    @property
    def clef(self) -> Optional[clef]:
        if self.paper is PaperVoice.MELODY:
            return Clef.SOL
        
        if self.paper is PaperVoice.ACCOMPANIMENT:
            return Clef.FA
        
        return None
    

    def clone(self) -> "Voice":
        return deepcopy(self)