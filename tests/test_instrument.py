from Compass.instrument import Instrument
from models.voice import Clef


def test_create_instrument_personalized():
    instrument = Instrument(
        name="Violino",
        range_min=55,
        range_max=103,
        clefs=[Clef.SOL]
    )

    assert instrument.name == "Violino"
    assert instrument.range_min == 55
    assert instrument.range_max == 103
    assert instrument.clefs == [Clef.SOL]

def test_instrument_piano_has_correct_range():
    piano = Instrument.piano()

    assert piano.name == "Piano"
    assert piano.range_min == 21
    assert piano.range_max == 108

def test_piano_has_correct_clefs():
    piano = Instrument.piano()

    assert piano.clefs == [Clef.SOL, Clef.FA]

def test_is_in_range_limits():
    piano = Instrument.piano()

    assert piano.is_in_range(21)
    assert piano.is_in_range(108)

    assert not piano.is_in_range(20)
    assert not piano.is_in_range(109)

def test_is_in_range_middle():
    piano = Instrument.piano()

    assert piano.is_in_range(60)
    assert piano.is_in_range(72)
    assert piano.is_in_range(88)