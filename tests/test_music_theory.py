import pytest
from models.note import Note
from models.compass import TonalMode
from music_theory import (PitchClassHistogram, most_likely_major_tonic, choose_mode, accidents_of_major_tonic)
from tests.fixtures import (notes_in_d_major, notes_in_a_minor_natural, notes_in_c_mixolydian)


def test_histogram_from_notes_weighs_by_duration():
    notes = [
        Note(60, 0.0, 1.0, 0.8),   # C, duracao 1.0
        Note(60, 1.0, 1.5, 0.8),   # C, duracao 0.5 (mesma classe)
        Note(64, 0.0, 0.3, 0.8),   # E, duracao 0.3
    ]
    histogram = PitchClassHistogram.from_notes(notes)

    assert histogram.weight_of(0) == pytest.approx(1.5)
    assert histogram.weight_of(4) == pytest.approx(0.3)
    assert histogram.weight_of(7) == pytest.approx(0.0)

def test_most_likely_major_tonic_identifies_d_major():
    notes = notes_in_d_major()
    histogram = PitchClassHistogram.from_notes(notes)

    assert most_likely_major_tonic(histogram) == 2

def test_most_likely_major_tonic_identifies_f_major_for_mixolydian_content():
    notes = notes_in_c_mixolydian()
    histogram = PitchClassHistogram.from_notes(notes)

    assert most_likely_major_tonic(histogram) == 5


@pytest.mark.parametrize("tonic,expected_accidents",
                         [
                            (0, 0),     # C
                            (7, 1),     # G
                            (2, 2),     # D
                            (9, 3),     # A
                            (4, 4),     # E
                            (11, 5),    # B
                            (6, 6),     # F#
                            (1, -5),    # Db
                            (8, -4),    # Ab
                            (3, -3),    # Eb
                            (10, -2),   # Bb
                            (5, -1),    # F
                         ])

def test_accidents_of_major_tonic_covers_the_12_tonics(tonic, expected_accidents):
    assert accidents_of_major_tonic(tonic) == expected_accidents

def test_choose_mode_identifies_major_by_final_note():
    histogram = PitchClassHistogram([0.0] * 12)
    histogram.weights[0] = 5.0
    histogram.weights[4] = 5.0
    histogram.weights[7] = 5.0

    result = choose_mode(histogram, major_tonic=0, last_significant_note=60)

    assert result == (0, TonalMode.MAJOR)

def test_choose_mode_identifies_minor_by_final_note():
    notes = notes_in_a_minor_natural()
    histogram = PitchClassHistogram.from_notes(notes)
    major_tonic = most_likely_major_tonic(histogram)
    last_note_pitch = notes[-1].pitch

    result = choose_mode(histogram, major_tonic, last_note_pitch)

    assert result == (9, TonalMode.MINOR)

def test_choose_mode_reinforces_minor_with_leading_tone_present():
    histogram = PitchClassHistogram([0.0] * 12)
    histogram.weights[8] = 5.0 # G# -> A minor

    result = choose_mode(histogram, 0, None)

    assert result == (9, TonalMode.MINOR)

def test_choose_mode_does_not_force_absent_leading_tone_to_major():
    notes = notes_in_a_minor_natural()
    histogram = PitchClassHistogram.from_notes(notes)

    assert histogram.weight_of(8) == 0.0

    result = choose_mode(histogram, 0, 69)

    assert result == (9, TonalMode.MINOR)

def test_choose_mode_returns_none_on_tie():
    histogram = PitchClassHistogram([0.0] * 12)
    histogram.weights[8] = 10.0 

    result = choose_mode(histogram, 0, 60)

    assert result is None

