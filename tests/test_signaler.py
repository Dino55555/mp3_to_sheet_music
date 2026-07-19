from signaling.signaler import Signaler
from models.signaling import (SignalingCategory, SeverityLevel)


def test_signaler_starts_empty():
    signaler = Signaler()

    assert signaler.all() == []

def test_register_adds_signaling():
    signaler = Signaler()
    signaler.register(
        SignalingCategory.INFERRED_NOTE,
        SeverityLevel.VERIFY,
        "Nota inferida",
        2
    )
    signals = signaler.all()

    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.INFERRED_NOTE
    assert signals[0].level == SeverityLevel.VERIFY
    assert signals[0].description == "Nota inferida"
    assert signals[0].compass_number == 2

def test_all_returns_copy_not_internal_list():
    signaler = Signaler()
    signaler.register(
        SignalingCategory.INFERRED_NOTE,
        SeverityLevel.VERIFY,
        "Teste",
        1
    )
    copy = signaler.all()
    copy.clear()

    assert len(copy) == 0
    assert len(signaler.all()) == 1

def test_ordered_report_prioritizes_requires_decision():
    signaler = Signaler()
    signaler.register(
        SignalingCategory.INFERRED_NOTE,
        SeverityLevel.INFORMATIONAL,
        "",
        1
    )
    signaler.register(
        SignalingCategory.IMPOSSIBLE_PASSAGE,
        SeverityLevel.REQUIRES_DECISION,
        "",
        5
    )
    signaler.register(
        SignalingCategory.LOW_CONFIDENCE_QUANTIZATION,
        SeverityLevel.VERIFY,
        "",
        3
    )
    report = signaler.ordered_report()

    assert report[0].level == SeverityLevel.REQUIRES_DECISION
    assert report[1].level == SeverityLevel.VERIFY
    assert report[2].level == SeverityLevel.INFORMATIONAL

def test_ordered_report_breaks_ties_by_compass():
    signaler = Signaler()
    signaler.register(
        SignalingCategory.INFERRED_NOTE,
        SeverityLevel.VERIFY,
        "",
        5
    )
    signaler.register(
        SignalingCategory.AMBIGUOUS_KEY,
        SeverityLevel.VERIFY,
        "",
        2
    )
    signaler.register(
        SignalingCategory.POSSIBLE_MISSING_NOTE,
        SeverityLevel.VERIFY,
        "",
        8
    )

    report = signaler.ordered_report()

    assert report[0].compass_number == 2
    assert report[1].compass_number == 5
    assert report[2].compass_number == 8

def test_ordered_report_empty_signaler_returns_empty_list():
    signaler = Signaler()

    assert signaler.ordered_report() == []
    


