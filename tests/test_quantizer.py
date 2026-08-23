import pytest
from rhythm.quantizer import (
    Quantizer,
    SMALL_THRESHOLD_FRACTION,
    AMBIGUITY_TOLERANCE_FRACTION,
    MODERATE_DEVIATION_CONFIDENCE,
    AMBIGUOUS_TIME_CONFIDENCE,
    TERNARY_DIVISIONS,
)
from rhythm.rhythmic_grid import (build_grid, closest_index)
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
from models.raw_signals import RawSignals
from tests.fixtures import (
    note_with_small_deviation,
    note_with_ambiguous_deviation,
    note_with_moderate_deviation,
    long_note_crossing_measure,
    grace_note_voice,
    trill_voice,
    small_gap_voice,
    consistent_staccato_voice,
    isolated_staccato_voice,
    consistent_swing_voice,
    compass_with_constant_triplets,
    compass_with_isolated_triplet,
    sequence_with_sustained_ternary_change,
    regular_4_4_beats,
)


def _single_measure_piece() -> Piece:
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(
        index=1,
        begin_time=0.0,
        end_time=4.0,
        formula=TimeSignature(4, 4),
        armor=KeySignature(0, "C", TonalMode.MAJOR),
    )
    piece.add_compass(compass)
    return piece


def test_compass_at_instant_finds_correct_compass():
    piece = Piece(instrument=Instrument.piano())
    compass1 = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    compass2 = Compass(2, 4.0, 8.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass1)
    piece.add_compass(compass2)

    assert piece.compass_at_instant(5.5) is compass2
    assert piece.compass_at_instant(1.0) is compass1

def test_compass_at_instant_edge_case_end_of_last_compass():
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)

    assert piece.compass_at_instant(4.0) is compass

def test_compass_at_instant_raises_error_outside_any_compass():
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)

    with pytest.raises(ValueError):
        piece.compass_at_instant(10.0)

def test_build_grid_has_correct_number_of_points():
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))

    grid = build_grid(compass, 4)

    assert len(grid) == 4 * 4 + 1

def test_build_grid_includes_both_extremes():
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))

    grid = build_grid(compass, 4)

    assert grid[0] == pytest.approx(0.0)
    assert grid[-1] == pytest.approx(4.0)

def test_two_closest_identifies_correct_pair():
    quantizer = Quantizer()
    grid = [0.0, 1.0, 2.0, 3.0, 4.0]

    closest, second_closest = quantizer._two_closest(2.7, grid)

    assert closest == 3
    assert second_closest == 2

@pytest.mark.parametrize("index_in_grid,divisions,expected_level", [
    (0, 4, 3),
    (4, 4, 3),
    (8, 4, 3),
    (2, 4, 1),
    (1, 4, 0),
    (3, 4, 0),
])
def test_metric_level_beat_is_simpler_than_subdivision(index_in_grid, divisions, expected_level):
    quantizer = Quantizer()

    assert quantizer._metric_level(index_in_grid, divisions) == expected_level

def test_quantize_instant_small_deviation_adjusts_silently():
    quantizer = Quantizer()
    piece, note = note_with_small_deviation()

    quantized, confidence, ambiguous = quantizer._quantize_instant(note.onset, piece, 4)

    assert quantized == pytest.approx(0.25)
    assert confidence == 1.0
    assert ambiguous is False

def test_quantize_instant_ambiguous_deviation_chooses_higher_metric_level():
    quantizer = Quantizer()
    piece, note = note_with_ambiguous_deviation()

    quantized, confidence, ambiguous = quantizer._quantize_instant(note.onset, piece, 4)

    assert quantized == pytest.approx(0.0)
    assert confidence == AMBIGUOUS_TIME_CONFIDENCE
    assert ambiguous is True

def test_quantize_instant_moderate_deviation_without_signaling():
    quantizer = Quantizer()
    piece, note = note_with_moderate_deviation()

    quantized, confidence, ambiguous = quantizer._quantize_instant(note.onset, piece, 4)

    assert quantized == pytest.approx(0.25)
    assert confidence == MODERATE_DEVIATION_CONFIDENCE
    assert ambiguous is False

def test_quantize_note_confidence_is_minimum_of_onset_and_offset():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = _single_measure_piece()
    note = Note(60, 0.23, 3.13, 0.8)

    quantizer._quantize_note(note, piece, 4, signaler)

    assert note.reliability_duration == AMBIGUOUS_TIME_CONFIDENCE

def test_quantize_note_generates_at_most_one_signal():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = _single_measure_piece()
    note = Note(60, 0.13, 1.13, 0.8)

    quantizer._quantize_note(note, piece, 4, signaler)

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.LOW_CONFIDENCE_QUANTIZATION
    assert signals[0].level == SeverityLevel.VERIFY

def test_quantize_note_offset_in_different_compass_than_onset():
    quantizer = Quantizer()
    signaler = Signaler()
    piece, note = long_note_crossing_measure()

    quantizer._quantize_note(note, piece, 4, signaler)

    assert note.onset == pytest.approx(3.5)
    assert note.offset == pytest.approx(4.75)
    assert note.reliability_duration == 1.0
    assert signaler.all() == []

def test_classify_ornaments_marks_short_note_close_in_pitch():
    quantizer = Quantizer()
    piece, voice = grace_note_voice()

    quantizer._classify_ornaments(voice, piece, 4)

    assert voice.notes[0].is_ornament is False
    assert voice.notes[1].is_ornament is True
    assert voice.notes[2].is_ornament is False

def test_classify_ornaments_ignores_short_note_distant_in_pitch():
    quantizer = Quantizer()
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(72, 0.5, 0.55, 0.8))
    voice.add_note(Note(60, 0.55, 1.05, 0.8))

    quantizer._classify_ornaments(voice, piece, 4)

    assert voice.notes[1].is_ornament is False

def test_classify_ornaments_ignores_normal_duration_note():
    quantizer = Quantizer()
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(61, 0.5, 1.0, 0.8))
    voice.add_note(Note(60, 1.0, 1.5, 0.8))

    quantizer._classify_ornaments(voice, piece, 4)

    assert all(not n.is_ornament for n in voice.notes)

def test_detect_trills_confirms_alternating_sequence():
    quantizer = Quantizer()
    voice = trill_voice()

    quantizer._detect_trills(voice)

    assert all(n.is_ornament for n in voice.notes)

def test_process_gaps_extends_small_gap():
    quantizer = Quantizer()
    piece, voice = small_gap_voice()

    quantizer._process_gaps(voice, piece, 4)

    assert voice.notes[0].offset == pytest.approx(voice.notes[1].onset)
    assert voice.notes[0].offset == pytest.approx(0.52)

def test_process_gaps_marks_staccato_in_consistent_pattern():
    quantizer = Quantizer()
    piece, voice = consistent_staccato_voice()

    quantizer._process_gaps(voice, piece, 4)

    assert voice.notes[0].staccato is True
    assert voice.notes[1].staccato is True
    assert voice.notes[2].staccato is True
    assert voice.notes[3].staccato is False
    assert voice.notes[0].offset == pytest.approx(0.30)
    assert voice.notes[1].onset == pytest.approx(0.38)

def test_process_gaps_ignores_isolated_staccato_candidate():
    quantizer = Quantizer()
    piece, voice = isolated_staccato_voice()

    quantizer._process_gaps(voice, piece, 4)

    assert voice.notes[0].staccato is False
    assert voice.notes[0].offset == pytest.approx(0.30)

def test_process_gaps_never_alters_pair_involving_ornament():
    quantizer = Quantizer()
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.00, 0.48, 0.8))
    voice.add_note(Note(62, 0.50, 0.55, 0.8, is_ornament=True))
    voice.add_note(Note(64, 0.60, 1.00, 0.8))

    quantizer._process_gaps(voice, piece, 4)

    assert voice.notes[0].offset == pytest.approx(0.48)
    assert voice.notes[1].onset == pytest.approx(0.50)
    assert voice.notes[1].offset == pytest.approx(0.55)
    assert voice.notes[2].onset == pytest.approx(0.60)
    assert all(not n.staccato for n in voice.notes)

def test_process_gaps_leaves_large_gap_unchanged():
    quantizer = Quantizer()
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.3, 0.8))
    voice.add_note(Note(62, 0.6, 0.9, 0.8))

    quantizer._process_gaps(voice, piece, 4)

    assert voice.notes[0].offset == pytest.approx(0.3)
    assert voice.notes[0].staccato is False
    assert voice.notes[1].staccato is False

def test_detect_groove_patterns_identifies_consistent_deviation():
    quantizer = Quantizer()
    piece, voice = consistent_swing_voice()

    patterns = quantizer._detect_groove_patterns(voice, piece, 4)

    assert 2 in patterns
    assert patterns[2] == pytest.approx(0.05)

def test_detect_groove_patterns_ignores_deviation_too_small_to_matter():
    quantizer = Quantizer()
    piece = _single_measure_piece()
    voice = Voice()
    for onset in (0.5, 1.5, 2.5, 3.5):
        note = Note(60, onset, onset + 0.2, 0.8)
        note.raw_onset = onset + 0.02
        note.raw_offset = onset + 0.22
        voice.add_note(note)

    patterns = quantizer._detect_groove_patterns(voice, piece, 4)

    assert patterns == {}

def test_detect_groove_patterns_ignores_group_with_few_notes():
    quantizer = Quantizer()
    piece = _single_measure_piece()
    voice = Voice()
    for onset in (0.5, 1.5, 2.5):
        note = Note(60, onset, onset + 0.2, 0.8)
        note.raw_onset = onset + 0.05
        note.raw_offset = onset + 0.25
        voice.add_note(note)

    patterns = quantizer._detect_groove_patterns(voice, piece, 4)

    assert patterns == {}

def test_detect_groove_patterns_ignores_inconsistent_deviation():
    quantizer = Quantizer()
    piece = _single_measure_piece()
    voice = Voice()
    deviations = [0.02, 0.10, 0.02, 0.10]
    for onset, deviation in zip((0.5, 1.5, 2.5, 3.5), deviations):
        note = Note(60, onset, onset + 0.2, 0.8)
        note.raw_onset = onset + deviation
        note.raw_offset = onset + 0.2 + deviation
        voice.add_note(note)

    patterns = quantizer._detect_groove_patterns(voice, piece, 4)

    assert patterns == {}

def test_detect_groove_patterns_ignores_ornament_notes():
    quantizer = Quantizer()
    piece = _single_measure_piece()
    voice = Voice()
    for onset in (0.5, 1.5, 2.5, 3.5):
        note = Note(60, onset, onset + 0.2, 0.8, is_ornament=True)
        note.raw_onset = onset + 0.05
        note.raw_offset = onset + 0.25
        voice.add_note(note)

    patterns = quantizer._detect_groove_patterns(voice, piece, 4)

    assert patterns == {}

def test_apply_groove_updates_confidence_without_altering_onset():
    quantizer = Quantizer()
    signaler = Signaler()
    piece, voice = consistent_swing_voice()
    original_onsets = [n.onset for n in voice.notes]
    original_offsets = [n.offset for n in voice.notes]

    patterns = quantizer._detect_groove_patterns(voice, piece, 4)
    quantizer._apply_groove(voice, piece, patterns, 4, signaler)

    for note in voice.notes:
        assert note.reliability_duration == 1.0
    assert [n.onset for n in voice.notes] == original_onsets
    assert [n.offset for n in voice.notes] == original_offsets

def test_apply_groove_marks_compass_with_feel_indication():
    quantizer = Quantizer()
    signaler = Signaler()
    piece, voice = consistent_swing_voice()

    patterns = quantizer._detect_groove_patterns(voice, piece, 4)
    quantizer._apply_groove(voice, piece, patterns, 4, signaler)

    assert piece.compasses[0].feel_indication == "swing"

def test_quantize_note_preserves_raw_onset_and_raw_offset_via_capture():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = _single_measure_piece()
    voice = Voice()
    note = Note(60, 0.13, 0.66, 0.8)
    voice.add_note(note)

    quantizer._capture_raw_values(voice)
    quantizer._quantize_note(note, piece, 4, signaler)

    assert note.raw_onset == pytest.approx(0.13)
    assert note.raw_offset == pytest.approx(0.66)

def test_grupos_de_batida_simples_retorna_numerador():
    formula = TimeSignature(4, 4)

    assert formula.beat_groups() == 4

def test_grupos_de_batida_composta_divide_por_tres():
    formula = TimeSignature(12, 8, is_compound=True)

    assert formula.beat_groups() == 4

@pytest.mark.parametrize("numerator,denominator,expected_numerator,expected_denominator", [
    (4, 4, 12, 8),
    (3, 4, 9, 8),
    (2, 4, 6, 8),
])
def test_converter_para_composta_aplica_formula_padrao(numerator, denominator, expected_numerator, expected_denominator):
    formula = TimeSignature(numerator, denominator)

    converted = formula.convert_to_compound()

    assert converted.numerator == expected_numerator
    assert converted.denominator == expected_denominator
    assert converted.is_compound is True

def test_construir_grid_usa_grupos_de_batida_nao_numerador_bruto():
    compass = Compass(1, 0.0, 4.0, TimeSignature(12, 8, is_compound=True), KeySignature(0, "C", TonalMode.MAJOR))

    grid = build_grid(compass, TERNARY_DIVISIONS)

    assert len(grid) == 4 * TERNARY_DIVISIONS + 1

def test_indice_mais_proximo_extraido_preserva_comportamento_da_fase_11():
    grid = [0.0, 1.0, 2.0, 3.0, 4.0]

    assert closest_index(2.7, grid) == 3

def test_erro_total_de_ajuste_soma_distancias_corretamente():
    quantizer = Quantizer()
    grid = [0.0, 0.5, 1.0, 1.5, 2.0]
    raw_onsets = [0.3, 0.7, 1.6]

    error = quantizer._total_fit_error(raw_onsets, grid)

    assert error == pytest.approx(0.5)

def test_classificar_metrica_do_compasso_identifica_ternario_dominante():
    quantizer = Quantizer()
    piece = compass_with_constant_triplets()
    quantizer._capture_raw_values(piece.voices[0])

    result = quantizer._classify_compass_meter(piece.compasses[0], piece, 4)

    assert result is True

def test_classificar_metrica_do_compasso_identifica_binario_dominante():
    quantizer = Quantizer()
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)
    voice = Voice()
    for group_index in range(4):
        group_start = group_index * 1.0
        voice.add_note(Note(60, group_start + 0.25, group_start + 0.30, 0.8))
        voice.add_note(Note(60, group_start + 0.50, group_start + 0.55, 0.8))
    piece.add_voice(voice)
    quantizer._capture_raw_values(voice)

    result = quantizer._classify_compass_meter(compass, piece, 4)

    assert result is False

def test_classificar_metrica_do_compasso_ignora_grupo_com_poucas_notas():
    quantizer = Quantizer()
    piece = compass_with_constant_triplets()
    voice = piece.voices[0]
    del voice.notes[1]
    quantizer._capture_raw_values(voice)

    result = quantizer._classify_compass_meter(piece.compasses[0], piece, 4)

    assert result is True

def test_classificar_metrica_do_compasso_retorna_none_sem_grupos_avaliaveis():
    quantizer = Quantizer()
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)
    voice = Voice()
    piece.add_voice(voice)

    result = quantizer._classify_compass_meter(compass, piece, 4)

    assert result is None

def test_resolver_metrica_composta_ignora_mudanca_isolada():
    quantizer = Quantizer()
    signaler = Signaler()
    config = Config()
    piece = compass_with_isolated_triplet()
    for voice in piece.voices:
        quantizer._capture_raw_values(voice)

    quantizer._resolve_compound_meter(piece, config, signaler)

    assert piece.compasses[0].formula.is_compound is False
    assert piece.compasses[1].formula.is_compound is False
    assert piece.compasses[2].formula.is_compound is False

def test_resolver_metrica_composta_adota_mudanca_sustentada():
    quantizer = Quantizer()
    signaler = Signaler()
    config = Config()
    piece = sequence_with_sustained_ternary_change()
    for voice in piece.voices:
        quantizer._capture_raw_values(voice)

    quantizer._resolve_compound_meter(piece, config, signaler)

    assert piece.compasses[0].formula.is_compound is False
    assert piece.compasses[1].formula.is_compound is True
    assert piece.compasses[1].formula.numerator == 12
    assert piece.compasses[1].formula.denominator == 8
    assert piece.compasses[2].formula.is_compound is True

def test_resolver_metrica_composta_ignora_compassos_de_tempo_livre():
    quantizer = Quantizer()
    signaler = Signaler()
    config = Config()
    piece = sequence_with_sustained_ternary_change()
    piece.compasses[1].free_time = True
    original_formula = piece.compasses[1].formula
    for voice in piece.voices:
        quantizer._capture_raw_values(voice)

    quantizer._resolve_compound_meter(piece, config, signaler)

    assert piece.compasses[1].formula is original_formula
    assert piece.compasses[1].formula.is_compound is False

def test_requantizar_compasso_atualiza_onset_offset_contra_grid_ternario():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(12, 8, is_compound=True), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)
    voice = Voice()
    note = Note(60, 0.3, 0.63, 0.8)
    #onset e offset caem exatamente em dois pontos distintos do grid
    #ternario (0.0 e 2/3) - sem ambiguidade, sem colisao, testando
    #especificamente o caminho de sucesso da requantizacao
    note.raw_onset, note.raw_offset = 0.0, 2 / 3
    voice.add_note(note)
    piece.add_voice(voice)

    quantizer._requantize_compass(compass, piece, TERNARY_DIVISIONS, signaler)

    assert note.onset == pytest.approx(0.0)
    assert note.offset == pytest.approx(2 / 3)
    assert note.reliability_duration == 1.0

def test_requantizar_compasso_nao_recaptura_onset_bruto():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(12, 8, is_compound=True), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)
    voice = Voice()
    note = Note(60, 0.25, 0.30, 0.8)
    note.raw_onset, note.raw_offset = 1 / 3, 1 / 3 + 0.05
    voice.add_note(note)
    piece.add_voice(voice)

    quantizer._requantize_compass(compass, piece, TERNARY_DIVISIONS, signaler)

    assert note.raw_onset == pytest.approx(1 / 3)
    assert note.raw_offset == pytest.approx(1 / 3 + 0.05)

def test_capturar_valores_brutos_e_idempotente():
    quantizer = Quantizer()
    voice = Voice()
    note = Note(60, 0.2, 0.4, 0.8)
    voice.add_note(note)

    quantizer._capture_raw_values(voice)
    original_raw_onset, original_raw_offset = note.raw_onset, note.raw_offset

    note.onset, note.offset = 0.25, 0.45
    quantizer._capture_raw_values(voice)

    assert note.raw_onset == original_raw_onset == pytest.approx(0.2)
    assert note.raw_offset == original_raw_offset == pytest.approx(0.4)

def test_orquestrador_completo_ate_aqui_integra_corretamente():
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()

    for group_index in range(4):
        group_start = group_index * 1.0
        voice.add_note(Note(60, group_start + 0.25, group_start + 0.30, 0.8))
        voice.add_note(Note(60, group_start + 0.50, group_start + 0.55, 0.8))

    for measure_start in (4.0, 8.0):
        for group_index in range(4):
            group_start = measure_start + group_index * 1.0
            voice.add_note(Note(60, group_start + 1 / 3, group_start + 1 / 3 + 0.05, 0.8))
            voice.add_note(Note(60, group_start + 2 / 3, group_start + 2 / 3 + 0.05, 0.8))

    piece.add_voice(voice)
    piece.raw_signals = RawSignals(regular_4_4_beats(3))

    orchestrator = Orchestrator(config, signaler)
    orchestrator.add_stage(Cleaner())
    orchestrator.add_stage(StructuralDetector())
    orchestrator.add_stage(VoiceSeparator())
    orchestrator.add_stage(OctaveCorrector())
    orchestrator.add_stage(Quantizer())
    result = orchestrator.process(piece)

    assert result is piece
    assert len(result.compasses) == 3
    assert result.compasses[0].formula.is_compound is False
    assert result.compasses[1].formula.is_compound is True
    assert result.compasses[1].formula.numerator == 12
    assert result.compasses[1].formula.denominator == 8
    assert result.compasses[2].formula.is_compound is True

def test_quantizar_nota_resolve_colisao_empurrando_offset():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = _single_measure_piece()
    #onset=0.24 e offset=0.26 colapsam para o mesmo ponto de grid (0.25)
    #quando quantizados de forma independente
    note = Note(60, 0.24, 0.26, 0.8)

    quantizer._quantize_note(note, piece, 4, signaler)

    assert note.onset == pytest.approx(0.25)
    assert note.offset == pytest.approx(0.5)

def test_quantizar_nota_colisao_reduz_confianca_tempo():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = _single_measure_piece()
    note = Note(60, 0.24, 0.26, 0.8)

    quantizer._quantize_note(note, piece, 4, signaler)

    assert note.reliability_duration == AMBIGUOUS_TIME_CONFIDENCE

def test_quantizar_nota_colisao_gera_sinalizacao_informativa():
    quantizer = Quantizer()
    signaler = Signaler()
    piece = _single_measure_piece()
    note = Note(60, 0.24, 0.26, 0.8)

    quantizer._quantize_note(note, piece, 4, signaler)

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.LOW_CONFIDENCE_QUANTIZATION
    assert signals[0].level == SeverityLevel.INFORMATIONAL