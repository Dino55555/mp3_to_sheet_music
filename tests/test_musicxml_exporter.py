import pytest
from music21 import stream, converter
from notation.musicxml_exporter import MusicXMLExporter
from models.note import Note
from models.voice import (Voice, PaperVoice)
from models.compass import (Compass, TimeSignature, KeySignature, TonalMode)
from models.pitch_spelling import PitchSpelling
from Compass.piece import Piece
from Compass.instrument import Instrument
from tests.fixtures import (
    piece_ready_to_export,
    note_crossing_compass,
)


def _note_with_graphy(pitch: int, onset: float, offset: float, letter: str, alteration: int, octave: int) -> Note:
    note = Note(pitch, onset, offset, 0.8)
    note.graphy = PitchSpelling(letter, alteration, octave)
    return note


def test_fator_quarterlength_por_segundo_metrica_simples():
    exporter = MusicXMLExporter()
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))

    factor = exporter._quarterlength_factor_per_second(compass)

    assert factor == pytest.approx(1.0)

def test_fator_quarterlength_por_segundo_metrica_composta():
    exporter = MusicXMLExporter()
    compass = Compass(1, 0.0, 8.0, TimeSignature(12, 8, is_compound=True), KeySignature(0, "C", TonalMode.MAJOR))

    factor = exporter._quarterlength_factor_per_second(compass)

    #beat_groups=4, segundos_por_grupo=8.0/4=2.0, quarterLength_por_grupo=1.5
    assert factor == pytest.approx(0.75)

def test_offsets_acumulados_soma_duracoes_em_sequencia():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    c1 = Compass(1, 0.0, 2.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    c2 = Compass(2, 2.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    c3 = Compass(3, 4.0, 6.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(c1)
    piece.add_compass(c2)
    piece.add_compass(c3)

    offsets = exporter._cumulative_offsets(piece)

    #cada compasso: 2.0s * fator(2.0) = 4.0 quarterLength
    assert offsets == {1: 0.0, 2: 4.0, 3: 8.0}

def test_pitch_m21_constroi_pitch_correto_para_nota_diatonica():
    exporter = MusicXMLExporter()
    spelling = PitchSpelling('F', 0, 4)

    p = exporter._m21_pitch(spelling)

    assert p.step == 'F'
    assert p.octave == 4
    assert p.midi == 65

@pytest.mark.parametrize("letter,alteration,expected_midi", [
    ('C', 1, 61),
    ('D', -1, 61),
])
def test_pitch_m21_constroi_pitch_correto_para_nota_com_acidente(letter, alteration, expected_midi):
    exporter = MusicXMLExporter()
    spelling = PitchSpelling(letter, alteration, 4)

    p = exporter._m21_pitch(spelling)

    assert p.step == letter
    assert p.accidental.alter == alteration
    assert p.midi == expected_midi

def test_nota_m21_converte_duracao_para_quarterlength_corretamente():
    exporter = MusicXMLExporter()
    note = _note_with_graphy(60, 0.0, 1.5, 'C', 0, 4)

    m21_note = exporter._m21_note(note, 2.0)

    assert m21_note.quarterLength == pytest.approx(3.0)

def test_nota_m21_adiciona_articulacao_staccato_quando_marcado():
    exporter = MusicXMLExporter()
    note = _note_with_graphy(60, 0.0, 0.5, 'C', 0, 4)
    note.staccato = True

    m21_note = exporter._m21_note(note, 1.0)

    assert len(m21_note.articulations) == 1
    assert m21_note.articulations[0].name == 'staccato'

def test_construir_parte_insere_clave_correta_conforme_papel_da_voz():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    offsets = exporter._cumulative_offsets(piece)

    melody_voice = Voice(paper=PaperVoice.MELODY)
    melody_voice.add_note(_note_with_graphy(60, 0.0, 4.0, 'C', 0, 4))
    accompaniment_voice = Voice(paper=PaperVoice.ACCOMPANIMENT)
    accompaniment_voice.add_note(_note_with_graphy(48, 0.0, 4.0, 'C', 0, 3))

    melody_part = exporter._build_part(melody_voice, piece, offsets)
    accompaniment_part = exporter._build_part(accompaniment_voice, piece, offsets)

    melody_measure = melody_part.getElementsByClass(stream.Measure)[0]
    accompaniment_measure = accompaniment_part.getElementsByClass(stream.Measure)[0]
    assert type(melody_measure.clef).__name__ == 'TrebleClef'
    assert type(accompaniment_measure.clef).__name__ == 'BassClef'

def test_construir_parte_insere_formula_apenas_quando_muda():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    c1 = Compass(1, 0.0, 2.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    c2 = Compass(2, 2.0, 3.5, TimeSignature(3, 4), KeySignature(0, "C", TonalMode.MAJOR))
    c3 = Compass(3, 3.5, 5.0, TimeSignature(3, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(c1)
    piece.add_compass(c2)
    piece.add_compass(c3)
    voice = Voice(paper=PaperVoice.MELODY)
    voice.add_note(_note_with_graphy(60, 0.0, 2.0, 'C', 0, 4))
    voice.add_note(_note_with_graphy(62, 2.0, 3.5, 'D', 0, 4))
    voice.add_note(_note_with_graphy(64, 3.5, 5.0, 'E', 0, 4))
    offsets = exporter._cumulative_offsets(piece)

    part = exporter._build_part(voice, piece, offsets)
    measures = part.getElementsByClass(stream.Measure)

    assert measures[0].timeSignature is not None
    assert measures[1].timeSignature is not None
    assert str(measures[1].timeSignature) == '<music21.meter.TimeSignature 3/4>'
    assert measures[2].timeSignature is None

def test_construir_parte_insere_armadura_apenas_quando_muda():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    c1 = Compass(1, 0.0, 2.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    c2 = Compass(2, 2.0, 4.0, TimeSignature(4, 4), KeySignature(2, "D", TonalMode.MAJOR))
    c3 = Compass(3, 4.0, 6.0, TimeSignature(4, 4), KeySignature(2, "D", TonalMode.MAJOR))
    piece.add_compass(c1)
    piece.add_compass(c2)
    piece.add_compass(c3)
    voice = Voice(paper=PaperVoice.MELODY)
    voice.add_note(_note_with_graphy(60, 0.0, 2.0, 'C', 0, 4))
    voice.add_note(_note_with_graphy(62, 2.0, 4.0, 'D', 0, 4))
    voice.add_note(_note_with_graphy(64, 4.0, 6.0, 'E', 0, 4))
    offsets = exporter._cumulative_offsets(piece)

    part = exporter._build_part(voice, piece, offsets)
    measures = part.getElementsByClass(stream.Measure)

    assert measures[0].keySignature is not None
    assert measures[1].keySignature is not None
    assert measures[1].keySignature.sharps == 2
    assert measures[2].keySignature is None

def test_construir_parte_nota_cruzando_compasso_vira_notas_ligadas_apos_makeNotation():
    exporter = MusicXMLExporter()
    piece = note_crossing_compass()
    voice = piece.voices[0]
    offsets = exporter._cumulative_offsets(piece)

    part = exporter._build_part(voice, piece, offsets)
    measures = part.getElementsByClass(stream.Measure)

    assert len(measures) == 2
    m1_notes = list(measures[0].notesAndRests)
    m2_notes = list(measures[1].notesAndRests)

    assert m1_notes[-1].tie is not None
    assert m1_notes[-1].tie.type == 'start'
    assert m2_notes[0].tie is not None
    assert m2_notes[0].tie.type == 'stop'
    #a soma dos dois segmentos ligados preserva a duracao total da nota
    assert m1_notes[-1].quarterLength + m2_notes[0].quarterLength == pytest.approx(2.0)

def test_construir_score_tem_uma_part_por_voz():
    exporter = MusicXMLExporter()
    piece = piece_ready_to_export()

    score = exporter._build_score(piece)

    assert len(score.getElementsByClass(stream.Part)) == 2

def test_exportar_produz_arquivo_valido_no_disco(tmp_path):
    exporter = MusicXMLExporter()
    piece = piece_ready_to_export()
    path = tmp_path / "saida.musicxml"

    exporter.export(piece, str(path))

    assert path.exists()
    reloaded = converter.parse(str(path))
    assert isinstance(reloaded, stream.Score)

def test_exportar_arquivo_tem_numero_de_notas_esperado_por_parte(tmp_path):
    exporter = MusicXMLExporter()
    piece = piece_ready_to_export()
    path = tmp_path / "saida.musicxml"

    exporter.export(piece, str(path))
    reloaded = converter.parse(str(path))
    parts = list(reloaded.getElementsByClass(stream.Part))

    notes_per_part = sorted(len(list(part.recurse().notes)) for part in parts)
    assert notes_per_part == [3, 4]