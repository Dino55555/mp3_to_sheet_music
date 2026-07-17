import pytest
from models.voice import Voice
from models.note import Note
from models.compass import (KeySignature, TimeSignature, Compass, TonalMode)
from Compass.instrument import Instrument
from Compass.piece import Piece


def create_time_signature():
    return TimeSignature(4, 4)

def create_key_signature():
    return KeySignature(
        accidents_qunatity=0,
        tonic="C",
        mode=TonalMode.MAJOR
    )

def create_compass(index, begin, end):
    return Compass(
        index=index,
        begin_time=begin,
        end_time=end,
        formula=create_time_signature(),
        armor=create_key_signature()
    )

def create_piece():
    return Piece(instrument=Instrument.piano())


def test_add_compass_keeps_order():
    piece = create_piece()
    c3 = create_compass(3, 4.0, 6.0)
    c1 = create_compass(1, 0.0, 2.0)
    c2 = create_compass(2, 2.0, 4.0)
    piece.add_compass(c3)
    piece.add_compass(c1)
    piece.add_compass(c2)

    assert[c.index for c in piece.compasses] == [1, 2, 3]


def test_add_voice():
    piece = create_piece()
    voice = Voice()
    piece.add_voice(voice)

    assert len(piece.voices) == 1
    assert piece.voices[0] is voice


def test_compass_by_index_translates_1_for_list():
    piece = create_piece()
    c1 = create_compass(1, 0.0, 2.0)
    c2 = create_compass(2, 2.0, 4.0)
    piece.add_compass(c1)
    piece.add_compass(c2)

    assert piece.compass_by_index(1) is c1
    assert piece.compass_by_index(2) is c2

def test_compass_raises_error():
    piece = create_piece()
    
    with pytest.raises(
        ValueError,
        match="Compasso 1 não existe"
    ):
        piece.compass_by_index(1)

def test_all_notes_on_all_voices():
    piece = create_piece()
    voice1 = Voice()
    voice2 = Voice()
    n1 = Note(60, 0.0, 1.0, 0.8)
    n2 = Note(62, 1.0, 2.0, 0.8)
    n3 = Note(64, 2.0, 3.0, 0.8)
    voice1.add_note(n1)
    voice1.add_note(n2)
    voice2.add_note(n3)
    piece.add_voice(voice1)
    piece.add_voice(voice2)
    notes = piece.all_notes()

    assert len(notes) == 3
    assert n1 in notes
    assert n2 in notes
    assert n3 in notes

def test_notes_in_compass_crosses_voices_correctly():
    piece = create_piece()
    piece.add_compass(create_compass(1, 0.0, 2.0))
    piece.add_compass(create_compass(2, 2.0, 4.0))
    voice1 = Voice()
    voice2 = Voice()
    n1 = Note(60, 0.5, 1.5, 0.8)
    n2 = Note(62, 2.5, 3.0, 0.8)
    n3 = Note(64, 1.0, 1.8, 0.8)    
    n4 = Note(65, 3.2, 3.8, 0.8)  
    voice1.add_note(n1)
    voice1.add_note(n2)
    voice2.add_note(n3)
    voice2.add_note(n4)
    piece.add_voice(voice1)
    piece.add_voice(voice2)
    notes_compass_1 = piece.notes_in_compass(1)
    notes_compass_2 = piece.notes_in_compass(2)

    assert notes_compass_1 == [n1, n3]
    assert notes_compass_2 == [n2, n4]