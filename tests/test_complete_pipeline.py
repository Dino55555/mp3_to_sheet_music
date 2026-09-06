import os
import sys
import subprocess
import pytest
from complete_pipeline import (
    InvalidInputError,
    ProcessingResult,
    default_stages,
    _count_by_severity,
    _output_names,
    process_file,
)
from models.signaling import (Signaling, SignalingCategory, SeverityLevel)
from cleaning.cleaner import Cleaner
from structure.structural_detector import StructuralDetector
from voices.voice_separator import VoiceSeparator
from voices.octave_corrector import OctaveCorrector
from rhythm.quantizer import Quantizer
from completeness.completeness_detector import CompletenessDetector
from playability.playability_checker import PlayabilityChecker
from notation.notator import Notator
from tests.fixtures import generate_simple_melody_wav
import signal_extractor.rhythmic_detection as rhythmic_detection_module
from vibrato.vibrato_detector import VibratoDetector

@pytest.fixture
def use_local_checkpoint(monkeypatch):
    monkeypatch.setattr(rhythmic_detection_module, "MODEL_CHECKPOINT", "checkpoints/final0.ckpt")


def test_contar_por_severidade_soma_corretamente_os_tres_niveis():
    signalings = [
        Signaling(SignalingCategory.IMPOSSIBLE_PASSAGE, SeverityLevel.REQUIRES_DECISION, "a", 1),
        Signaling(SignalingCategory.IMPOSSIBLE_PASSAGE, SeverityLevel.REQUIRES_DECISION, "b", 2),
        Signaling(SignalingCategory.AMBIGUOUS_KEY, SeverityLevel.VERIFY, "c", 3),
        Signaling(SignalingCategory.INFERRED_NOTE, SeverityLevel.INFORMATIONAL, "d", 4),
        Signaling(SignalingCategory.INFERRED_NOTE, SeverityLevel.INFORMATIONAL, "e", 5),
        Signaling(SignalingCategory.INFERRED_NOTE, SeverityLevel.INFORMATIONAL, "f", 6),
    ]

    result = _count_by_severity(signalings)

    assert result[SeverityLevel.REQUIRES_DECISION] == 2
    assert result[SeverityLevel.VERIFY] == 1
    assert result[SeverityLevel.INFORMATIONAL] == 3
    assert sum(result.values()) == len(signalings)

def test_nomes_de_saida_deriva_do_nome_base_do_mp3():
    musicxml_path, mxl_path, report_path = _output_names("/caminho/qualquer/musica.mp3", "/saida")

    assert musicxml_path == os.path.join("/saida", "musica.musicxml")
    assert mxl_path == os.path.join("/saida", "musica.mxl")
    assert report_path == os.path.join("/saida", "musica_relatorio.txt")

def test_processar_arquivo_inexistente_levanta_erro_de_entrada_invalida(tmp_path):
    with pytest.raises(InvalidInputError):
        process_file(str(tmp_path / "nao_existe.mp3"), str(tmp_path / "saida"))

def test_main_arquivo_inexistente_encerra_com_codigo_1_sem_traceback(tmp_path):
    result = subprocess.run(
        [sys.executable, "main.py", str(tmp_path / "nao_existe.mp3"), "--saida", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "não encontrado" in result.stderr

@pytest.mark.integracao
def test_processar_arquivo_completo_produz_tres_arquivos(tmp_path, use_local_checkpoint):
    audio_path = str(tmp_path / "melodia.wav")
    generate_simple_melody_wav(audio_path, [60, 62, 64, 65], 120)
    output_dir = str(tmp_path / "saida")

    result = process_file(audio_path, output_dir)

    assert os.path.exists(result.musicxml_path)
    assert os.path.exists(result.mxl_path)
    assert os.path.exists(result.report_path)

@pytest.mark.integracao
def test_processar_arquivo_completo_musicxml_e_valido_via_music21(tmp_path, use_local_checkpoint):
    from music21 import converter

    audio_path = str(tmp_path / "melodia.wav")
    generate_simple_melody_wav(audio_path, [60, 62, 64, 65], 120)
    output_dir = str(tmp_path / "saida")

    result = process_file(audio_path, output_dir)

    reloaded = converter.parse(result.musicxml_path)
    assert reloaded is not None

@pytest.mark.integracao
def test_processar_arquivo_completo_resultado_reflete_sinalizacoes_reais(tmp_path, use_local_checkpoint):
    audio_path = str(tmp_path / "melodia.wav")
    generate_simple_melody_wav(audio_path, [60, 62, 64, 65], 120)
    output_dir = str(tmp_path / "saida")

    result = process_file(audio_path, output_dir)

    report_content = open(result.report_path, encoding="utf-8").read()
    total_signaled = sum(result.count_by_severity.values())

    if total_signaled == 0:
        assert "Nenhum ponto sinalizado" in report_content
    else:
        level_titles = {
            SeverityLevel.REQUIRES_DECISION: "REQUER DECISÃO",
            SeverityLevel.VERIFY: "VERIFICAR",
            SeverityLevel.INFORMATIONAL: "INFORMATIVO",
        }
        for level, count in result.count_by_severity.items():
            if count > 0:
                assert f"{level_titles[level]} ({count})" in report_content

def test_etapas_padrao_retorna_nove_etapas_na_ordem_certa():
    stages = default_stages()

    assert len(stages) == 9
    expected_types = [
        Cleaner, StructuralDetector, VibratoDetector, VoiceSeparator, OctaveCorrector,
        Quantizer, CompletenessDetector, PlayabilityChecker, Notator,
    ]
    assert [type(stage) for stage in stages] == expected_types