import pytest
from tests.fixtures import create_example_piece
from models.raw_signals import Beat
from structure.structural_detector import (StructuralDetector, COMPASS_SUSTAIN_LIMIT)
from models.compass import TimeSignature

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