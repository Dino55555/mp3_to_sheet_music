import pytest
from voices.voice_separator import (
    VoiceSeparator,
    SMALL_INTERVAL_THRESHOLD_SEMITONES,
    RHYTHMIC_VARIETY_THRESHOLD,
    PATTERN_REPETITION_THRESHOLD,
    HIGH_SCORE_THRESHOLD,
)
from models.note import Note
from models.voice import (Voice, PaperVoice, Clef)
from Compass.piece import Piece
from Compass.instrument import Instrument
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)
from orchestrator import Orchestrator
from cleaning.cleaner import Cleaner
from structure.structural_detector import StructuralDetector
from models.raw_signals import RawSignals
from tests.fixtures import (
    notes_clear_melody_over_accompaniment,
    notes_melody_temporarily_descending,
    notes_ambiguous_counterpoint,
    notes_with_marked_vocal_origin,
    regular_4_4_beats,
)


def test_classify_by_register_isolated_note_becomes_melody():
    separator = VoiceSeparator()
    note = Note(60, 0.0, 1.0, 0.8)

    melody, accompaniment = separator._classify_by_register([note])

    assert melody == [note]
    assert accompaniment == []

def test_classify_by_register_highest_note_in_group_becomes_melody():
    separator = VoiceSeparator()
    low = Note(60, 0.0, 1.0, 0.8)
    mid = Note(64, 0.0, 1.0, 0.8)
    high = Note(67, 0.0, 1.0, 0.8)

    melody, accompaniment = separator._classify_by_register([low, mid, high])

    assert melody == [high]
    assert accompaniment == [low, mid]

def test_average_interval_calculates_mean_of_jumps():
    separator = VoiceSeparator()
    notes = [
        Note(60, 0.0, 1.0, 0.8),
        Note(64, 1.0, 2.0, 0.8),
        Note(67, 2.0, 3.0, 0.8),
        Note(60, 3.0, 4.0, 0.8),
    ]

    result = separator._average_interval(notes)

    assert result == pytest.approx(14 / 3)

def test_rhythmic_variety_high_with_diverse_durations():
    separator = VoiceSeparator()
    notes = [
        Note(60, 0.0, 0.2, 0.8),
        Note(60, 0.2, 1.7, 0.8),
        Note(60, 1.7, 2.0, 0.8),
        Note(60, 2.0, 4.0, 0.8),
    ]

    result = separator._rhythmic_variety(notes)

    assert result > RHYTHMIC_VARIETY_THRESHOLD

def test_rhythmic_variety_low_with_uniform_durations():
    separator = VoiceSeparator()
    notes = [
        Note(60, 0.0, 1.0, 0.8),
        Note(60, 1.0, 2.0, 0.8),
        Note(60, 2.0, 3.0, 0.8),
        Note(60, 3.0, 4.0, 0.8),
    ]

    result = separator._rhythmic_variety(notes)

    assert result == pytest.approx(0.0)

def test_pattern_repetition_high_in_repeated_arpeggio():
    separator = VoiceSeparator()
    notes = [
        Note(60, 0.0, 0.5, 0.8),
        Note(64, 0.5, 1.0, 0.8),
        Note(60, 1.0, 1.5, 0.8),
        Note(64, 1.5, 2.0, 0.8),
        Note(60, 2.0, 2.5, 0.8),
        Note(64, 2.5, 3.0, 0.8),
    ]

    result = separator._pattern_repetition(notes)

    assert result == pytest.approx(1.0)
    assert result > PATTERN_REPETITION_THRESHOLD

def test_pattern_repetition_low_in_non_repetitive_sequence():
    separator = VoiceSeparator()
    notes = [
        Note(60, 0.0, 0.3, 0.8),
        Note(63, 0.3, 0.9, 0.8),
        Note(58, 0.9, 1.8, 0.8),
        Note(70, 1.8, 2.2, 0.8),
        Note(65, 2.2, 3.7, 0.8),
        Note(72, 3.7, 4.0, 0.8),
    ]

    result = separator._pattern_repetition(notes)

    assert result < PATTERN_REPETITION_THRESHOLD
    assert result == pytest.approx(0.2)


@pytest.mark.parametrize(
    "interval_low,variety_high,repetition_high,expected_score",
    [
        (False, False, False, 0.0),
        (True, False, False, 1.0),
        (False, True, False, 1.0),
        (False, False, True, -1.0),
        (True, True, False, 2.0),
        (True, False, True, 0.0),
        (False, True, True, 0.0),
        (True, True, True, 1.0),
    ],
)
def test_melodic_score_sums_the_three_signals_correctly(
    monkeypatch, interval_low, variety_high, repetition_high, expected_score
):
    separator = VoiceSeparator()
    dummy_flow = [Note(60, 0.0, 1.0, 0.8), Note(62, 1.0, 2.0, 0.8)]

    monkeypatch.setattr(
        separator, "_average_interval",
        lambda flow: 1.0 if interval_low else 10.0
    )
    monkeypatch.setattr(
        separator, "_rhythmic_variety",
        lambda flow: 0.5 if variety_high else 0.1
    )
    monkeypatch.setattr(
        separator, "_pattern_repetition",
        lambda flow: 0.8 if repetition_high else 0.2
    )

    score = separator._melodic_score(dummy_flow)

    assert score == pytest.approx(expected_score)

def test_resolve_by_contour_confirms_a4_candidature():
    separator = VoiceSeparator()
    signaler = Signaler()
    notes = notes_melody_temporarily_descending()
    melody_candidates, accompaniment_candidates = separator._classify_by_register(notes)

    #A4 misclassifica o mergulho: a nota grave da melodia foi parar em
    #acompanhamento, e o acorde agudo daquele instante foi parar em melodia
    assert 48 in [n.pitch for n in accompaniment_candidates]
    assert 68 in [n.pitch for n in melody_candidates]

    resolved_melody, resolved_accompaniment = separator._resolve_by_contour(
        melody_candidates, accompaniment_candidates, signaler
    )

    #mesmo assim, o fluxo agregado de A4 nao e invertido por A5
    assert resolved_melody == melody_candidates
    assert resolved_accompaniment == accompaniment_candidates
    assert signaler.all() == []

def test_resolve_by_contour_inverts_when_contour_contradicts_register():
    separator = VoiceSeparator()
    signaler = Signaler()

    #candidata a melodia por A4: estatica/repetitiva (pontuacao baixa)
    melody_candidates = [
        Note(80, 0.0, 1.0, 0.8),
        Note(80, 1.0, 2.0, 0.8),
        Note(80, 2.0, 3.0, 0.8),
        Note(80, 3.0, 4.0, 0.8),
    ]
    #candidata a acompanhamento por A4: contorno melodico real (pontuacao alta)
    accompaniment_candidates = [
        Note(60, 0.0, 0.5, 0.8),
        Note(62, 1.0, 2.0, 0.8),
        Note(61, 2.0, 2.75, 0.8),
        Note(63, 3.0, 4.25, 0.8),
    ]

    resolved_melody, resolved_accompaniment = separator._resolve_by_contour(
        melody_candidates, accompaniment_candidates, signaler
    )

    assert resolved_melody == accompaniment_candidates
    assert resolved_accompaniment == melody_candidates
    assert signaler.all() == []

def test_resolve_by_contour_does_not_invert_without_clear_winner_below_threshold():
    #Caso-limite mencionado no documento: diferenca de pontuacao existe, mas
    #nenhuma das duas atinge LIMIAR_PONTUACAO_ALTA - nao deveria inverter
    separator = VoiceSeparator()
    signaler = Signaler()

    melody_candidates = [
        Note(72, 0.0, 1.0, 0.8),
        Note(74, 1.0, 2.0, 0.8),
        Note(72, 2.0, 3.0, 0.8),
        Note(74, 3.0, 4.0, 0.8),
    ]
    accompaniment_candidates = [
        Note(60, 0.0, 1.0, 0.8),
        Note(60, 1.0, 2.0, 0.8),
        Note(60, 2.0, 3.0, 0.8),
    ]

    melody_score = separator._melodic_score(melody_candidates)
    accompaniment_score = separator._melodic_score(accompaniment_candidates)
    assert melody_score < HIGH_SCORE_THRESHOLD
    assert accompaniment_score < HIGH_SCORE_THRESHOLD

    resolved_melody, resolved_accompaniment = separator._resolve_by_contour(
        melody_candidates, accompaniment_candidates, signaler
    )

    assert resolved_melody == melody_candidates
    assert resolved_accompaniment == accompaniment_candidates
    assert signaler.all() == []

def test_resolve_by_contour_signals_unresolved_counterpoint_when_both_high():
    separator = VoiceSeparator()
    signaler = Signaler()
    notes = notes_ambiguous_counterpoint()
    melody_candidates, accompaniment_candidates = separator._classify_by_register(notes)

    assert separator._melodic_score(melody_candidates) >= HIGH_SCORE_THRESHOLD
    assert separator._melodic_score(accompaniment_candidates) >= HIGH_SCORE_THRESHOLD

    resolved_melody, resolved_accompaniment = separator._resolve_by_contour(
        melody_candidates, accompaniment_candidates, signaler
    )

    #candidatura crua de A4 e mantida, nao ha excecao nao tratada
    assert resolved_melody == melody_candidates
    assert resolved_accompaniment == accompaniment_candidates

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.UNRESOLVED_COUNTERPOINT
    assert signals[0].level == SeverityLevel.REQUIRES_DECISION

def test_resolve_by_contour_with_empty_list_changes_nothing():
    separator = VoiceSeparator()
    signaler = Signaler()
    accompaniment_candidates = [Note(60, 0.0, 1.0, 0.8)]

    resolved_melody, resolved_accompaniment = separator._resolve_by_contour(
        [], accompaniment_candidates, signaler
    )

    assert resolved_melody == []
    assert resolved_accompaniment == accompaniment_candidates
    assert signaler.all() == []

def test_apply_vocal_line_returns_none_without_any_marked_note():
    separator = VoiceSeparator()
    notes = notes_clear_melody_over_accompaniment()

    result = separator._apply_vocal_line_if_available(notes)

    assert result is None

def test_apply_vocal_line_overrides_a4_a5_result():
    separator = VoiceSeparator()
    notes = notes_with_marked_vocal_origin()

    vocal_notes, other_notes = separator._apply_vocal_line_if_available(notes)

    assert [n.pitch for n in vocal_notes] == [55, 57]
    assert [n.pitch for n in other_notes] == [72, 74]

    #Confirma a sobreposicao tambem no pipeline completo do componente:
    #A4 isolado classificaria 72/74 (mais agudas) como melodia - A6 inverte isso
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    for note in notes:
        voice.add_note(note)
    piece.add_voice(voice)

    separator.process(piece, Config(), Signaler())

    melody_voice = next(v for v in piece.voices if v.paper is PaperVoice.MELODY)
    accompaniment_voice = next(v for v in piece.voices if v.paper is PaperVoice.ACCOMPANIMENT)
    assert [n.pitch for n in melody_voice.notes] == [55, 57]
    assert [n.pitch for n in accompaniment_voice.notes] == [72, 74]

def test_process_produces_exactly_two_voices_with_correct_papers():
    separator = VoiceSeparator()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    for note in notes_clear_melody_over_accompaniment():
        voice.add_note(note)
    piece.add_voice(voice)

    separator.process(piece, Config(), Signaler())

    assert len(piece.voices) == 2
    papers = {v.paper for v in piece.voices}
    assert papers == {PaperVoice.MELODY, PaperVoice.ACCOMPANIMENT}

def test_process_clef_correct_as_consequence_of_paper():
    separator = VoiceSeparator()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    for note in notes_clear_melody_over_accompaniment():
        voice.add_note(note)
    piece.add_voice(voice)

    separator.process(piece, Config(), Signaler())

    melody_voice = next(v for v in piece.voices if v.paper is PaperVoice.MELODY)
    accompaniment_voice = next(v for v in piece.voices if v.paper is PaperVoice.ACCOMPANIMENT)
    assert melody_voice.clef is Clef.SOL
    assert accompaniment_voice.clef is Clef.FA

def test_orchestrator_complete_so_far_integrates_correctly():
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    for note in notes_clear_melody_over_accompaniment():
        voice.add_note(note)
    piece.add_voice(voice)
    piece.raw_signals = RawSignals(regular_4_4_beats(1))

    orchestrator = Orchestrator(config, signaler)
    orchestrator.add_stage(Cleaner())
    orchestrator.add_stage(StructuralDetector())
    orchestrator.add_stage(VoiceSeparator())
    result = orchestrator.process(piece)

    assert result is piece
    assert len(result.voices) == 2
    papers = {v.paper for v in result.voices}
    assert papers == {PaperVoice.MELODY, PaperVoice.ACCOMPANIMENT}
    assert len(result.all_notes()) == 8
    assert len(result.compasses) == 1