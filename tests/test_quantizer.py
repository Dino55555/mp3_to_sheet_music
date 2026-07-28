import pytest
from rhythm.quantizer import (
    Quantizer,
    SMALL_THRESHOLD_FRACTION,
    AMBIGUITY_TOLERANCE_FRACTION,
    MODERATE_DEVIATION_CONFIDENCE,
    AMBIGUOUS_TIME_CONFIDENCE,
)
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
from models.raw_signals import RawSignals
from tests.fixtures import (
    note_with_small_deviation,
    note_with_ambiguous_deviation,
    note_with_moderate_deviation,
    long_note_crossing_measure,
    regular_4_4_beats,
)


def _single_measure_piece() -> Piece:
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(
        index=1,
        begin_time=0.0,
        end_time=4.0,
        formula=TimeSignature(4, 4),
        armor=KeySignature(0, "C", TonalMode.MAJOR),
    )
    piece.add_compass(compass)
    return piece


def test_compass_at_instant_finds_correct_compass():
    piece = Piece(instrument=Instrument.piano())
    compass1 = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    compass2 = Compass(2, 4.0, 8.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass1)
    piece.add_compass(compass2)

    assert piece.compass_at_instant(5.5) is compass2
    assert piece.compass_at_instant(1.0) is compass1

def test_compass_at_instant_edge_case_end_of_last_compass():
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)

    assert piece.compass_at_instant(4.0) is compass

def test_compass_at_instant_raises_error_outside_any_compass():
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)

    with pytest.raises(ValueError):
        piece.compass_at_instant(10.0)

def test_build_grid_has_correct_number_of_points():
    quantizer = Quantizer()
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))

    grid = quantizer._build_grid(compass, 4)

    assert len(grid) == 4 * 4 + 1

def test_build_grid_includes_both_extremes():
    quantizer = Quantizer()
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))

    grid = quantizer._build_grid(compass, 4)

    assert grid[0] == pytest.approx(0.0)
    assert grid[-1] == pytest.approx(4.0)

def test_two_closest_identifies_correct_pair():
    quantizer = Quantizer()
    grid = [0.0, 1.0, 2.0, 3.0, 4.0]

    closest, second_closest = quantizer._two_closest(2.7, grid)

    assert closest == 3
    assert second_closest == 2

@pytest.mark.parametrize("index_in_grid,divisions,expected_level", [
    (0, 4, 3),
    (4, 4, 3),
    (8, 4, 3),
    (2, 4, 1),
    (1, 4, 0),
    (3, 4, 0),
])
def test_metric_level_beat_is_simpler_than_subdivision(index_in_grid, divisions, expected_level):
    quantizer = Quantizer()

    assert quantizer._metric_level(index_in_grid, divisions) == expected_level

def test_quantize_instant_small_deviation_adjusts_silently():
    quantizer = Quantizer()
    piece, note = note_with_small_deviation()

    quantized, confidence, ambiguous = quantizer._quantize_instant(note.onset, piece, 4)

    assert quantized == pytest.approx(0.25)
    assert confidence == 1.0
    assert ambiguous is False

def test_quantize_instant_ambiguous_deviation_chooses_higher_metric_level():
    quantizer = Quantizer()
    piece, note = note_with_ambiguous_deviation()

    quantized, confidence, ambiguous = quantizer._quantize_instant(note.onset, piece, 4)

    #o tempo (0.0) tem nivel metrico maior que a subdivisao vizinha (0.25)
    assert quantized == pytest.approx(0.0)
    assert confidence == AMBIGUOUS_TIME_CONFIDENCE
    assert ambiguous is True

def test_quantize_instant_moderate_deviation_without_signaling():
    quantizer = Quantizer()
    piece, note = note_with_moderate_deviation()

    quantized, confidence, ambiguous = quantizer._quantize_instant(note.onset, piece, 4)

    assert quantized == pytest.approx(0.25)
    assert confidence == MODERATE_DEVIATION_CONFIDENCE
    assert ambiguous is False

def test_quantize_note_confidence_is_minimum_of_onset_and_offset():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = _single_measure_piece()
    #onset com desvio pequeno (confianca 1.0), offset ambiguo (confianca 0.3)
    note = Note(60, 0.23, 3.13, 0.8)

    quantizer._quantize_note(note, piece, 4, signaler)

    assert note.reliability_duration == AMBIGUOUS_TIME_CONFIDENCE

def test_quantize_note_generates_at_most_one_signal():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = _single_measure_piece()
    #onset e offset ambos ambiguos
    note = Note(60, 0.13, 1.13, 0.8)

    quantizer._quantize_note(note, piece, 4, signaler)

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.LOW_CONFIDENCE_QUANTIZATION
    assert signals[0].level == SeverityLevel.VERIFY

def test_quantize_note_offset_in_different_compass_than_onset():
    quantizer = Quantizer()
    signaler = Signaler()
    piece, note = long_note_crossing_measure()

    quantizer._quantize_note(note, piece, 4, signaler)

    assert note.onset == pytest.approx(3.5)
    assert note.offset == pytest.approx(4.75)
    assert note.reliability_duration == 1.0
    assert signaler.all() == []

def test_orchestrator_complete_so_far_integrates_correctly():
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()

    pitches = [60, 62, 64, 65, 67, 69]
    base_onset = 0.0
    for pitch in pitches:
        #cada nota deslocada +0.02s do grid pretendido (desvio pequeno, B9)
        onset = base_onset + 0.02
        offset = base_onset + 0.5 + 0.02
        voice.add_note(Note(pitch, onset, offset, 0.8))
        base_onset += 0.5

    piece.add_voice(voice)
    piece.raw_signals = RawSignals(regular_4_4_beats(1))

    orchestrator = Orchestrator(config, signaler)
    orchestrator.add_stage(Cleaner())
    orchestrator.add_stage(StructuralDetector())
    orchestrator.add_stage(VoiceSeparator())
    orchestrator.add_stage(OctaveCorrector())
    orchestrator.add_stage(Quantizer())
    result = orchestrator.process(piece)

    assert result is piece
    all_notes = sorted(result.all_notes(), key=lambda n: n.onset)
    assert len(all_notes) == 6

    expected_onset = 0.0
    for note in all_notes:
        assert note.onset == pytest.approx(expected_onset)
        assert note.offset == pytest.approx(expected_onset + 0.5)
        assert note.reliability_duration == 1.0
        expected_onset += 0.5

    quantization_signals = [
        s for s in signaler.all()
        if s.category == SignalingCategory.LOW_CONFIDENCE_QUANTIZATION
    ]
    assert quantization_signals == []