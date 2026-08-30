import pytest
from music21 import stream, converter, expressions
from notation.musicxml_exporter import (
    MusicXMLExporter,
    FREE_TIME_TEXT,
    SEVERITY_COLORS,
)
from models.note import Note
from models.voice import (Voice, PaperVoice)
from models.compass import (Compass, TimeSignature, KeySignature, TonalMode)
from models.pitch_spelling import PitchSpelling
from models.signaling import (Signaling, SignalingCategory, SeverityLevel)
from Compass.piece import Piece
from Compass.instrument import Instrument
from config import Config
from signaling.signaler import Signaler
from tests.fixtures import (
    piece_ready_to_export,
    note_crossing_compass,
    peca_com_compasso_rubato_e_swing,
    sinalizador_com_tres_niveis,
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

    assert offsets == {1: 0.0, 2: 4.0, 3: 8.0}

def test_offsets_acumulados_nao_depende_de_duracao_em_segundos():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    #duracoes de compasso "feias", tipicas de BPM nao-redondo derivado de
    #batida real - a soma acumulada deve continuar exata, sem envolver
    #compasso.duracao_em_segundos() em nenhum momento
    c1 = Compass(1, 0.0, 1.9387234, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    c2 = Compass(2, 1.9387234, 4.0512891, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    c3 = Compass(3, 4.0512891, 5.7734512, TimeSignature(3, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(c1)
    piece.add_compass(c2)
    piece.add_compass(c3)

    offsets = exporter._cumulative_offsets(piece)

    assert offsets == {1: 0.0, 2: 4.0, 3: 8.0}

def test_arredondar_para_passo_de_grid_recupera_fracao_exata_a_partir_de_ruido_de_ponto_flutuante():
    exporter = MusicXMLExporter()
    config = Config()   # divisions_per_beat=4, passo=0.25

    assert exporter._round_to_grid_step(0.5721830985915494, config, False) == pytest.approx(0.5)
    assert exporter._round_to_grid_step(1.2499999999999822, config, False) == pytest.approx(1.25)
    assert exporter._round_to_grid_step(0.0788690476190478, config, False) == pytest.approx(0.0)

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

    m21_note = exporter._m21_note(note, 2.0, Config(), False)

    assert m21_note.quarterLength == pytest.approx(3.0)

def test_nota_m21_adiciona_articulacao_staccato_quando_marcado():
    exporter = MusicXMLExporter()
    note = _note_with_graphy(60, 0.0, 0.5, 'C', 0, 4)
    note.staccato = True

    m21_note = exporter._m21_note(note, 1.0, Config(), False)

    assert len(m21_note.articulations) == 1
    assert m21_note.articulations[0].name == 'staccato'

def test_nota_m21_quarterlength_nunca_e_inexpressible_com_compasso_de_bpm_irregular():
    from music21 import duration as m21_duration
    exporter = MusicXMLExporter()
    config = Config()

    #duracoes exatas relatadas como problematicas contra audio real
    problematic_durations_ql = [
        0.5721830985915494,
        0.0788690476190478,
        1.5160876132930512,
        1.5889865924092046,
        1.0889865924092563,
        2.4517658127080635,
    ]

    for raw_ql in problematic_durations_ql:
        note = _note_with_graphy(60, 0.0, raw_ql, 'C', 0, 4)
        m21_note = exporter._m21_note(note, 1.0, config, False)
        d = m21_duration.Duration()
        d.quarterLength = m21_note.quarterLength
        assert d.type not in ('inexpressible', 'zero')

def test_construir_parte_insere_clave_correta_conforme_papel_da_voz():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    offsets = exporter._cumulative_offsets(piece)
    config = Config()

    melody_voice = Voice(paper=PaperVoice.MELODY)
    melody_voice.add_note(_note_with_graphy(60, 0.0, 4.0, 'C', 0, 4))
    accompaniment_voice = Voice(paper=PaperVoice.ACCOMPANIMENT)
    accompaniment_voice.add_note(_note_with_graphy(48, 0.0, 4.0, 'C', 0, 3))

    melody_part, _ = exporter._build_part(melody_voice, piece, offsets, config)
    accompaniment_part, _ = exporter._build_part(accompaniment_voice, piece, offsets, config)

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

    part, _ = exporter._build_part(voice, piece, offsets, Config())
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

    part, _ = exporter._build_part(voice, piece, offsets, Config())
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

    part, _ = exporter._build_part(voice, piece, offsets, Config())
    measures = part.getElementsByClass(stream.Measure)

    assert len(measures) == 2
    m1_notes = list(measures[0].notesAndRests)
    m2_notes = list(measures[1].notesAndRests)

    assert m1_notes[-1].tie is not None
    assert m1_notes[-1].tie.type == 'start'
    assert m2_notes[0].tie is not None
    assert m2_notes[0].tie.type == 'stop'
    assert m1_notes[-1].quarterLength + m2_notes[0].quarterLength == pytest.approx(2.0)

def test_construir_parte_posicao_de_nota_e_exata_sob_bpm_irregular():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    #compasso com duracao "feia", tipico de BPM real nao-redondo
    compass = Compass(1, 0.0, 1.8734129, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)
    voice = Voice(paper=PaperVoice.MELODY)
    #nota comecando exatamente no 3o tempo (indice de grid 8 de 16, ql=2.0)
    note_onset_seconds = compass.begin_time + (2.0 / 4.0) * (compass.duration())
    note = _note_with_graphy(60, note_onset_seconds, compass.end_time, 'C', 0, 4)
    voice.add_note(note)
    offsets = exporter._cumulative_offsets(piece)

    part, note_map = exporter._build_part(voice, piece, offsets, Config())

    m21_note = note_map[id(note)]
    assert m21_note.offset == pytest.approx(2.0)

def test_construir_score_tem_uma_part_por_voz():
    exporter = MusicXMLExporter()
    piece = piece_ready_to_export()

    score, note_map = exporter._build_score(piece, Config())

    assert len(score.getElementsByClass(stream.Part)) == 2
    assert len(note_map) == 7

def test_exportar_produz_arquivo_valido_no_disco(tmp_path):
    exporter = MusicXMLExporter()
    piece = piece_ready_to_export()
    signaler = Signaler()
    score_path = tmp_path / "saida.musicxml"
    report_path = tmp_path / "relatorio.txt"

    exporter.export(piece, str(score_path), signaler, str(report_path), Config())

    assert score_path.exists()
    reloaded = converter.parse(str(score_path))
    assert isinstance(reloaded, stream.Score)

def test_exportar_arquivo_tem_numero_de_notas_esperado_por_parte(tmp_path):
    exporter = MusicXMLExporter()
    piece = piece_ready_to_export()
    signaler = Signaler()
    score_path = tmp_path / "saida.musicxml"
    report_path = tmp_path / "relatorio.txt"

    exporter.export(piece, str(score_path), signaler, str(report_path), Config())
    reloaded = converter.parse(str(score_path))
    parts = list(reloaded.getElementsByClass(stream.Part))

    notes_per_part = sorted(len(list(part.recurse().notes)) for part in parts)
    assert notes_per_part == [3, 4]

def test_exportar_musicxml_com_bpm_irregular_e_valido_via_music21(tmp_path):
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    #serie de compassos com duracoes irregulares, tipico de rastreamento
    #de batida real
    compasses = []
    start = 0.0
    for i, duration in enumerate([1.9387234, 2.0512891, 1.7734512, 2.1123457]):
        end = start + duration
        compasses.append(Compass(i + 1, start, end, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
        start = end
    for compass in compasses:
        piece.add_compass(compass)

    voice = Voice(paper=PaperVoice.MELODY)
    for compass in compasses:
        step = compass.duration() / 4.0
        for beat_index, pitch in enumerate([60, 62, 64, 65]):
            onset = compass.begin_time + beat_index * step
            offset = onset + step
            voice.add_note(_note_with_graphy(pitch, onset, offset, 'C', 0, 4))
    piece.add_voice(voice)

    signaler = Signaler()
    score_path = tmp_path / "saida.musicxml"
    report_path = tmp_path / "relatorio.txt"

    exporter.export(piece, str(score_path), signaler, str(report_path), Config())

    reloaded = converter.parse(str(score_path))
    assert isinstance(reloaded, stream.Score)
    assert len(list(reloaded.recurse().notes)) > 0

def test_construir_parte_retorna_mapa_de_notas_com_id_correto():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice(paper=PaperVoice.MELODY)
    note = _note_with_graphy(60, 0.0, 4.0, 'C', 0, 4)
    voice.add_note(note)
    offsets = exporter._cumulative_offsets(piece)

    part, note_map = exporter._build_part(voice, piece, offsets, Config())

    assert id(note) in note_map
    assert note_map[id(note)] in list(part.recurse().notes)

def test_inserir_indicacoes_de_feel_texto_para_tempo_livre():
    exporter = MusicXMLExporter()
    piece = peca_com_compasso_rubato_e_swing()
    voice = piece.voices[0]
    offsets = exporter._cumulative_offsets(piece)
    part, _ = exporter._build_part(voice, piece, offsets, Config())

    exporter._insert_feel_indications(part, piece, offsets)

    measures = part.getElementsByClass(stream.Measure)
    texts = list(measures[0].getElementsByClass(expressions.TextExpression))
    assert len(texts) == 1
    assert texts[0].content == FREE_TIME_TEXT

def test_inserir_indicacoes_de_feel_texto_para_swing():
    exporter = MusicXMLExporter()
    piece = peca_com_compasso_rubato_e_swing()
    voice = piece.voices[0]
    offsets = exporter._cumulative_offsets(piece)
    part, _ = exporter._build_part(voice, piece, offsets, Config())

    exporter._insert_feel_indications(part, piece, offsets)

    measures = part.getElementsByClass(stream.Measure)
    texts = list(measures[1].getElementsByClass(expressions.TextExpression))
    assert len(texts) == 1
    assert texts[0].content == "swing"

def test_inserir_indicacoes_de_feel_prioriza_tempo_livre_quando_ambos_presentes():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(
        1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR),
        free_time=True, feel_indication="swing",
    )
    piece.add_compass(compass)
    voice = Voice(paper=PaperVoice.MELODY)
    voice.add_note(_note_with_graphy(60, 0.0, 4.0, 'C', 0, 4))
    offsets = exporter._cumulative_offsets(piece)
    part, _ = exporter._build_part(voice, piece, offsets, Config())

    exporter._insert_feel_indications(part, piece, offsets)

    measures = part.getElementsByClass(stream.Measure)
    texts = list(measures[0].getElementsByClass(expressions.TextExpression))
    assert len(texts) == 1
    assert texts[0].content == FREE_TIME_TEXT

def test_inserir_indicacoes_de_feel_ignora_compasso_sem_nenhum_dos_dois():
    exporter = MusicXMLExporter()
    piece = peca_com_compasso_rubato_e_swing()
    voice = piece.voices[0]
    offsets = exporter._cumulative_offsets(piece)
    part, _ = exporter._build_part(voice, piece, offsets, Config())

    exporter._insert_feel_indications(part, piece, offsets)

    measures = part.getElementsByClass(stream.Measure)
    texts = list(measures[2].getElementsByClass(expressions.TextExpression))
    assert texts == []

def test_cor_para_severidade_mapeia_os_tres_niveis():
    exporter = MusicXMLExporter()

    assert exporter._color_for_severity(SeverityLevel.REQUIRES_DECISION) == SEVERITY_COLORS[SeverityLevel.REQUIRES_DECISION]
    assert exporter._color_for_severity(SeverityLevel.VERIFY) == SEVERITY_COLORS[SeverityLevel.VERIFY]
    assert exporter._color_for_severity(SeverityLevel.INFORMATIONAL) == SEVERITY_COLORS[SeverityLevel.INFORMATIONAL]

def test_aplicar_marcacao_visual_define_cor_e_parenteses():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice(paper=PaperVoice.MELODY)
    note = _note_with_graphy(60, 0.0, 4.0, 'C', 0, 4)
    voice.add_note(note)
    offsets = exporter._cumulative_offsets(piece)
    part, note_map = exporter._build_part(voice, piece, offsets, Config())

    signaling = Signaling(SignalingCategory.IMPOSSIBLE_PASSAGE, SeverityLevel.REQUIRES_DECISION, "teste", 1, note)
    exporter._apply_visual_marking(note_map, [signaling])

    m21_note = note_map[id(note)]
    assert m21_note.style.color == SEVERITY_COLORS[SeverityLevel.REQUIRES_DECISION]
    assert m21_note.noteheadParenthesis is True

def test_aplicar_marcacao_visual_ignora_sinalizacao_sem_nota():
    exporter = MusicXMLExporter()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice(paper=PaperVoice.MELODY)
    note = _note_with_graphy(60, 0.0, 4.0, 'C', 0, 4)
    voice.add_note(note)
    offsets = exporter._cumulative_offsets(piece)
    part, note_map = exporter._build_part(voice, piece, offsets, Config())

    signaling = Signaling(SignalingCategory.AMBIGUOUS_KEY, SeverityLevel.VERIFY, "teste", 1, None)
    exporter._apply_visual_marking(note_map, [signaling])

    m21_note = note_map[id(note)]
    assert m21_note.style.color is None
    assert m21_note.noteheadParenthesis is False

def test_aplicar_marcacao_visual_tolera_nota_nao_encontrada_no_mapa():
    exporter = MusicXMLExporter()
    orphan_note = _note_with_graphy(90, 0.0, 1.0, 'F', 1, 5)
    signaling = Signaling(SignalingCategory.IMPOSSIBLE_PASSAGE, SeverityLevel.REQUIRES_DECISION, "teste", 1, orphan_note)

    exporter._apply_visual_marking({}, [signaling])   # nao deve levantar erro

def test_exportar_gera_arquivo_de_relatorio_alem_do_musicxml(tmp_path):
    exporter = MusicXMLExporter()
    piece = piece_ready_to_export()
    signaler = sinalizador_com_tres_niveis()
    score_path = tmp_path / "saida.musicxml"
    report_path = tmp_path / "relatorio.txt"

    exporter.export(piece, str(score_path), signaler, str(report_path), Config())

    assert score_path.exists()
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "REQUER DECISÃO" in content
    assert "VERIFICAR" in content
    assert "INFORMATIVO" in content

def test_orquestrador_completo_ate_aqui_integra_corretamente(tmp_path):
    from models.raw_signals import RawSignals
    from orchestrator import Orchestrator
    from cleaning.cleaner import Cleaner
    from structure.structural_detector import StructuralDetector
    from voices.voice_separator import VoiceSeparator
    from voices.octave_corrector import OctaveCorrector
    from rhythm.quantizer import Quantizer
    from completeness.completeness_detector import CompletenessDetector
    from notation.notator import Notator
    from playability.playability_checker import PlayabilityChecker
    from tests.fixtures import regular_4_4_beats

    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    voice.add_note(Note(60, 0.0, 1.0, 0.8))    # C4
    voice.add_note(Note(96, 1.0, 1.25, 0.8))   # C7, salto impossivel (PlayabilityChecker)
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

    melody_voice = next(v for v in result.voices if v.paper is PaperVoice.MELODY)
    first_note = melody_voice.notes[0]
    signaler.register(SignalingCategory.INFERRED_NOTE, SeverityLevel.INFORMATIONAL, "nota inferida de teste", 1, first_note)
    signaler.register(SignalingCategory.AMBIGUOUS_KEY, SeverityLevel.VERIFY, "tonalidade ambígua de teste", 1)

    exporter = MusicXMLExporter()
    score_path = tmp_path / "saida.musicxml"
    report_path = tmp_path / "relatorio.txt"
    exporter.export(result, str(score_path), signaler, str(report_path), config)

    assert score_path.exists()
    assert report_path.exists()

    reloaded = converter.parse(str(score_path))
    notes = sorted(reloaded.recurse().notes, key=lambda n: n.pitch.midi)
    assert notes[0].style.color == SEVERITY_COLORS[SeverityLevel.INFORMATIONAL]
    assert notes[-1].style.color == SEVERITY_COLORS[SeverityLevel.REQUIRES_DECISION]

    report_content = report_path.read_text(encoding="utf-8")
    assert "REQUER DECISÃO" in report_content
    assert "VERIFICAR" in report_content
    assert "INFORMATIVO" in report_content