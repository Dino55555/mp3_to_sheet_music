from __future__ import annotations
from models.note import Note
from signal_extractor.separation import SourceSeparator
from signal_extractor.note_extraction import NoteExtractor


def extract_notes_from_mix(audio_path: str, temp_directory: str) -> list[Note]:
    vocal_path, instrumental_path = SourceSeparator().separate(audio_path, temp_directory)

    extractor = NoteExtractor()
    vocal_notes = extractor.extract(vocal_path)
    instrumental_notes = extractor.extract(instrumental_path)

    for note in vocal_notes:
        note.vocal_origin_identified = True

    combined = vocal_notes + instrumental_notes
    combined.sort(key=lambda note: note.onset)
    return combined