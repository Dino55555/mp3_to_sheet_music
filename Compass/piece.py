from __future__ import annotations
from dataclasses import dataclass, field
from models.compass import Compass
from models.voice import Voice
from Compass.instrument import Instrument
from models.note import Note


@dataclass
class Piece:
    instrument: Instrument
    compasses: list[Compass] = field(default_factory=list)
    voices: list[Voice] = field(default_factory=list)

    def add_compass(self, compass: Compass) -> None:
        #Adicionar compasso mantendo lista ordenada pelo índice
        self.compasses.append(compass)
        self.compasses.sort(key=lambda c: c.index)

    def add_voice(self, voice: Voice) -> None:
        #Adicionar uma voz à peça
        self.voices.append(voice)

    def compass_by_index(self, index: int) -> Compass:
        #Retorna o compasso do dado índice
        for compass in self.compasses:
            if compass.index == index:
                return compass
            
        raise ValueError(f"Compasso {index} não existe")
    
    def all_notes(self) -> list[Note]:
        #Retorna todas as notas
        notes = []
        for voice in self.voices:
            notes.extend(voice.notes)

        return notes
    
    def notes_in_compass(self, index: int) -> list[Note]:
        #Retorna as notas de um compasso
        compass = self.compass_by_index(index)

        return [
            note 
            for note in self.all_notes()
            if compass.has_time(note.onset)
            ]
    
    def summary(self) -> str:
        total_notes = len(self.all_notes())

        return (
            f"Peça: {self.instrument.name}, "
            f"{len(self.compasses)} compassos, "
            f"{len(self.voices)} voz(es), "
            f"{total_notes} notas"
        )