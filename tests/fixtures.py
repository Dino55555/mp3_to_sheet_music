from Compass.instrument import Instrument
from models.voice import (Voice, PaperVoice)
from models.note import Note
from models.compass import(Compass, TimeSignature, KeySignature, TonalMode)
from Compass.piece import Piece
from models.raw_signals import Beat


def create_example_piece() -> Piece:
    instrument = Instrument.piano()
    piece = Piece(instrument=instrument)
    compass = Compass(
        index=1,
        begin_time=0.0,
        end_time=2.0,
        formula=TimeSignature(4, 4),
        armor=KeySignature(
            accidents_qunatity=0,
            tonic="C",
            mode=TonalMode.MAJOR
        )
    )
    piece.add_compass(compass)
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(62, 0.5, 1.0, 0.8))
    voice.add_note(Note(64, 1.0, 1.5, 0.8))
    piece.add_voice(voice)

    return piece

def create_piece_with_spurious_note() -> Piece:
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    main_note = Note(pitch=60, onset=0.0, offset=1.0, magnitude=1.0)
    spurious_note = Note(pitch=72,onset=0.0,offset=1.0,magnitude=0.3)
    voice.add_note(main_note)
    voice.add_note(spurious_note)
    piece.add_voice(voice)
    compass = Compass(
        index=1,
        begin_time=0.0,
        end_time=1.0,
        formula=TimeSignature(4, 4),
        armor=KeySignature(accidents_qunatity=0, tonic="C", mode=TonalMode.MAJOR)
    )
    piece.add_compass(compass)
    return piece

def regular_4_4_beats(measures: int) -> list[Beat]:
    beats = []
    instant = 0.0
    for _ in range(measures):
        beats.append(Beat(instant, True, 1.0))
        instant += 1
        beats.append(Beat(instant, False, 1.0))
        instant += 1
        beats.append(Beat(instant, False, 1.0))
        instant += 1
        beats.append(Beat(instant, False, 1.0))
        instant += 1

    return beats

def notes_in_d_major() -> list[Note]:
    return [
        Note(62, 0.00, 0.50, 0.8),   # D
        Note(63, 0.20, 0.23, 0.8),   # D# - cromatica de passagem, peso pequeno
        Note(64, 0.50, 1.00, 0.8),   # E
        Note(66, 1.00, 1.50, 0.8),   # F#
        Note(67, 1.50, 2.00, 0.8),   # G
        Note(68, 1.70, 1.73, 0.8),   # G# - cromatica de passagem, peso pequeno
        Note(69, 2.00, 2.50, 0.8),   # A
        Note(71, 2.50, 3.00, 0.8),   # B
        Note(73, 3.00, 3.50, 0.8),   # C#
        Note(74, 3.50, 4.00, 0.8),   # D
    ]

def notes_in_c_mixolydian() -> list[Note]:
    return[
        Note(60, 0.00, 0.50, 0.8),   # C
        Note(62, 0.50, 1.00, 0.8),   # D
        Note(64, 1.00, 1.50, 0.8),   # E
        Note(65, 1.50, 2.00, 0.8),   # F
        Note(67, 2.00, 2.50, 0.8),   # G
        Note(69, 2.50, 3.00, 0.8),   # A
        Note(70, 3.00, 3.50, 0.8),   # Bb
        Note(72, 3.50, 4.00, 0.8),   # C
    ]

def notes_in_a_minor_natural() -> list[Note]:
    return[
        Note(57, 0.00, 0.50, 0.8),   # A
        Note(59, 0.50, 1.00, 0.8),   # B
        Note(60, 1.00, 1.50, 0.8),   # C
        Note(62, 1.50, 2.00, 0.8),   # D
        Note(64, 2.00, 2.50, 0.8),   # E
        Note(65, 2.50, 3.00, 0.8),   # F
        Note(67, 3.00, 3.50, 0.8),   # G
        Note(69, 3.50, 4.00, 0.8),   # A
    ]

def create_piece_with_isolated_chromatic_note():
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    voice.add_note(Note(60, 0.00, 0.50, 0.8))   # C
    voice.add_note(Note(62, 0.50, 1.00, 0.8))   # D
    voice.add_note(Note(73, 1.00, 1.08, 0.8))   # C# uma oitava acima - isolada, curta
    voice.add_note(Note(64, 1.08, 1.58, 0.8))   # E
    voice.add_note(Note(67, 1.58, 2.08, 0.8))   # G
    piece.add_voice(voice)

    return piece

def notes_clear_melody_over_accompaniment() -> list[Note]:
    
    return [
        # melodia
        Note(60, 0.0, 0.5, 0.8),
        Note(62, 1.0, 2.0, 0.8),
        Note(64, 2.0, 2.75, 0.8),
        Note(65, 3.0, 4.25, 0.8),
        # acompanhamento (pedal repetido, mesma altura)
        Note(55, 0.0, 1.0, 0.8),
        Note(55, 1.0, 2.0, 0.8),
        Note(55, 2.0, 3.0, 0.8),
        Note(55, 3.0, 4.0, 0.8),
    ]


def notes_melody_temporarily_descending() -> list[Note]:
    
    return [
        Note(72, 0.0, 1.0, 0.8),   # melodia
        Note(60, 0.0, 1.0, 0.8),   # acompanhamento
        Note(71, 1.0, 2.0, 0.8),   # melodia
        Note(60, 1.0, 2.0, 0.8),   # acompanhamento
        Note(48, 2.0, 3.0, 0.8),   # melodia - o mergulho (uma oitava abaixo)
        Note(68, 2.0, 3.0, 0.8),   # acompanhamento - acorde mais agudo neste instante
        Note(71, 3.0, 4.0, 0.8),   # melodia
        Note(60, 3.0, 4.0, 0.8),   # acompanhamento
        Note(72, 4.0, 5.0, 0.8),   # melodia
        Note(60, 4.0, 5.0, 0.8),   # acompanhamento
    ]


def notes_ambiguous_counterpoint() -> list[Note]:
    
    return [
        # linha superior (fica com A4 como melodia)
        Note(72, 0.0, 0.5, 0.8),
        Note(74, 1.0, 2.0, 0.8),
        Note(73, 2.0, 2.75, 0.8),
        Note(75, 3.0, 4.25, 0.8),
        # linha inferior (fica com A4 como acompanhamento)
        Note(60, 0.0, 1.25, 0.8),
        Note(62, 1.0, 1.5, 0.8),
        Note(61, 2.0, 3.0, 0.8),
        Note(63, 3.0, 3.75, 0.8),
    ]


def notes_with_marked_vocal_origin() -> list[Note]:
    
    return [
        Note(55, 0.0, 1.0, 0.8, vocal_origin_identified=True),
        Note(57, 1.0, 2.0, 0.8, vocal_origin_identified=True),
        Note(72, 0.0, 1.0, 0.8),
        Note(74, 1.0, 2.0, 0.8),
    ]

def octave_leap_isolated_voice() -> Voice:
    #Salto de oitava isolado (sobe e retorna) dentro de contorno
    #predominantemente por grau conjunto - A10 deve corrigir
    voice = Voice()
    pitches = [60, 62, 64, 76, 65, 67]
    onset = 0.0
    for pitch in pitches:
        voice.add_note(Note(pitch, onset, onset + 0.5, 0.8))
        onset += 0.5
    return voice


def sustained_octave_leap_voice() -> Voice:
    #Salto de oitava que se sustenta (nao retorna ao registro original) -
    voice = Voice()
    pitches = [60, 62, 64, 76, 78, 80]
    onset = 0.0
    for pitch in pitches:
        voice.add_note(Note(pitch, onset, onset + 0.5, 0.8))
        onset += 0.5
    return voice


def accompaniment_with_note_off_center() -> Voice:
    #Um acorde com uma nota isolada muito acima do centro do proprio acorde,
    #seguido de outro acorde compacto sem outlier - proporcao de candidatas
    #baixa, entao a correcao de A11 deve ser aplicada so na nota isolada
    voice = Voice(paper=PaperVoice.ACCOMPANIMENT)
    voice.add_note(Note(40, 0.0, 1.0, 0.8))
    voice.add_note(Note(43, 0.0, 1.0, 0.8))
    voice.add_note(Note(47, 0.0, 1.0, 0.8))
    voice.add_note(Note(72, 0.0, 1.0, 0.8))
    voice.add_note(Note(40, 1.0, 2.0, 0.8))
    voice.add_note(Note(43, 1.0, 2.0, 0.8))
    voice.add_note(Note(47, 1.0, 2.0, 0.8))
    return voice


def accompaniment_with_consistent_open_voicing() -> Voice:
    #Varios acordes com o mesmo spread aberto (25 semitons) de forma
    #consistente - proporcao alta de candidatas, entao A11 nao deve
    #aplicar nenhuma correcao
    voice = Voice(paper=PaperVoice.ACCOMPANIMENT)
    onset = 0.0
    for _ in range(3):
        voice.add_note(Note(40, onset, onset + 1.0, 0.8))
        voice.add_note(Note(65, onset, onset + 1.0, 0.8))
        onset += 1.0
    return voice


def voice_with_note_isolated_out_of_range() -> Voice:
    #Nota isolada uma oitava abaixo da tessitura do piano (range_min=21),
    #com vizinhas dentro da faixa
    voice = Voice()
    voice.add_note(Note(30, 0.0, 0.5, 0.8))   # dentro da faixa
    voice.add_note(Note(15, 0.5, 1.0, 0.8))   # fora da faixa
    voice.add_note(Note(32, 1.0, 1.5, 0.8))   # dentro da faixa
    return voice

def _single_measure_piece() -> Piece:
    #Peca auxiliar com um unico compasso 4/4 de 4.0s (grid a cada 0.25s
    #com divisions_per_beat=4), usada pelas fixtures de quantizacao
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


def note_with_small_deviation() -> tuple[Piece, Note]:
    #Onset e offset ambos a 0.02s (20ms) do ponto de grid mais proximo -
    #B9: ajuste silencioso nos dois extremos
    piece = _single_measure_piece()
    note = Note(60, 0.23, 0.73, 0.8)
    return piece, note


def note_with_ambiguous_deviation() -> tuple[Piece, Note]:
    #Onset a meio caminho entre um tempo (0.0) e sua subdivisao vizinha
    #(0.25) - B10: escolhe o ponto de maior nivel metrico (o tempo).
    #Offset exatamente no grid (0.75), sem ambiguidade
    piece = _single_measure_piece()
    note = Note(62, 0.13, 0.75, 0.8)
    return piece, note


def note_with_moderate_deviation() -> tuple[Piece, Note]:
    #Onset e offset com desvio nem pequeno nem ambiguo (diferenca entre as
    #duas distancias maior que a tolerancia de empate) - ajustado para o
    #ponto mais proximo, com confianca intermediaria, sem sinalizacao
    piece = _single_measure_piece()
    note = Note(64, 0.16, 0.66, 0.8)
    return piece, note


def long_note_crossing_measure() -> tuple[Piece, Note]:
    #Nota longa cujo onset cai no primeiro compasso (exatamente no grid) e
    #o offset cai no segundo compasso (desvio pequeno) - cada ponta deve
    #ser quantizada contra o grid do seu proprio compasso
    piece = Piece(instrument=Instrument.piano())
    compass1 = Compass(
        index=1, begin_time=0.0, end_time=4.0,
        formula=TimeSignature(4, 4), armor=KeySignature(0, "C", TonalMode.MAJOR),
    )
    compass2 = Compass(
        index=2, begin_time=4.0, end_time=8.0,
        formula=TimeSignature(4, 4), armor=KeySignature(0, "C", TonalMode.MAJOR),
    )
    piece.add_compass(compass1)
    piece.add_compass(compass2)
    note = Note(67, 3.5, 4.77, 0.8)
    return piece, note