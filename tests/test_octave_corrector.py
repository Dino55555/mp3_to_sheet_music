import pytest
from voices.octave_corrector import (
    OctaveCorrector,
    OCTAVE_TOLERANCE_SEMITONES,
    CONTOUR_WINDOW_SIZE,
    STEPWISE_MOTION_THRESHOLD_SEMITONES,
    CENTER_DISTANCE_THRESHOLD_SEMITONES,
    CONFIDENCE_AFTER_CORRECTION,
)
from voices.voice_separator import VoiceSeparator
from models.note import Note
from models.voice import (Voice, PaperVoice)
from Compass.piece import Piece
from Compass.instrument import Instrument
from config import Config
from signaling.signaler import Signaler
from orchestrator import Orchestrator
from cleaning.cleaner import Cleaner
from structure.structural_detector import StructuralDetector
from models.raw_signals import RawSignals
from tests.fixtures import (
    octave_leap_isolated_voice,
    sustained_octave_leap_voice,
    accompaniment_with_note_off_center,
    accompaniment_with_consistent_open_voicing,
    voice_with_note_isolated_out_of_range,
    regular_4_4_beats,
)


def test_simultaneous_of_ignores_the_note_itself():
    voice = Voice()
    a = Note(60, 0.0, 1.0, 0.8)
    b = Note(64, 0.0, 1.0, 0.8)
    voice.add_note(a)
    voice.add_note(b)

    result = voice.simultaneous_of(a)

    assert a not in result
    assert result == [b]

def test_simultaneous_of_returns_empty_without_overlap():
    voice = Voice()
    a = Note(60, 0.0, 1.0, 0.8)
    b = Note(64, 1.0, 2.0, 0.8)
    voice.add_note(a)
    voice.add_note(b)

    assert voice.simultaneous_of(a) == []
    assert voice.simultaneous_of(b) == []

def test_contour_window_respects_configured_size():
    corrector = OctaveCorrector()
    voice = Voice()
    pitches = [60, 62, 64, 66, 68]
    onset = 0.0
    for pitch in pitches:
        voice.add_note(Note(pitch, onset, onset + 0.5, 0.8))
        onset += 0.5

    window = corrector._contour_window(voice, 2)

    assert [n.pitch for n in window] == [60, 62, 66, 68]
    assert len(window) == 2 * CONTOUR_WINDOW_SIZE

def test_contour_window_at_voice_extremities():
    corrector = OctaveCorrector()
    voice = Voice()
    pitches = [60, 62, 64, 66, 68]
    onset = 0.0
    for pitch in pitches:
        voice.add_note(Note(pitch, onset, onset + 0.5, 0.8))
        onset += 0.5

    window = corrector._contour_window(voice, 0)

    assert [n.pitch for n in window] == [62, 64]

def test_correct_implausible_leap_corrects_isolated_peak():
    corrector = OctaveCorrector()
    voice = octave_leap_isolated_voice()
    target = voice.notes[3]
    assert target.pitch == 76

    corrector._correct_implausible_leap(voice)

    assert target.pitch == 64
    assert target.reliability_highness == CONFIDENCE_AFTER_CORRECTION

def test_correct_implausible_leap_keeps_sustained_leap():
    corrector = OctaveCorrector()
    voice = sustained_octave_leap_voice()
    target = voice.notes[3]
    assert target.pitch == 76

    corrector._correct_implausible_leap(voice)

    assert target.pitch == 76
    assert target.reliability_highness == 1.0

def test_correct_implausible_leap_ignores_contour_already_with_large_jumps():
    corrector = OctaveCorrector()
    voice = Voice()
    pitches = [38, 40, 64, 76, 65, 67]
    onset = 0.0
    for pitch in pitches:
        voice.add_note(Note(pitch, onset, onset + 0.5, 0.8))
        onset += 0.5
    target = voice.notes[3]

    corrector._correct_implausible_leap(voice)

    assert target.pitch == 76
    assert target.reliability_highness == 1.0

def test_correct_accompaniment_register_corrects_isolated_note_off_center():
    corrector = OctaveCorrector()
    voice = accompaniment_with_note_off_center()
    outlier = voice.notes[3]
    assert outlier.pitch == 72

    corrector._correct_accompaniment_register(voice)

    assert outlier.pitch == 60
    assert outlier.reliability_highness == CONFIDENCE_AFTER_CORRECTION
    #as demais notas do primeiro acorde nao foram tocadas
    assert {n.pitch for n in voice.notes[:3]} == {40, 43, 47}

def test_correct_accompaniment_register_keeps_consistent_open_voicing():
    corrector = OctaveCorrector()
    voice = accompaniment_with_consistent_open_voicing()
    original_pitches = [n.pitch for n in voice.notes]

    corrector._correct_accompaniment_register(voice)

    assert [n.pitch for n in voice.notes] == original_pitches

def test_correct_accompaniment_register_does_not_run_on_melody_voice():
    corrector = OctaveCorrector()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice(paper=PaperVoice.MELODY)
    voice.add_note(Note(40, 0.0, 1.0, 0.8))
    voice.add_note(Note(43, 0.0, 1.0, 0.8))
    voice.add_note(Note(47, 0.0, 1.0, 0.8))
    voice.add_note(Note(72, 0.0, 1.0, 0.8))
    piece.add_voice(voice)

    corrector.process(piece, Config(), Signaler())

    outlier = [n for n in piece.all_notes() if n.onset == 0.0 and n.pitch == 72]
    assert len(outlier) == 1

def test_correct_out_of_range_adjusts_isolated_note():
    corrector = OctaveCorrector()
    voice = voice_with_note_isolated_out_of_range()
    instrument = Instrument.piano()
    target = voice.notes[1]
    assert target.pitch == 15

    corrector._correct_out_of_range(voice, instrument)

    assert target.pitch == 27
    assert instrument.is_in_range(target.pitch)
    assert target.reliability_highness == CONFIDENCE_AFTER_CORRECTION

def test_correct_out_of_range_adjusts_by_multiple_octaves_if_needed():
    corrector = OctaveCorrector()
    voice = Voice()
    voice.add_note(Note(30, 0.0, 0.5, 0.8))
    voice.add_note(Note(3, 0.5, 1.0, 0.8))
    voice.add_note(Note(32, 1.0, 1.5, 0.8))
    instrument = Instrument.piano()
    target = voice.notes[1]

    corrector._correct_out_of_range(voice, instrument)

    assert target.pitch == 27
    assert instrument.is_in_range(target.pitch)

def test_correct_out_of_range_keeps_sustained_pattern():
    corrector = OctaveCorrector()
    voice = Voice()
    voice.add_note(Note(10, 0.0, 0.5, 0.8))
    voice.add_note(Note(12, 0.5, 1.0, 0.8))
    voice.add_note(Note(14, 1.0, 1.5, 0.8))
    instrument = Instrument.piano()
    original_pitches = [n.pitch for n in voice.notes]

    corrector._correct_out_of_range(voice, instrument)

    assert [n.pitch for n in voice.notes] == original_pitches

def test_all_corrections_set_maximum_pitch_confidence():
    corrector = OctaveCorrector()
    instrument = Instrument.piano()

    leap_voice = octave_leap_isolated_voice()
    corrector._correct_implausible_leap(leap_voice)
    assert leap_voice.notes[3].reliability_highness == CONFIDENCE_AFTER_CORRECTION

    accompaniment_voice = accompaniment_with_note_off_center()
    corrector._correct_accompaniment_register(accompaniment_voice)
    assert accompaniment_voice.notes[3].reliability_highness == CONFIDENCE_AFTER_CORRECTION

    range_voice = voice_with_note_isolated_out_of_range()
    corrector._correct_out_of_range(range_voice, instrument)
    assert range_voice.notes[1].reliability_highness == CONFIDENCE_AFTER_CORRECTION

def test_orchestrator_complete_so_far_integrates_correctly():
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    pitches = [60, 62, 64, 76, 65, 67]
    onset = 0.0
    for pitch in pitches:
        voice.add_note(Note(pitch, onset, onset + 0.5, 0.8))
        onset += 0.5
    piece.add_voice(voice)
    piece.raw_signals = RawSignals(regular_4_4_beats(1))

    orchestrator = Orchestrator(config, signaler)
    orchestrator.add_stage(Cleaner())
    orchestrator.add_stage(StructuralDetector())
    orchestrator.add_stage(VoiceSeparator())
    orchestrator.add_stage(OctaveCorrector())
    result = orchestrator.process(piece)

    assert result is piece
    assert len(result.voices) == 2
    melody_voice = next(v for v in result.voices if v.paper is PaperVoice.MELODY)
    accompaniment_voice = next(v for v in result.voices if v.paper is PaperVoice.ACCOMPANIMENT)

    assert accompaniment_voice.notes == []
    assert [n.pitch for n in melody_voice.notes] == [60, 62, 64, 64, 65, 67]
    assert melody_voice.notes[3].reliability_highness == CONFIDENCE_AFTER_CORRECTION