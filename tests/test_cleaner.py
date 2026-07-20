import pytest
from cleaning.cleaner import(Cleaner, HARMONIC_PENALTY)
from config import Config
from orchestrator import Orchestrator
from tests.fixtures import (create_example_piece, create_piece_with_spurious_note)
from models.note import Note
from models.voice import Voice
from Compass.piece import Piece
from signaling.signaler import Signaler
from Compass.instrument import Instrument


def test_is_harmonic_detects_octave():
    cleaner = Cleaner()
    strong = Note(60, 0.0, 1.0, 1.0)
    weak = Note(72, 0.0, 1.0, 0.2)

    assert cleaner._is_harmonic_of(weak, strong)

def test_is_harmonic_detects_fifth():
    cleaner = Cleaner()
    strong = Note(60, 0.0, 1.0, 1.0)
    weak = Note(67, 0.0, 1.0, 0.2)

    assert cleaner._is_harmonic_of(weak, strong)

def test_is_harmonic_ignores_without_overlap():
    cleaner = Cleaner()
    strong = Note(60, 0.0, 1.0, 1.0)
    weak = Note(72, 2.0, 3.0, 0.2)

    assert not cleaner._is_harmonic_of(weak, strong)

def test_is_harmonic_ignores_independent_onsets():
    cleaner = Cleaner()
    strong = Note(60, 0.0, 1.0, 1.0)
    weak = Note(72, 0.2, 1.2, 0.2)

    assert not cleaner._is_harmonic_of(weak, strong)

def test_is_harmonic_ignores_other_intervals():
    cleaner = Cleaner()
    strong = Note(60, 0.0, 1.0, 1.0)
    weak = Note(65, 0.0, 1.0, 0.2)

    assert not cleaner._is_harmonic_of(weak, strong)

def test_mark_harmonics_reduces_only_weaker_note():
    cleaner = Cleaner()
    piece = create_piece_with_spurious_note()
    notes = piece.all_notes()
    weak = min(notes, key=lambda n: n.magnitude)
    strong = max(notes, key=lambda n: n.magnitude)
    cleaner._mark_harmonics(piece)

    assert weak.reliability_existence == HARMONIC_PENALTY
    assert strong.reliability_existence == 1.0

def test_process_removes_confirmed_harmonic():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece = create_piece_with_spurious_note()
    before = len(piece.all_notes())
    cleaner.process(piece, config, signaler)
    after = len(piece.all_notes())

    assert after == before - 1 

def test_process_keeps_independent_double():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    voice.add_note(Note(60, 0.0, 1.0, 1.0))
    voice.add_note(Note(72, 0.2, 1.2, 0.2))
    piece.add_voice(voice)
    cleaner.process(piece, config, signaler)

    assert len(piece.all_notes()) == 2

def test_process_removes_low_initial_confidence():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    voice.add_note(Note(60, 0.0, 1.0, 1.0, reliability_existence=0.2))
    piece.add_voice(voice)
    cleaner.process(piece, config, signaler)

    assert len(piece.all_notes()) == 0

def test_process_keeps_normal_notes():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece = create_example_piece()
    before = len(piece.all_notes())
    cleaner.process(piece, config, signaler)
    after = len(piece.all_notes())

    assert after == before

def test_process_empty_piece_changes_nothing():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    cleaner.process(piece, config, signaler)

    assert len(piece.all_notes()) == 0

def test_orchestrator_with_cleaner_matches_direct_processing():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece1 = create_piece_with_spurious_note()
    piece2 = create_piece_with_spurious_note()
    cleaner.process(piece1, config, signaler)
    orchestrator = Orchestrator(config, signaler)
    orchestrator.add_stage(cleaner)
    orchestrator.process(piece2)

    assert len(piece1.all_notes()) == len(piece2.all_notes())
