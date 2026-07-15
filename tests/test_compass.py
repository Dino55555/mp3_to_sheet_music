import pytest
from models.compass import (KeySignature, Compass, TimeSignature, TonalMode)


def create_formula() -> TimeSignature:
    return TimeSignature(4, 4)


def create_key() -> KeySignature:
    return KeySignature(accidents_qunatity=0, tonic="C", mode=TonalMode.MAJOR)


def create_compass() -> Compass:
    return Compass(index=1, begin_time=0.0, end_time=2.0, formula=create_formula(), armor=create_key())


def test_create_compass():
    compass = create_compass()

    assert compass.index == 1
    assert compass.begin_time == 0.0
    assert compass.end_time == 2.0
    assert compass.formula == create_formula()
    assert compass.armor == create_key()
    assert compass.free_time is False


def test_time_signature_str_formats_as_fraction():
    formula = TimeSignature(6, 8)

    assert str(formula) == "6/8"


@pytest.mark.parametrize(
    "time,expected",
    [
    (0.0, True),
    (1.0, True),
    (1.9999, True),
    (2.0, False),
    (-0.1, False),
    (2.1, False)
    ]
)


def test_has_instant_includes_begin_excluds_end(time, expected):
    compass = create_compass()

    assert compass.has_time(time) is expected


def test_duration():
    compass = create_compass()

    assert compass.duration() == pytest.approx(2.0)


def test_clone_returns_copy():
    original = create_compass()
    clone = original.clone()

    assert clone == original
    assert clone is not original

    clone.index = 5
    clone.formula.numerator = 3
    clone.armor.tonic = "G"

    assert original.index == 1
    assert original.formula.numerator == 4
    assert original.armor.tonic == "C"


def test_free_tempo_false():
    compass = create_compass()

    assert compass.free_time is False


def test_mode_tonal_major():
    keysignature = KeySignature(
        accidents_qunatity=2,
        tonic="D",
        mode=TonalMode.MAJOR,
    )

    assert keysignature.mode is TonalMode.MAJOR


def test_tonal_mode_minor():
    keysignature = KeySignature(
        accidents_qunatity=3,
        tonic="A",
        mode=TonalMode.MINOR
    )

    assert keysignature.mode is TonalMode.MINOR
