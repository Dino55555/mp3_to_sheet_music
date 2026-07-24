import pytest
from cleaning.cleaner import(Cleaner, HARMONIC_PENALTY)
from config import Config
from orchestrator import Orchestrator
from tests.fixtures import (create_example_piece, create_piece_with_spurious_note, create_piece_with_isolated_chromatic_note)
from models.note import Note
from models.voice import Voice
from models.compass import TonalMode
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

def test_estimate_rough_tonality_does_not_generate_signaling():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece = create_example_piece()
    cleaner.process(piece, config, signaler)

    assert signaler.all() == []

def test_is_out_of_key_detects_chromatic_note():
    cleaner = Cleaner()
    in_key_note = Note(60, 0.0, 0.5, 0.8)      # C, pertence a Do maior
    chromatic_note = Note(61, 0.0, 0.5, 0.8)   # C#, fora de Do maior

    assert not cleaner._is_out_of_key(in_key_note, 0, TonalMode.MAJOR)
    assert cleaner._is_out_of_key(chromatic_note, 0, TonalMode.MAJOR)

def test_is_isolated_without_melodic_connection_true_and_false():
    cleaner = Cleaner()
    voice = Voice()
    connected = Note(61, 0.5, 0.6, 0.8)   # a 1 semitom da vizinha
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(connected)
    voice.add_note(Note(72, 0.6, 1.0, 0.8))   # distante (12 semitons)

    voice2 = Voice()
    isolated = Note(90, 2.0, 2.5, 0.8)
    voice2.add_note(isolated)

    assert cleaner._is_isolated_without_melodic_connection(connected, voice) is False
    assert cleaner._is_isolated_without_melodic_connection(isolated, voice2) is True

def test_process_removes_isolated_note_out_of_key():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece = create_piece_with_isolated_chromatic_note()
    before = len(piece.all_notes())
    cleaner.process(piece, config, signaler)
    after = len(piece.all_notes())

    assert after == before - 1

def test_process_keeps_note_out_of_key_but_connected_by_step():
    cleaner = Cleaner()
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    voice.add_note(Note(60, 0.00, 0.50, 0.8))   # C
    voice.add_note(Note(62, 0.50, 1.00, 0.8))   # D
    voice.add_note(Note(61, 1.00, 1.08, 0.8))   # C# curta, fora da tonalidade, mas a 1 semitom de D
    voice.add_note(Note(64, 1.08, 1.58, 0.8))   # E
    voice.add_note(Note(67, 1.58, 2.08, 0.8))   # G
    piece.add_voice(voice)
    before = len(piece.all_notes())
    cleaner.process(piece, config, signaler)
    after = len(piece.all_notes())

    assert after == before