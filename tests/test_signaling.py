import pytest
from models.note import Note
from models.signaling import (Signaling, SignalingCategory, SeverityLevel)


def test_severity_level():
    assert SeverityLevel.REQUIRES_DECISION < SeverityLevel.VERIFY
    assert SeverityLevel.VERIFY < SeverityLevel.INFORMATIONAL
    assert sorted(
        [
            SeverityLevel.INFORMATIONAL,
            SeverityLevel.REQUIRES_DECISION,
            SeverityLevel.VERIFY
        ]
    ) == [
        SeverityLevel.REQUIRES_DECISION,
        SeverityLevel.VERIFY,
        SeverityLevel.INFORMATIONAL
    ]

def test_signaling_stores_all_fields():
    note = Note(60, 0.0, 1.0, 0.8)
    signaling = Signaling(
        category=SignalingCategory.INFERRED_NOTE,
        level=SeverityLevel.VERIFY,
        description="Nota inferida",
        compass_number=3,
        note=note
    )

    assert signaling.category == SignalingCategory.INFERRED_NOTE
    assert signaling.level == SeverityLevel.VERIFY
    assert signaling.description == "Nota inferida"
    assert signaling.compass_number == 3
    assert signaling.note is note

def test_signaling_note_is_optimal():
    signaling = Signaling(
        category=SignalingCategory.AMBIGUOUS_KEY,
        level=SeverityLevel.INFORMATIONAL,
        description="Tonalidade ambígua",
        compass_number=8
    )

    assert signaling.note is None
