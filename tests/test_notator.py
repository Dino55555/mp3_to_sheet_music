import pytest
from notation.notator import Notator
from models.pitch_spelling import PitchSpelling
from music_theory import (
    key_signature_alterations,
    diatonic_letter_for,
    spell_pitch,
    SHARP_ORDER,
    FLAT_ORDER,
    NATURAL_PITCH_CLASS,
    TONIC_NAMES,
    accidents_of_major_tonic,
)
from models.compass import (Compass, TimeSignature, KeySignature, TonalMode)
from models.voice import Voice
from models.note import Note
from Compass.piece import Piece
from Compass.instrument import Instrument
from config import Config
from signaling.signaler import Signaler
from orchestrator import Orchestrator
from cleaning.cleaner import Cleaner
from structure.structural_detector import StructuralDetector
from voices.voice_separator import VoiceSeparator
from voices.octave_corrector import OctaveCorrector
from rhythm.quantizer import Quantizer
from completeness.completeness_detector import CompletenessDetector
from models.raw_signals import RawSignals
from tests.fixtures import (
    voice_with_spurious_rearticulations,
    voice_with_real_repeated_attack,
    notes_diatonic_in_d_major,
    notes_chromatic_ascending_and_descending,
    regular_4_4_beats,
)


def test_deve_unir_confirma_sequencia_valida():
    notator = Notator()
    voice = voice_with_spurious_rearticulations()

    assert notator._should_merge(voice.notes[0], voice.notes[1]) is True

def test_deve_unir_rejeita_gap_real():
    notator = Notator()
    current = Note(60, 0.0, 0.3, 0.7)
    following = Note(60, 0.5, 0.8, 0.7)

    assert notator._should_merge(current, following) is False

def test_deve_unir_rejeita_pico_de_intensidade():
    notator = Notator()
    voice = voice_with_real_repeated_attack()

    assert notator._should_merge(voice.notes[0], voice.notes[1]) is False

def test_deve_unir_rejeita_nota_de_ornamento():
    notator = Notator()
    current = Note(60, 0.0, 0.3, 0.7, is_ornament=True)
    following = Note(60, 0.31, 0.6, 0.72)

    assert notator._should_merge(current, following) is False

    current2 = Note(60, 0.0, 0.3, 0.7)
    following2 = Note(60, 0.31, 0.6, 0.72, is_ornament=True)

    assert notator._should_merge(current2, following2) is False

def test_unir_grupo_intensidade_e_o_maximo_do_grupo():
    notator = Notator()
    group = [
        Note(60, 0.0, 0.3, 0.5),
        Note(60, 0.3, 0.6, 0.8),
        Note(60, 0.6, 0.9, 0.6),
    ]

    merged = notator._merge_group(group)

    assert merged.pitch == 60
    assert merged.onset == pytest.approx(0.0)
    assert merged.offset == pytest.approx(0.9)
    assert merged.magnitude == pytest.approx(0.8)

def test_unir_grupo_confianca_e_o_minimo_do_grupo():
    notator = Notator()
    group = [
        Note(60, 0.0, 0.3, 0.5,
             reliability_existence=0.9, reliability_highness=1.0,
             reliability_duration=0.8, reliability_voice=1.0),
        Note(60, 0.3, 0.6, 0.6,
             reliability_existence=0.7, reliability_highness=0.95,
             reliability_duration=1.0, reliability_voice=0.85),
    ]

    merged = notator._merge_group(group)

    assert merged.reliability_existence == pytest.approx(0.7)
    assert merged.reliability_highness == pytest.approx(0.95)
    assert merged.reliability_duration == pytest.approx(0.8)
    assert merged.reliability_voice == pytest.approx(0.85)

def test_unir_reariculacoes_funde_sequencia_de_quatro():
    notator = Notator()
    voice = voice_with_spurious_rearticulations()

    notator._merge_rearticulations(voice)

    assert len(voice.notes) == 1
    assert voice.notes[0].onset == pytest.approx(0.0)
    assert voice.notes[0].offset == pytest.approx(1.2)

def test_unir_reariculacoes_preserva_nota_isolada_sem_grupo():
    notator = Notator()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(64, 1.0, 1.5, 0.8))

    notator._merge_rearticulations(voice)

    assert len(voice.notes) == 2
    assert voice.notes[0].pitch == 60
    assert voice.notes[1].pitch == 64

def test_alteracoes_da_armadura_re_maior_tem_fa_e_do_sustenidos():
    key_signature = KeySignature(2, "D", TonalMode.MAJOR)

    alterations = key_signature_alterations(key_signature)

    assert alterations['F'] == 1
    assert alterations['C'] == 1
    assert alterations['G'] == 0
    assert alterations['D'] == 0

@pytest.mark.parametrize("major_tonic", range(12))
def test_alteracoes_da_armadura_fa_maior_tem_si_bemol(major_tonic):
    accidents = accidents_of_major_tonic(major_tonic)
    key_signature = KeySignature(accidents, TONIC_NAMES[major_tonic], TonalMode.MAJOR)

    alterations = key_signature_alterations(key_signature)

    if accidents > 0:
        sharp_letters = set(SHARP_ORDER[:accidents])
        for letter in sharp_letters:
            assert alterations[letter] == 1
        for letter in set(NATURAL_PITCH_CLASS) - sharp_letters:
            assert alterations[letter] == 0
    elif accidents < 0:
        flat_letters = set(FLAT_ORDER[:abs(accidents)])
        for letter in flat_letters:
            assert alterations[letter] == -1
        for letter in set(NATURAL_PITCH_CLASS) - flat_letters:
            assert alterations[letter] == 0
    else:
        assert all(value == 0 for value in alterations.values())

def test_letra_diatonica_para_encontra_nota_pertencente_a_escala():
    key_signature = KeySignature(2, "D", TonalMode.MAJOR)
    alterations = key_signature_alterations(key_signature)

    letter = diatonic_letter_for(6, alterations)   # F# (pitch class 6)

    assert letter == 'F'

def test_letra_diatonica_para_retorna_none_para_nota_cromatica():
    key_signature = KeySignature(0, "C", TonalMode.MAJOR)
    alterations = key_signature_alterations(key_signature)

    letter = diatonic_letter_for(1, alterations)   # C#/Db, fora de Do maior

    assert letter is None

def test_grafar_altura_nota_diatonica_ignora_direcao_melodica():
    key_signature = KeySignature(2, "D", TonalMode.MAJOR)

    spelling_ascending = spell_pitch(66, key_signature, 'ascending')   # F#4
    spelling_descending = spell_pitch(66, key_signature, 'descending')

    assert spelling_ascending == PitchSpelling('F', 1, 4)
    assert spelling_descending == PitchSpelling('F', 1, 4)

def test_grafar_altura_cromatica_ascendente_usa_sustenido():
    key_signature = KeySignature(0, "C", TonalMode.MAJOR)

    spelling = spell_pitch(61, key_signature, 'ascending')

    assert spelling == PitchSpelling('C', 1, 4)

def test_grafar_altura_cromatica_descendente_usa_bemol():
    key_signature = KeySignature(0, "C", TonalMode.MAJOR)

    spelling = spell_pitch(61, key_signature, 'descending')

    assert spelling == PitchSpelling('D', -1, 4)

def test_grafar_altura_cromatica_sem_direcao_usa_sustenido_por_padrao():
    key_signature = KeySignature(0, "C", TonalMode.MAJOR)

    spelling = spell_pitch(61, key_signature, None)

    assert spelling == PitchSpelling('C', 1, 4)

def test_direcao_melodica_usa_anterior_quando_disponivel():
    notator = Notator()
    voice = Voice()
    n1 = Note(60, 0.0, 0.5, 0.8)
    n2 = Note(64, 0.5, 1.0, 0.8)
    voice.add_note(n1)
    voice.add_note(n2)

    assert notator._melodic_direction(n2, voice) == 'ascending'

def test_direcao_melodica_usa_seguinte_na_primeira_nota_da_voz():
    notator = Notator()
    voice = Voice()
    n1 = Note(60, 0.0, 0.5, 0.8)
    n2 = Note(64, 0.5, 1.0, 0.8)
    voice.add_note(n1)
    voice.add_note(n2)

    #n1 e a primeira nota da voz (sem anterior) - usa n2 como referencia
    assert notator._melodic_direction(n1, voice) == 'descending'

def test_processar_atribui_grafia_a_todas_as_notas_apos_uniao():
    notator = Notator()
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(2, "D", TonalMode.MAJOR))
    piece.add_compass(compass)
    voice = Voice()
    for note in notes_diatonic_in_d_major():
        voice.add_note(note)
    piece.add_voice(voice)

    notator.process(piece, config, signaler)

    assert all(n.graphy is not None for n in piece.all_notes())

    f_sharp_note = next(n for n in piece.all_notes() if n.pitch == 66)
    c_sharp_note = next(n for n in piece.all_notes() if n.pitch == 73)
    assert f_sharp_note.graphy == PitchSpelling('F', 1, 4)
    assert c_sharp_note.graphy == PitchSpelling('C', 1, 5)

def test_processar_atribui_sustenido_ascendente_e_bemol_descendente_via_contexto_real():
    notator = Notator()
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass)
    voice = Voice()
    for note in notes_chromatic_ascending_and_descending():
        voice.add_note(note)
    piece.add_voice(voice)

    notator.process(piece, config, signaler)

    ascending_chromatic = next(n for n in voice.notes if n.pitch == 61 and n.onset < 2.0)
    descending_chromatic = next(n for n in voice.notes if n.pitch == 61 and n.onset >= 2.0)

    assert ascending_chromatic.graphy == PitchSpelling('C', 1, 4)
    assert descending_chromatic.graphy == PitchSpelling('D', -1, 4)

def test_orquestrador_completo_ate_aqui_integra_corretamente():
    config = Config()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    voice.add_note(Note(60, 0.0, 1.0, 0.8))   # C
    voice.add_note(Note(62, 1.0, 2.0, 0.8))   # D
    voice.add_note(Note(64, 2.0, 3.0, 0.8))   # E
    voice.add_note(Note(60, 3.0, 4.0, 0.8))   # C
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
    result = orchestrator.process(piece)

    assert result is piece
    for note in result.all_notes():
        assert note.graphy is not None
        compass = result.compass_at_instant(note.onset)
        alterations = key_signature_alterations(compass.armor)
        letter = diatonic_letter_for(note.pitch % 12, alterations)
        if letter is not None:
            assert note.graphy.letter_class == letter
            assert note.graphy.alteration == alterations[letter]