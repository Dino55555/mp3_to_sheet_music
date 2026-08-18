import pytest
from signal_extractor.rhythmic_detection import (
    BeatDetector,
    INSTANT_TOLERANCE_SECONDS,
    REGULARITY_WINDOW_SIZE,
    LOW_CONFIDENCE,
)
from models.raw_signals import RawSignals
from config import Config
from signaling.signaler import Signaler
from structure.structural_detector import StructuralDetector
from Compass.piece import Piece
from Compass.instrument import Instrument
from models.note import Note
from models.voice import Voice
from tests.fixtures import generate_click_wav


def test_eh_downbeat_identifica_correspondencia_dentro_da_tolerancia():
    detector = BeatDetector()

    assert detector._is_downbeat(1.0, [1.003]) is True

def test_eh_downbeat_rejeita_instante_fora_da_tolerancia():
    detector = BeatDetector()

    assert detector._is_downbeat(1.0, [1.05]) is False

def test_estimar_confianca_alta_para_sequencia_regular():
    detector = BeatDetector()
    beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

    for index in range(1, len(beats) - 1):
        assert detector._estimate_confidence_by_regularity(index, beats) == 1.0

def test_estimar_confianca_baixa_para_perturbacao_isolada():
    detector = BeatDetector()
    #mesma sequencia regular (intervalo 0.5), com uma perturbacao isolada
    #no indice 4 (2.0 -> 2.3)
    beats = [0.0, 0.5, 1.0, 1.5, 2.3, 2.5, 3.0, 3.5, 4.0]

    assert detector._estimate_confidence_by_regularity(4, beats) == LOW_CONFIDENCE
    assert detector._estimate_confidence_by_regularity(5, beats) == LOW_CONFIDENCE
    #vizinha mais distante nao deveria ser contaminada
    assert detector._estimate_confidence_by_regularity(1, beats) == 1.0
    assert detector._estimate_confidence_by_regularity(7, beats) == 1.0

def test_estimar_confianca_nas_bordas_retorna_padrao_alto():
    detector = BeatDetector()
    #sequencia deliberadamente irregular - a borda deve retornar 1.0
    #independente da irregularidade ao redor
    beats = [0.0, 0.5, 5.0, 5.3, 20.0]

    assert detector._estimate_confidence_by_regularity(0, beats) == 1.0
    assert detector._estimate_confidence_by_regularity(len(beats) - 1, beats) == 1.0

def test_construir_batidas_marca_tempo_forte_corretamente():
    detector = BeatDetector()
    beats = [0.0, 0.5, 1.0, 1.5]
    downbeats = [0.0, 1.0]

    result = detector._build_beats(beats, downbeats)

    assert [b.is_strong_beat for b in result] == [True, False, True, False]
    assert [b.instant for b in result] == beats

@pytest.mark.integracao
def test_detectar_produz_batidas_com_instantes_crescentes(tmp_path):
    audio_path = str(tmp_path / "cliques.wav")
    generate_click_wav(audio_path, 120, 4.0)

    result = BeatDetector().detect(audio_path)

    instants = [b.instant for b in result.beats]
    assert instants == sorted(instants)
    assert len(instants) >= 2

@pytest.mark.integracao
def test_detectar_identifica_ao_menos_um_downbeat_em_audio_ritmico(tmp_path):
    audio_path = str(tmp_path / "cliques.wav")
    generate_click_wav(audio_path, 120, 4.0)

    result = BeatDetector().detect(audio_path)

    assert any(b.is_strong_beat for b in result.beats)

@pytest.mark.integracao
def test_sinais_brutos_de_detectar_e_aceito_pelo_detector_estrutural(tmp_path):
    audio_path = str(tmp_path / "cliques.wav")
    generate_click_wav(audio_path, 120, 4.0)

    raw_signals = BeatDetector().detect(audio_path)

    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    voice.add_note(Note(60, 0.1, 0.4, 0.8))
    piece.add_voice(voice)
    piece.raw_signals = raw_signals

    result = StructuralDetector().process(piece, Config(), Signaler())

    assert len(result.compasses) > 0