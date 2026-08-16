import pytest
import wave
import os
import torch
from models.note import Note
from signal_extractor.separation import SourceSeparator
from signal_extractor.note_extraction import NoteExtractor
from signal_extractor.extraction_pipeline import extract_notes_from_mix
from tests.fixtures import generate_two_tone_wav


def _wav_duration_seconds(path: str) -> float:
    with wave.open(path, 'r') as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def test_combinar_stems_instrumentais_soma_elementwise():
    separator = SourceSeparator()
    stems = {
        "drums": torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
        "bass": torch.tensor([[0.5, 0.5], [0.5, 0.5]]),
        "other": torch.tensor([[1.0, 1.0], [1.0, 1.0]]),
        "vocals": torch.tensor([[100.0, 100.0], [100.0, 100.0]]),
    }

    combined = separator._combine_instrumental_stems(stems)

    expected = torch.tensor([[2.5, 3.5], [4.5, 5.5]])
    assert torch.allclose(combined, expected)

def test_combinar_stems_instrumentais_ignora_stem_vocal():
    separator = SourceSeparator()
    stems = {
        "drums": torch.zeros((1, 2)),
        "bass": torch.zeros((1, 2)),
        "other": torch.zeros((1, 2)),
        "vocals": torch.tensor([[999.0, 999.0]]),
    }

    combined = separator._combine_instrumental_stems(stems)

    assert torch.allclose(combined, torch.zeros((1, 2)))

@pytest.mark.integracao
def test_separar_produz_exatamente_dois_arquivos(tmp_path):
    audio_path = str(tmp_path / "entrada.wav")
    generate_two_tone_wav(audio_path, 220.0, 440.0, 2.0)
    output_dir = str(tmp_path / "saida")

    vocal_path, instrumental_path = SourceSeparator().separate(audio_path, output_dir)

    assert os.path.exists(vocal_path)
    assert os.path.exists(instrumental_path)
    assert vocal_path != instrumental_path

@pytest.mark.integracao
def test_separar_arquivos_tem_duracao_proxima_do_original(tmp_path):
    audio_path = str(tmp_path / "entrada.wav")
    generate_two_tone_wav(audio_path, 220.0, 440.0, 2.0)
    output_dir = str(tmp_path / "saida")

    vocal_path, instrumental_path = SourceSeparator().separate(audio_path, output_dir)

    original_duration = _wav_duration_seconds(audio_path)

    for path in (vocal_path, instrumental_path):
        duration = _wav_duration_seconds(path)
        assert duration == pytest.approx(original_duration, abs=0.5)

@pytest.mark.integracao
def test_separar_arquivos_sao_audio_valido_recarregavel(tmp_path):
    audio_path = str(tmp_path / "entrada.wav")
    generate_two_tone_wav(audio_path, 220.0, 440.0, 2.0)
    output_dir = str(tmp_path / "saida")

    vocal_path, instrumental_path = SourceSeparator().separate(audio_path, output_dir)

    for path in (vocal_path, instrumental_path):
        with wave.open(path, 'r') as wav_file:
            assert wav_file.getnframes() > 0
            assert wav_file.getframerate() == 44100

def test_extrair_notas_de_mixagem_marca_origem_vocal_corretamente(monkeypatch, tmp_path):
    #Nao chama Demucs/Basic Pitch de verdade - o Demucs usa shifts como
    #augmentation na inferencia (desloca, separa, desfaz o deslocamento),
    #entao duas chamadas reais sobre o mesmo audio nao produzem exatamente
    #o mesmo resultado. A propriedade que este teste verifica e nossa
    #(a logica de marcacao/mesclagem em extract_notes_from_mix), nao uma
    #garantia de reprodutibilidade do modelo - por isso o isolamento via
    #monkeypatch, e por isso NAO e um teste de integracao
    vocal_notes = [Note(60, 0.0, 0.5, 0.8), Note(64, 1.0, 1.5, 0.8)]
    instrumental_notes = [Note(48, 0.2, 0.7, 0.8), Note(52, 1.2, 1.7, 0.8)]

    def fake_separate(self, audio_path, output_directory):
        return "fake_vocal.wav", "fake_instrumental.wav"

    def fake_extract(self, path):
        return list(vocal_notes) if path == "fake_vocal.wav" else list(instrumental_notes)

    monkeypatch.setattr(SourceSeparator, "separate", fake_separate)
    monkeypatch.setattr(NoteExtractor, "extract", fake_extract)

    notes = extract_notes_from_mix("qualquer.wav", str(tmp_path))

    vocal_results = [n for n in notes if n.pitch in (60, 64)]
    instrumental_results = [n for n in notes if n.pitch in (48, 52)]
    assert len(vocal_results) == 2
    assert len(instrumental_results) == 2
    assert all(n.vocal_origin_identified is True for n in vocal_results)
    assert all(n.vocal_origin_identified is False for n in instrumental_results)

@pytest.mark.integracao
def test_extrair_notas_de_mixagem_retorna_lista_ordenada_por_onset(tmp_path):
    audio_path = str(tmp_path / "entrada.wav")
    generate_two_tone_wav(audio_path, 220.0, 440.0, 2.0)
    temp_dir = str(tmp_path / "temp")

    notes = extract_notes_from_mix(audio_path, temp_dir)

    onsets = [n.onset for n in notes]
    assert onsets == sorted(onsets)