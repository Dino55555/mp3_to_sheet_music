import pytest
from completeness.completeness_detector import (
    CompletenessDetector,
    INFERRED_NOTE_EXISTENCE_CONFIDENCE,
)
from rhythm.rhythmic_grid import build_grid
from models.note import Note
from models.voice import Voice
from models.compass import (Compass, TimeSignature, KeySignature, TonalMode)
from Compass.piece import Piece
from Compass.instrument import Instrument
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)
from orchestrator import Orchestrator
from cleaning.cleaner import Cleaner
from structure.structural_detector import StructuralDetector
from voices.voice_separator import VoiceSeparator
from voices.octave_corrector import OctaveCorrector
from rhythm.quantizer import Quantizer
from models.raw_signals import RawSignals
from tests.fixtures import (
    voice_with_repeated_arpeggio_and_one_gap,
    voice_with_pattern_confirmed_once,
    voice_without_repetitive_pattern,
    regular_4_4_beats,
)


def test_compass_signature_maps_positions_correctly():
    detector = CompletenessDetector()
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)
    voice = Voice()
    n1 = Note(60, 0.0, 0.5, 0.8)
    n2 = Note(62, 1.0, 1.5, 0.8)
    n3 = Note(64, 2.0, 2.5, 0.8)
    voice.add_note(n1)
    voice.add_note(n2)
    voice.add_note(n3)

    signature = detector._compass_signature(compass, voice, 4)

    assert signature == {0: n1, 4: n2, 8: n3}

def test_patterns_match_identifies_single_gap():
    detector = CompletenessDetector()
    target = {0: Note(60, 0.0, 0.5, 0.8), 4: Note(62, 1.0, 1.5, 0.8)}
    neighbor = {
        0: Note(60, 0.0, 0.5, 0.8),
        4: Note(62, 1.0, 1.5, 0.8),
        8: Note(64, 2.0, 2.5, 0.8),
    }

    result = detector._patterns_match(target, neighbor)

    assert result == 8

def test_patterns_match_returns_none_with_more_than_one_gap():
    detector = CompletenessDetector()
    target = {0: Note(60, 0.0, 0.5, 0.8)}
    neighbor = {
        0: Note(60, 0.0, 0.5, 0.8),
        4: Note(62, 1.0, 1.5, 0.8),
        8: Note(64, 2.0, 2.5, 0.8),
    }

    assert detector._patterns_match(target, neighbor) is None

def test_patterns_match_returns_none_when_target_already_has_everything():
    detector = CompletenessDetector()
    target = {0: Note(60, 0.0, 0.5, 0.8), 4: Note(62, 1.0, 1.5, 0.8)}
    neighbor = {0: Note(60, 0.0, 0.5, 0.8), 4: Note(62, 1.0, 1.5, 0.8)}

    assert detector._patterns_match(target, neighbor) is None

def test_find_gap_candidates_ignores_neighbors_with_different_formula():
    detector = CompletenessDetector()
    piece = Piece(instrument=Instrument.piano())
    target_compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    other_compass = Compass(2, 4.0, 7.0, TimeSignature(3, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(target_compass)
    piece.add_compass(other_compass)
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(62, 1.0, 1.5, 0.8))
    voice.add_note(Note(60, 4.0, 4.5, 0.8))
    voice.add_note(Note(62, 5.0, 5.5, 0.8))
    voice.add_note(Note(64, 6.0, 6.5, 0.8))
    piece.add_voice(voice)

    candidates = detector._find_gap_candidates(target_compass, voice, piece, 4)

    assert candidates == []

def test_find_gap_candidates_ignores_free_time_neighbors():
    detector = CompletenessDetector()
    piece = Piece(instrument=Instrument.piano())
    target_compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    neighbor_compass = Compass(2, 4.0, 8.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR), free_time=True)
    piece.add_compass(target_compass)
    piece.add_compass(neighbor_compass)
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(62, 1.0, 1.5, 0.8))
    voice.add_note(Note(60, 4.0, 4.5, 0.8))
    voice.add_note(Note(62, 5.0, 5.5, 0.8))
    voice.add_note(Note(64, 6.0, 6.5, 0.8))
    piece.add_voice(voice)

    candidates = detector._find_gap_candidates(target_compass, voice, piece, 4)

    assert candidates == []

def test_find_gap_candidates_aggregates_confirmations_from_multiple_neighbors():
    detector = CompletenessDetector()
    piece = voice_with_repeated_arpeggio_and_one_gap()
    voice = piece.voices[0]
    target_compass = piece.compass_by_index(3)

    candidates = detector._find_gap_candidates(target_compass, voice, piece, 4)

    assert len(candidates) == 1
    position, model_note, confirmations = candidates[0]
    assert position == 8
    assert model_note.pitch == 64
    assert confirmations == 4

def test_create_inferred_note_preserves_model_duration():
    detector = CompletenessDetector()
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    grid = build_grid(compass, 4)
    model_note = Note(64, 10.0, 10.7, 0.8)

    inferred = detector._create_inferred_note(model_note, grid, 8)

    assert inferred.pitch == 64
    assert inferred.onset == pytest.approx(grid[8])
    assert inferred.offset == pytest.approx(grid[8] + 0.7)
    assert inferred.reliability_existence == INFERRED_NOTE_EXISTENCE_CONFIDENCE

def test_evaluate_compass_fills_with_high_confidence():
    detector = CompletenessDetector()
    signaler = Signaler()
    piece = voice_with_repeated_arpeggio_and_one_gap()
    voice = piece.voices[0]
    target_compass = piece.compass_by_index(3)
    before = len(voice.notes)

    detector._evaluate_compass(target_compass, voice, piece, 4, signaler)

    assert len(voice.notes) == before + 1
    inferred = next(n for n in voice.notes if n.onset == pytest.approx(10.0))
    assert inferred.pitch == 64
    assert inferred.reliability_existence == INFERRED_NOTE_EXISTENCE_CONFIDENCE

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.INFERRED_NOTE
    assert signals[0].level == SeverityLevel.INFORMATIONAL
    assert signals[0].note is inferred

def test_evaluate_compass_only_signals_with_low_confidence():
    detector = CompletenessDetector()
    signaler = Signaler()
    piece = voice_with_pattern_confirmed_once()
    voice = piece.voices[0]
    target_compass = piece.compass_by_index(1)
    before = len(voice.notes)

    detector._evaluate_compass(target_compass, voice, piece, 4, signaler)

    assert len(voice.notes) == before

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.POSSIBLE_MISSING_NOTE
    assert signals[0].level == SeverityLevel.VERIFY
    assert signals[0].note is None

def test_evaluate_compass_generates_no_candidate_without_repetitive_pattern():
    detector = CompletenessDetector()
    signaler = Signaler()
    piece = voice_without_repetitive_pattern()
    voice = piece.voices[0]
    before = len(voice.notes)

    for compass in piece.compasses:
        detector._evaluate_compass(compass, voice, piece, 4, signaler)

    assert len(voice.notes) == before
    assert signaler.all() == []

def test_inferred_note_is_inserted_respecting_voice_ordering():
    detector = CompletenessDetector()
    signaler = Signaler()
    piece = voice_with_repeated_arpeggio_and_one_gap()
    voice = piece.voices[0]
    target_compass = piece.compass_by_index(3)

    detector._evaluate_compass(target_compass, voice, piece, 4, signaler)

    onsets = [n.onset for n in voice.notes]
    assert onsets == sorted(onsets)

def test_orquestrador_completo_ate_aqui_integra_corretamente():
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()

    pitches = [60, 62, 64, 65]
    for measure_index in range(5):
        start = measure_index * 4.0
        for beat_index, pitch in enumerate(pitches):
            if measure_index == 2 and beat_index == 2:
                continue
            onset = start + beat_index * 1.0
            voice.add_note(Note(pitch, onset, onset + 1.0, 0.8))

    piece.add_voice(voice)
    piece.raw_signals = RawSignals(regular_4_4_beats(5))

    orchestrator = Orchestrator(config, signaler)
    orchestrator.add_stage(Cleaner())
    orchestrator.add_stage(StructuralDetector())
    orchestrator.add_stage(VoiceSeparator())
    orchestrator.add_stage(OctaveCorrector())
    orchestrator.add_stage(Quantizer())
    orchestrator.add_stage(CompletenessDetector())
    result = orchestrator.process(piece)

    assert result is piece
    total_notes = len(result.all_notes())
    assert total_notes == 20

    inferred_candidates = [
        n for n in result.all_notes()
        if n.reliability_existence == INFERRED_NOTE_EXISTENCE_CONFIDENCE
    ]
    assert len(inferred_candidates) == 1
    assert inferred_candidates[0].pitch == 64

    inferred_signals = [
        s for s in signaler.all()
        if s.category == SignalingCategory.INFERRED_NOTE
    ]
    assert len(inferred_signals) == 1