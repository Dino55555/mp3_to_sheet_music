import pytest
from tests.fixtures import (create_example_piece, create_piece_with_spurious_note, regular_4_4_beats)
from models.raw_signals import (Beat, RawSignals)
from config import Config
from structure.structural_detector import (StructuralDetector, COMPASS_SUSTAIN_LIMIT)
from models.compass import (Compass, TimeSignature, KeySignature, TonalMode)
from orchestrator import Orchestrator
from cleaning.cleaner import Cleaner
from signaling.signaler import Signaler

def test_group_into_cadidates_measures_splits_correctly():
    detector = StructuralDetector()
    beats = [
        Beat(0.0, True, 1.0),
        Beat(1.0, False, 1.0),
        Beat(2.0, False, 1.0),
        Beat(3.0, False, 1.0),
        Beat(4.0, True, 1.0),
        Beat(5.0, False, 1.0),
        Beat(6.0, False, 1.0),
        Beat(7.0, False, 1.0),
        Beat(8.0, True, 1.0)
    ]
    groups = detector._group_candidate_measures(beats)

    assert len(groups) == 2
    assert len(groups[0]) == 4
    assert len(groups[1]) == 4
    assert groups[0][0].is_strong_beat is True
    assert groups[1][0].is_strong_beat is True

def test_formula_from_group_counts_beats():
    detector = StructuralDetector()
    group = [
        Beat(0.0, True, 1.0),
        Beat(1.0, False, 1.0),
        Beat(2.0, False, 1.0),
        Beat(3.0, False, 1.0)
    ]
    formula = detector._formula_from_group(group)

    assert formula.numerator == 4
    assert formula.denominator == 4

def test_group_is_free_time_detects_predominantly_low_confidence():
    detector = StructuralDetector()
    group = [
        Beat(0.0, True, 0.2),
        Beat(1.0, False, 0.3),
        Beat(2.0, False, 0.2),
        Beat(3.0, False, 0.9)
    ]

    assert detector._group_is_free_time(group)

def test_group_is_free_time_ignores_single_bad_beat():
    detector = StructuralDetector()
    group = [
        Beat(0.0, True, 1.0),
        Beat(1.0, False, 1.0),
        Beat(2.0, False, 0.2),
        Beat(3.0, False, 1.0)
    ]

    assert detector._group_is_free_time(group) is False

def test_resolve_formula_changes_keeps_formula_for_isolated_exception():
    detector = StructuralDetector()
    formulas = [
        TimeSignature(4, 4),
        TimeSignature(2, 4),
        TimeSignature(4, 4),
        TimeSignature(4, 4)
    ]
    free_flags = [False, False, False, False]
    resolved = detector._resolve_formula_changes(formulas, free_flags)

    assert resolved[0] == TimeSignature(4, 4)
    assert resolved[1] == TimeSignature(4, 4)
    assert resolved[2] == TimeSignature(4, 4)
    assert resolved[3] == TimeSignature(4, 4)

def test_resolve_formla_changes_adopts_formula_after_sustain():
    detector = StructuralDetector()
    formulas = [
        TimeSignature(4, 4),
        TimeSignature(3, 4),
        TimeSignature(3, 4),
        TimeSignature(3, 4)
    ]
    free_flags = [False, False, False, False]
    resolved = detector._resolve_formula_changes(formulas, free_flags)

    assert resolved[0] == TimeSignature(4, 4)
    assert resolved[1] == TimeSignature(3, 4)
    assert resolved[2] == TimeSignature(3, 4)
    assert resolved[3] == TimeSignature(3, 4)

def test_resolve_formula_changes_free_time_as_evidence():
    detector = StructuralDetector()
    formulas = [
        TimeSignature(4, 4),
        TimeSignature(3, 4),
        TimeSignature(3, 4),
        TimeSignature(4, 4)
    ]
    free_flags = [False, True, True, False]
    resolved = detector._resolve_formula_changes(formulas, free_flags)

    assert resolved[0] == TimeSignature(4, 4)
    assert resolved[1] == TimeSignature(4, 4)
    assert resolved[2] == TimeSignature(4, 4)
    assert resolved[3] == TimeSignature(4, 4)

def test_resolve_formula_changes_keeps_formula_for_isolated_exception():
    detector = StructuralDetector()
    raw_formulas = [
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(2, 4),
        TimeSignature(4, 4),
        TimeSignature(4, 4)
    ]
    free_time = [False] * 5
    resolved = detector._resolve_formula_changes(raw_formulas, free_time)

    assert resolved == [
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(4, 4)
    ]

def test_resolve_formula_changes_accepts_after_sustained_change():
    detector = StructuralDetector()
    raw_formulas = [
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(3, 4),
        TimeSignature(3, 4),
        TimeSignature(3, 4)
    ]
    free_time = [False] * 5
    resolved = detector._resolve_formula_changes(raw_formulas, free_time)

    assert resolved == [
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(3, 4),
        TimeSignature(3, 4),
        TimeSignature(3, 4)
    ]

def test_resolve_formula_changes_ignores_free_time_groups():
    detector = StructuralDetector()
    raw_formulas = [
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(3, 4),
        TimeSignature(3, 4),
        TimeSignature(4, 4)
    ]
    free_time = [False, False, True, True, False]
    resolved = detector._resolve_formula_changes(raw_formulas, free_time)

    assert resolved == [
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(4, 4),
        TimeSignature(4, 4)
    ]

def test_build_measures_calculates_end_from_next_start():
        detector = StructuralDetector()
        groups = [
            [
                Beat(0.0, True, 1.0),
                Beat(1.0, False, 1.0),
                Beat(2.0, False, 1.0),
                Beat(3.0, False, 1.0)
            ],
            [
                Beat(4.0, True, 1.0),
                Beat(5.0, False, 1.0),
                Beat(6.0, False, 1.0),
                Beat(7.0, False, 1.0)
            ]
        ]
        formulas = [
            TimeSignature(4, 4),
            TimeSignature(4, 4)
        ]
        free_time = [False, False]
        measures = detector._build_measures(groups, formulas, free_time)

        assert measures[0].begin_time == 0.0
        assert measures[0].end_time == 4.0

def test_build_measures_extrapolates_last_measure_end():
    detector = StructuralDetector()
    groups = [
        [
            Beat(0.0, True, 1.0),
            Beat(1.0, False, 1.0),
            Beat(2.0, False, 1.0),
            Beat(3.0, False, 1.0)
        ]
    ]
    formulas = [TimeSignature(4, 4)]
    free_time = [False]
    measures = detector._build_measures(groups, formulas, free_time)

    assert measures[0].begin_time == 0.0
    assert measures[0].end_time == 4.0

def test_build_measures_uses_neutral_placeholder_key():
    detector = StructuralDetector()
    groups = [
        [
            Beat(0.0, True, 1.0),
            Beat(1.0, False, 1.0),
            Beat(2.0, False, 1.0),
            Beat(3.0, False, 1.0)
        ]
    ]
    formulas = [TimeSignature(4, 4)]
    free_time = [False]
    measures = detector._build_measures(groups, formulas, free_time)

    assert measures[0].armor == KeySignature(0, "C", TonalMode.MAJOR)

def test_detect_pickup_inserts_partial_measure_at_start():
    detector = StructuralDetector()
    piece = create_example_piece()
    #primeira nota que vai começar antes do primeiro compass
    piece.all_notes()[0].onset = -0.5
    measures = [
        Compass(
            1,
            0.0,
            4.0,
            TimeSignature(4, 4),
            KeySignature(0, "C", TonalMode.MAJOR),
            False
        )
    ]
    adjusted = detector._detect_and_adjust_pickup(piece, measures)

    assert len(adjusted) == 2
    assert adjusted[0].begin_time == -0.5
    assert adjusted[0].end_time == 0.0

def test_detect_pickup_shortens_last_measure_by_same_amount():
    detector = StructuralDetector()
    piece = create_example_piece()
    piece.all_notes()[0].onset = -0.5
    measures = [
        Compass(
            1,
            0.0,
            4.0,
            TimeSignature(4, 4),
            KeySignature(0, "C", TonalMode.MAJOR),
            False
        )
    ]
    adjusted = detector._detect_and_adjust_pickup(piece, measures)

    assert adjusted[-1].end_time == 3.5

def test_detect_pickup_does_nothing_when_no_pickup():
    detector = StructuralDetector()
    piece = create_example_piece()
    measures = [
        Compass(
            1,
            0.0,
            4.0,
            TimeSignature(4, 4),
            KeySignature(0, "C", TonalMode.MAJOR),
            False
        )
    ]
    adjusted = detector._detect_and_adjust_pickup(piece, measures)

    assert adjusted == measures
    assert len(adjusted) == 1
    assert adjusted[0].begin_time == 0.0
    assert adjusted[0].end_time == 4.0

def test_process_raises_error_without_raw_signals():
    detector = StructuralDetector()
    piece = create_example_piece()
    config = Config()
    signaler = Signaler()

    with pytest.raises(ValueError):
        detector.process(piece, config, signaler)

def test_process_raises_error_with_empty_raw_signals():
    detector = StructuralDetector()
    piece = create_example_piece()
    piece.raw_signals = RawSignals()
    config = Config()
    signaler = Signaler()

    with pytest.raises(ValueError):
        detector.process(piece, config, signaler)

def test_orchestrator_with_cleaner_and_structural_detector_integrates_correctly():
    config = Config()
    signaler = Signaler()
    piece = create_piece_with_spurious_note()
    piece.raw_signals = RawSignals(regular_4_4_beats(2))
    orchestrator = Orchestrator(config, signaler)
    orchestrator.add_stage(Cleaner())
    orchestrator.add_stage(StructuralDetector())
    result = orchestrator.process(piece)

    assert result is piece
    assert len(result.all_notes()) == 1
    assert len(result.compasses) == 2
    assert result.compasses[0].formula == TimeSignature(4, 4)
    assert result.compasses[1].formula == TimeSignature(4, 4)
    assert result.compasses[0].free_time is False
    assert result.compasses[1].free_time is False

