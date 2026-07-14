import pytest
from models.note import Note
from models.voice import Voice, PaperVoice, Clef


def test_add_note_keeps_order_out_of_order():
    voice = Voice()

    n1 = Note(60, 2.0, 3.0, 1.0)
    n2 = Note(62, 0.0, 1.0, 1.0)
    n3 = Note(64, 1.0, 2.0, 1.0)

    voice.add_note(n1)
    voice.add_note(n2)
    voice.add_note(n3)

    assert voice.notes == [n2, n3, n1]

def test_add_note_defines_voice_reference():
    voice = Voice()

    note = Note(60, 0.0, 1.0, 1.0)

    voice.add_note(note)
    
    assert note.voice is voice

def test_neighbour_returns_none_at_extremity():
    voice = Voice()

    n1 = Note(60, 0.0, 1.0, 1.0)
    n2 = Note(62, 1.0, 2.0, 1.0)
    n3 = Note(64, 2.0, 3.0, 1.0)

    voice.add_note(n1)
    voice.add_note(n2)
    voice.add_note(n3)

    prev, next = voice.neighbour(n1)

    assert prev is None
    assert next is n2

    prev, next = voice.neighbour(n3)

    assert prev is n2
    assert next is None

def text_neighbour_middle_note():
    voice = Voice()

    n1 = Note(60, 0.0, 1.0, 1.0)
    n2 = Note(62, 1.0, 2.0, 1.0)
    n3 = Note(64, 2.0, 3.0, 1.0)

    voice.add_note(n1)
    voice.add_note(n2)
    voice.add_note(n3)

    prev, next = voice.neighbour(n2)

    assert prev is n1
    assert next is n3

    def test_neighbour_non_existent():
        voice = Voice()

        note = Note(60, 0.0, 1.0, 1.0)

        with pytest.raises(ValueError):
            voice.neighbour(note)

    def test_notes_on_interval():
        voice = Voice()

        n1 = Note(60, 0.0, 1.0, 1.0)
        n2 = Note(62, 1.0, 2.0, 1.0)
        n3 = Note(64, 2.0, 3.0, 1.0)

        voice.add_note(n1)
        voice.add_note(n2)
        voice.add_note(n3)

        notes = voice.notes_on_interval(0.5, 2.5)

        assert notes == [n2, n3]

    def test_clef_and_none_on_undefined_paper():
        voice = Voice()

        assert voice.clef is None


    @pytest.mark.parametrize(
        "paper,expected_clef",
        [
            (PaperVoice.MELODY, Clef.SOL),
            (PaperVoice.ACCOMPANIMENT, Clef.FA)
        ]
    )

    def test_clef_derives_from_paper(paper, expected_clef):
        voice = Voice(paper=paper)

        assert voice.clef == expected_clef

    def test_clef_only_read():
        voice = Voice()

        with pytest.raises(AttributeError):
            voice.clef = Clef.SOL

    def test_clone_returns_copy():
        voice = Voice()

        note = Note(60, 0.0, 1.0, 1.0)

        voice.add_note(note)

        clone = voice.clone()

        assert clone == voice
        assert clone is not voice

        clone.notes[0].pitch = 72

        assert voice.notes[0].pitch == 60

    

