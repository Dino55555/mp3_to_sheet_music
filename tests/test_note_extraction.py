import pytest
import wave
import pretty_midi
from signal_extractor.note_extraction import (NoteExtractor, build_initial_piece)
from models.voice import PaperVoice
from Compass.instrument import Instrument
from tests.fixtures import (generate_sine_wav, generate_silence_wav)


def test_nota_a_partir_de_mapeia_campos_corretamente():
    extractor = NoteExtractor()
    midi_note = pretty_midi.Note(velocity=100, pitch=69, start=0.1, end=0.9)

    note = extractor._note_from(midi_note)

    assert note.pitch == 69
    assert note.onset == pytest.approx(0.1)
    assert note.offset == pytest.approx(0.9)

def test_nota_a_partir_de_normaliza_velocity_para_intensidade_0_a_1():
    extractor = NoteExtractor()
    midi_note = pretty_midi.Note(velocity=127, pitch=60, start=0.0, end=1.0)

    note = extractor._note_from(midi_note)

    assert note.magnitude == pytest.approx(1.0)

    midi_note_half = pretty_midi.Note(velocity=64, pitch=60, start=0.0, end=1.0)
    note_half = extractor._note_from(midi_note_half)
    assert note_half.magnitude == pytest.approx(64 / 127.0)

def test_nota_a_partir_de_usa_confiancas_padrao():
    extractor = NoteExtractor()
    midi_note = pretty_midi.Note(velocity=100, pitch=69, start=0.1, end=0.9)

    note = extractor._note_from(midi_note)

    assert note.reliability_existence == 1.0
    assert note.reliability_highness == 1.0
    assert note.reliability_duration == 1.0
    assert note.reliability_voice == 1.0

def test_montar_peca_inicial_cria_voz_unica_sem_papel():
    from models.note import Note
    notes = [Note(60, 0.0, 0.5, 0.8), Note(62, 0.5, 1.0, 0.8)]

    piece = build_initial_piece(notes, Instrument.piano())

    assert len(piece.voices) == 1
    assert piece.voices[0].paper is None

def test_montar_peca_inicial_preserva_ordenacao_das_notas():
    from models.note import Note
    notes = [Note(64, 1.0, 1.5, 0.8), Note(60, 0.0, 0.5, 0.8), Note(62, 0.5, 1.0, 0.8)]

    piece = build_initial_piece(notes, Instrument.piano())

    onsets = [n.onset for n in piece.voices[0].notes]
    assert onsets == sorted(onsets)

def test_montar_peca_inicial_compassos_vazio():
    from models.note import Note
    notes = [Note(60, 0.0, 0.5, 0.8)]

    piece = build_initial_piece(notes, Instrument.piano())

    assert piece.compasses == []

def test_gerar_wav_seno_produz_arquivo_com_duracao_correta(tmp_path):
    path = str(tmp_path / "seno.wav")

    generate_sine_wav(path, 440.0, 1.0)

    with wave.open(path, 'r') as wav_file:
        duration = wav_file.getnframes() / wav_file.getframerate()
        assert duration == pytest.approx(1.0)
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2

@pytest.mark.integracao
def test_extrair_detecta_pitch_aproximado_de_seno_puro(tmp_path):
    path = str(tmp_path / "seno.wav")
    generate_sine_wav(path, 440.0, 1.0)

    notes = NoteExtractor().extract(path)

    assert len(notes) >= 1
    assert any(abs(note.pitch - 69) <= 1 for note in notes)

@pytest.mark.integracao
def test_extrair_onset_offset_proximos_da_duracao_real(tmp_path):
    path = str(tmp_path / "seno.wav")
    generate_sine_wav(path, 440.0, 1.0)

    notes = NoteExtractor().extract(path)

    assert len(notes) >= 1
    main_note = max(notes, key=lambda n: n.duration())
    assert main_note.onset < 0.2
    assert main_note.offset > 0.8

@pytest.mark.integracao
def test_extrair_retorna_vazio_para_silencio(tmp_path):
    path = str(tmp_path / "silencio.wav")
    generate_silence_wav(path, 1.0)

    notes = NoteExtractor().extract(path)

    assert notes == []