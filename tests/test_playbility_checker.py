import pytest
from playability.playability_checker import (
    PlayabilityChecker,
    CHORD_REACH_LIMIT_SEMITONES,
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
from rhythm.quantizer import Quantizer
from completeness.completeness_detector import CompletenessDetector
from notation.notator import Notator
from models.raw_signals import RawSignals
from tests.fixtures import (
    chord_within_reach,
    chord_above_reach,
    leap_with_sufficient_time,
    impossible_leap,
    regular_4_4_beats,
)


def _single_measure_piece() -> Piece:
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    return piece


def test_agrupar_em_acordes_junta_notas_simultaneas():
    checker = PlayabilityChecker()
    _, voice = chord_within_reach()

    groups = checker._group_into_chords(voice)

    assert len(groups) == 1
    assert {n.pitch for n in groups[0]} == {60, 64, 67}

def test_agrupar_em_acordes_ignora_nota_sem_simultaneas():
    checker = PlayabilityChecker()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(64, 0.5, 1.0, 0.8))

    groups = checker._group_into_chords(voice)

    assert groups == []

def test_agrupar_em_acordes_nao_duplica_nota_entre_grupos():
    checker = PlayabilityChecker()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 1.0, 0.8))
    voice.add_note(Note(64, 0.0, 1.0, 0.8))
    voice.add_note(Note(67, 0.0, 1.0, 0.8))
    voice.add_note(Note(72, 0.0, 1.0, 0.8))

    groups = checker._group_into_chords(voice)

    assert len(groups) == 1
    assert len(groups[0]) == 4
    all_pitches_seen = [n.pitch for n in groups[0]]
    assert len(all_pitches_seen) == len(set(all_pitches_seen))

def test_verificar_alcance_gera_uma_sinalizacao_por_acorde_nao_por_nota():
    checker = PlayabilityChecker()
    signaler = Signaler()
    piece, voice = chord_above_reach()

    checker._check_chord_reach(voice, piece, signaler)

    assert len(signaler.all()) == 1

def test_verificar_alcance_ignora_acorde_dentro_do_limite():
    checker = PlayabilityChecker()
    signaler = Signaler()
    piece, voice = chord_within_reach()

    checker._check_chord_reach(voice, piece, signaler)

    assert signaler.all() == []

def test_verificar_alcance_detecta_acorde_acima_do_limite():
    checker = PlayabilityChecker()
    signaler = Signaler()
    piece, voice = chord_above_reach()

    checker._check_chord_reach(voice, piece, signaler)

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.IMPOSSIBLE_PASSAGE
    assert signals[0].level == SeverityLevel.REQUIRES_DECISION
    assert signals[0].note.pitch == 48   # a nota mais grave do grupo

def test_verificar_alcance_limite_exato_nao_dispara():
    checker = PlayabilityChecker()
    signaler = Signaler()
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(48, 0.0, 1.0, 0.8))
    voice.add_note(Note(48 + CHORD_REACH_LIMIT_SEMITONES, 0.0, 1.0, 0.8))
    piece.add_voice(voice)

    checker._check_chord_reach(voice, piece, signaler)

    assert signaler.all() == []

def test_verificar_velocidade_ignora_salto_com_tempo_suficiente():
    checker = PlayabilityChecker()
    signaler = Signaler()
    piece, voice = leap_with_sufficient_time()

    checker._check_leap_speed(voice, piece, signaler)

    assert signaler.all() == []

def test_verificar_velocidade_detecta_salto_impossivel():
    checker = PlayabilityChecker()
    signaler = Signaler()
    piece, voice = impossible_leap()

    checker._check_leap_speed(voice, piece, signaler)

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.IMPOSSIBLE_PASSAGE
    assert signals[0].level == SeverityLevel.REQUIRES_DECISION
    assert signals[0].note.pitch == 84   # a nota de chegada

@pytest.mark.parametrize("distance,expected_signal", [
    (2, False),    # distancia pequena, mesmo tempo curto -> passa
    (30, True),    # distancia grande, mesmo tempo curto -> falha
])
def test_verificar_velocidade_considera_distancia_e_tempo_juntos(distance, expected_signal):
    checker = PlayabilityChecker()
    signaler = Signaler()
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(60 + distance, 0.6, 1.0, 0.8))   # gap fixo de 0.1s
    piece.add_voice(voice)

    checker._check_leap_speed(voice, piece, signaler)

    assert (len(signaler.all()) == 1) is expected_signal

def test_processar_nunca_altera_nenhuma_nota():
    checker = PlayabilityChecker()
    config = Config()
    signaler = Signaler()
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(48, 0.0, 0.5, 0.8))
    voice.add_note(Note(64, 0.0, 0.5, 0.8))
    voice.add_note(Note(67, 0.0, 0.5, 0.8))
    voice.add_note(Note(90, 0.51, 1.0, 0.8))
    piece.add_voice(voice)

    notes_before = [(n.pitch, n.onset, n.offset) for n in piece.all_notes()]

    checker.process(piece, config, signaler)

    notes_after = [(n.pitch, n.onset, n.offset) for n in piece.all_notes()]
    assert notes_before == notes_after

def test_processar_gera_sinalizacoes_de_nivel_requer_decisao():
    checker = PlayabilityChecker()
    config = Config()
    signaler = Signaler()
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(48, 0.0, 0.5, 0.8))
    voice.add_note(Note(64, 0.0, 0.5, 0.8))
    voice.add_note(Note(67, 0.0, 0.5, 0.8))
    voice.add_note(Note(90, 0.51, 1.0, 0.8))
    piece.add_voice(voice)

    checker.process(piece, config, signaler)

    signals = signaler.all()
    assert len(signals) >= 1
    assert all(s.level == SeverityLevel.REQUIRES_DECISION for s in signals)
    assert all(s.category == SignalingCategory.IMPOSSIBLE_PASSAGE for s in signals)

def test_orquestrador_completo_ate_aqui_integra_corretamente():
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    voice.add_note(Note(60, 0.0, 1.0, 0.8))    # C4
    voice.add_note(Note(96, 1.0, 1.25, 0.8))   # C7, salto de 36 semitons, gap=0
    piece.add_voice(voice)
    piece.raw_signals = RawSignals(regular_4_4_beats(1))

    orchestrator = Orchestrator(config, signaler)
    orchestrator.add_stage(Cleaner())
    orchestrator.add_stage(StructuralDetector())
    orchestrator.add_stage(VoiceSeparator())
    orchestrator.add_stage(OctaveCorrector())
    orchestrator.add_stage(Quantizer())
    orchestrator.add_stage(CompletenessDetector())
    orchestrator.add_stage(Notator())
    orchestrator.add_stage(PlayabilityChecker())
    result = orchestrator.process(piece)

    assert result is piece
    melody_voice = next(v for v in result.voices if v.paper.value == "melodia")
    assert [n.pitch for n in melody_voice.notes] == [60, 96]
    assert [n.onset for n in melody_voice.notes] == [0.0, 1.0]
    assert [n.offset for n in melody_voice.notes] == [1.0, 1.25]

    signals = signaler.all()
    impossible_signals = [s for s in signals if s.category == SignalingCategory.IMPOSSIBLE_PASSAGE]
    assert len(impossible_signals) == 1
    assert impossible_signals[0].level == SeverityLevel.REQUIRES_DECISION
    assert impossible_signals[0].compass_number == 1