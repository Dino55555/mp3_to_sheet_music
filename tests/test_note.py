import pytest

from models.note import Note


def test_creation_with_obrigatory_mandatory_inputs():
    note = Note(
        pitch = 60,
        onset = 0.0,
        offset = 1.5,
        magnitude = 0.8
    )

    assert note.pitch == 60
    assert note.onset == 0.0
    assert note.offset == 1.5
    assert note.magnitude == 0.8


def test_optional_inputs():
    note = Note(60, 0.0, 1.0, 0.9)

    assert note.voice is None
    assert note.graphy is None
    assert note.signal is None
    assert note.is_ornament is False

    assert note.reliability_existence == 1.0
    assert note.reliability_highness == 1.0
    assert note.reliability_duration == 1.0
    assert note.reliability_voice == 1.0


def test_duration_calc():
    note = Note(60, 1.2, 3.8, 0.9)

    assert note.duration() == pytest.approx(2.6)


def test_transpose_sum_positive_semitones():
    note = Note(60, 0, 1, 1)

    note.transpose(5)

    assert note.pitch == 65


def test_transpose_sum_negative_semitones():
    note = Note(60, 0, 1, 1)

    note.transpose(-7)    

    assert note.pitch == 53


def test_transpose_return():
    note = Note(60, 0, 1, 1)

    ret = note.transpose(2)

    assert ret is note


def test_overlap_true():
    n1 = Note(60, 0.0, 2.0, 1.0)
    n2 = Note(64, 1.5, 3.0, 1.0)

    assert n1.overlap(n2)
    assert n2.overlap(n1)


def test_overlap_false():
    n1 = Note(60, 0.0, 1.0, 1.0)
    n2 = Note(64, 2.0, 3.0, 1.0)

    assert not n1.overlap(n2)

def test_overlap_limit_case():
    n1 = Note(60, 0.0, 1.0, 1.0)
    n2 = Note(64, 1.0, 2.0, 1.0)

    assert not n1.overlap(n2)
    assert not n2.overlap(n1)


def test_interval_semitones():
    n1 = Note(60, 0, 1, 1)
    n2 = Note(67, 0, 1, 1)

    assert n1.interval_in_semitones(n2) == 7
    assert n2.interval_in_semitones(n1) == 7


def test_clone():
    original = Note(60, 0, 1, 0.8)
    clone = original.clone()

    clone.pitch = 72
    clone.voice = object()

    assert original.pitch == 60
    assert original.voice is None


@pytest.mark.parametrize(
    "onset,offset",
    [
        (1.0, 1.0),
        (2.0, 1.5)
    ]
    )


def test_offset_lower_than_onset(onset, offset):
    with pytest.raises(ValueError, match="Offset .* deve ser maior que onset"):
        Note(
            pitch=60,
            onset=onset,
            offset=offset,
            magnitude=1.0
        )