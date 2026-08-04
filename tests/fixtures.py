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
    #7 notas de Re maior (I-VII) mais 2 cromaticas de passagem de peso pequeno
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
    #7 notas de Do mixolidio: mesmas classes de Fa maior (usa Sib em vez de Si)
    return [
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
    #Escala de La menor natural, ascendente, terminando na tonica (sem sensivel)
    return [
        Note(57, 0.00, 0.50, 0.8),   # A
        Note(59, 0.50, 1.00, 0.8),   # B
        Note(60, 1.00, 1.50, 0.8),   # C
        Note(62, 1.50, 2.00, 0.8),   # D
        Note(64, 2.00, 2.50, 0.8),   # E
        Note(65, 2.50, 3.00, 0.8),   # F
        Note(67, 3.00, 3.50, 0.8),   # G
        Note(69, 3.50, 4.00, 0.8),   # A
    ]


def create_piece_with_isolated_chromatic_note() -> Piece:
    #Peca com fundo diatonico claro (Do maior) e uma nota cromatica isolada,
    #curta, sem conexao por grau conjunto com as vizinhas (A2)
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
    #Melodia claramente mais aguda (ascendente, ritmo variado) sobre um
    #acompanhamento estatico (pedal repetido) - A4 sozinho ja acerta,
    #A5 confirma sem inverter
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
    #Melodia com um mergulho breve (uma oitava abaixo) num unico compasso,
    #onde A4 momentaneamente troca os papeis das duas notas daquele instante -
    #mas o fluxo agregado da melodia ainda vence em A5, sem inversao completa
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
    #Duas linhas com comportamento igualmente melodico (saltos pequenos,
    #ritmo variado, sem repeticao) - A4 separa por registro, mas A5 encontra
    #pontuacao alta demais nas duas para decidir sozinho
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
    #Notas graves marcadas com origem vocal identificada devem virar melodia,
    #mesmo com notas agudas nao marcadas simultaneas - A6 sobrepoe A4/A5
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
    #A10 nao deve alterar
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


def grace_note_voice() -> tuple[Piece, Voice]:
    #Apojatura: nota muito curta (0.05s < limiar de 0.125s) entre duas
    #notas normais, a 2 semitons de distancia de ambas as vizinhas
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))    # normal
    voice.add_note(Note(62, 0.5, 0.55, 0.8))   # curta, proxima em altura
    voice.add_note(Note(64, 0.55, 1.05, 0.8))  # normal
    return piece, voice


def trill_voice() -> Voice:
    #Sequencia de 3 notas curtas alternando entre duas alturas, ja
    #marcadas como ornamento (como se _classificar_ornamentos ja tivesse
    #rodado) - _detect_trills nao deve alterar nada
    voice = Voice()
    voice.add_note(Note(62, 0.00, 0.05, 0.8, is_ornament=True))
    voice.add_note(Note(64, 0.05, 0.10, 0.8, is_ornament=True))
    voice.add_note(Note(62, 0.10, 0.15, 0.8, is_ornament=True))
    return voice


def small_gap_voice() -> tuple[Piece, Voice]:
    #Gap pequeno (0.02s < limiar de 0.0375s) entre duas notas normais -
    #B13 deve estender a primeira ate o onset da segunda
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.0, 0.5, 0.8))
    voice.add_note(Note(62, 0.52, 1.02, 0.8))
    return piece, voice


def consistent_staccato_voice() -> tuple[Piece, Voice]:
    #4 notas com 3 gaps moderados consecutivos e identicos (0.08s, entre
    #o limiar pequeno e o limiar maximo de staccato) - as 3 primeiras
    #notas devem ser confirmadas como staccato
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.00, 0.30, 0.8))
    voice.add_note(Note(62, 0.38, 0.68, 0.8))
    voice.add_note(Note(64, 0.76, 1.06, 0.8))
    voice.add_note(Note(65, 1.14, 1.44, 0.8))
    return piece, voice


def isolated_staccato_voice() -> tuple[Piece, Voice]:
    #Um unico gap moderado (0.08s), isolado - nao atinge o minimo de
    #repeticoes e nao deve ser confirmado como staccato
    piece = _single_measure_piece()
    voice = Voice()
    voice.add_note(Note(60, 0.00, 0.30, 0.8))
    voice.add_note(Note(62, 0.38, 0.68, 0.8))
    return piece, voice


def consistent_swing_voice() -> tuple[Piece, Voice]:
    #4 notas na mesma posicao metrica (2 de 4, fora do tempo forte), todas
    #com o mesmo desvio positivo (0.05s) entre onset bruto e onset
    #quantizado - B11 deve reconhecer como groove consistente
    piece = _single_measure_piece()
    voice = Voice()
    deviation = 0.05
    for onset in (0.5, 1.5, 2.5, 3.5):
        note = Note(60, onset, onset + 0.2, 0.8)
        note.raw_onset = onset + deviation
        note.raw_offset = onset + 0.2 + deviation
        voice.add_note(note)
    return piece, voice


def _binary_notes_for_group(group_start: float, pitch: int = 60) -> list[Note]:
    #2 notas alinhadas exatamente ao grid binario (subdivisao de 4) do grupo
    step = 1.0 / 4
    onset1 = group_start + step
    onset2 = group_start + 2 * step
    return [
        Note(pitch, onset1, onset1 + 0.05, 0.8),
        Note(pitch, onset2, onset2 + 0.05, 0.8),
    ]


def _ternary_notes_for_group(group_start: float, pitch: int = 60) -> list[Note]:
    #2 notas alinhadas exatamente ao grid ternario (subdivisao de 3) do grupo
    step = 1.0 / 3
    onset1 = group_start + step
    onset2 = group_start + 2 * step
    return [
        Note(pitch, onset1, onset1 + 0.05, 0.8),
        Note(pitch, onset2, onset2 + 0.05, 0.8),
    ]


def compass_with_constant_triplets() -> Piece:
    #Compasso unico 4/4 com tercinas constantes e consistentes nos 4 tempos -
    #B2 deve classificar como candidato a metrica composta
    piece = Piece(instrument=Instrument.piano())
    compass = Compass(
        index=1, begin_time=0.0, end_time=4.0,
        formula=TimeSignature(4, 4), armor=KeySignature(0, "C", TonalMode.MAJOR),
    )
    piece.add_compass(compass)
    voice = Voice()
    for group_index in range(4):
        for note in _ternary_notes_for_group(group_index * 1.0):
            voice.add_note(note)
    piece.add_voice(voice)
    return piece


def compass_with_isolated_triplet() -> Piece:
    #3 compassos 4/4: binario, ternario isolado, binario novamente -
    #a mudanca isolada nao deve se sustentar
    piece = Piece(instrument=Instrument.piano())
    compass1 = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    compass2 = Compass(2, 4.0, 8.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    compass3 = Compass(3, 8.0, 12.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass1)
    piece.add_compass(compass2)
    piece.add_compass(compass3)
    voice = Voice()
    for group_index in range(4):
        for note in _binary_notes_for_group(group_index * 1.0):
            voice.add_note(note)
    for group_index in range(4):
        for note in _ternary_notes_for_group(4.0 + group_index * 1.0):
            voice.add_note(note)
    for group_index in range(4):
        for note in _binary_notes_for_group(8.0 + group_index * 1.0):
            voice.add_note(note)
    piece.add_voice(voice)
    return piece


def sequence_with_sustained_ternary_change() -> Piece:
    #3 compassos 4/4: binario, seguido de dois compassos ternarios
    #sustentados - a mudanca deve ser adotada a partir do segundo compasso
    piece = Piece(instrument=Instrument.piano())
    compass1 = Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    compass2 = Compass(2, 4.0, 8.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    compass3 = Compass(3, 8.0, 12.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR))
    piece.add_compass(compass1)
    piece.add_compass(compass2)
    piece.add_compass(compass3)
    voice = Voice()
    for group_index in range(4):
        for note in _binary_notes_for_group(group_index * 1.0):
            voice.add_note(note)
    for group_index in range(4):
        for note in _ternary_notes_for_group(4.0 + group_index * 1.0):
            voice.add_note(note)
    for group_index in range(4):
        for note in _ternary_notes_for_group(8.0 + group_index * 1.0):
            voice.add_note(note)
    piece.add_voice(voice)
    return piece


def voice_with_repeated_arpeggio_and_one_gap() -> Piece:
    #5 compassos 4/4 identicos (arpejo nas 4 pulsacoes), com uma nota
    #ausente exatamente na 3a pulsacao do compasso central (indice 3) -
    #A8a/A9 deve preencher com alta confianca (4 vizinhos confirmando)
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    pitches = [60, 62, 64, 65]
    for measure_index in range(5):
        start = measure_index * 4.0
        compass = Compass(
            index=measure_index + 1,
            begin_time=start,
            end_time=start + 4.0,
            formula=TimeSignature(4, 4),
            armor=KeySignature(0, "C", TonalMode.MAJOR),
        )
        piece.add_compass(compass)
        for beat_index, pitch in enumerate(pitches):
            if measure_index == 2 and beat_index == 2:
                continue   # o furo: compasso 3, 3a pulsacao
            onset = start + beat_index * 1.0
            voice.add_note(Note(pitch, onset, onset + 0.9, 0.8))
    piece.add_voice(voice)
    return piece


def voice_with_pattern_confirmed_once() -> Piece:
    #2 compassos 4/4: o alvo (indice 1) com um furo, e um unico vizinho
    #(indice 2) com o padrao completo - apenas 1 confirmacao, abaixo do
    #limiar de confianca alta
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()
    pitches = [60, 62, 64, 65]
    for measure_index in range(2):
        start = measure_index * 4.0
        compass = Compass(
            index=measure_index + 1,
            begin_time=start,
            end_time=start + 4.0,
            formula=TimeSignature(4, 4),
            armor=KeySignature(0, "C", TonalMode.MAJOR),
        )
        piece.add_compass(compass)
        for beat_index, pitch in enumerate(pitches):
            if measure_index == 0 and beat_index == 2:
                continue   # o compasso-alvo (indice 1) tem o furo
            onset = start + beat_index * 1.0
            voice.add_note(Note(pitch, onset, onset + 0.9, 0.8))
    piece.add_voice(voice)
    return piece


def voice_without_repetitive_pattern() -> Piece:
    #3 compassos 4/4 com padroes de grade mutuamente incompativeis -
    #nenhum par forma "mesmo padrao com exatamente um furo"
    piece = Piece(instrument=Instrument.piano())
    voice = Voice()

    patterns = [
        [0, 1, 2, 3],   # compasso 1: as 4 pulsacoes (padrao completo)
        [0, 2],         # compasso 2: so pulsacoes 1 e 3
        [1, 3],         # compasso 3: so pulsacoes 2 e 4
    ]
    for measure_index, beat_positions in enumerate(patterns):
        start = measure_index * 4.0
        compass = Compass(
            index=measure_index + 1,
            begin_time=start,
            end_time=start + 4.0,
            formula=TimeSignature(4, 4),
            armor=KeySignature(0, "C", TonalMode.MAJOR),
        )
        piece.add_compass(compass)
        for beat_index in beat_positions:
            onset = start + beat_index * 1.0
            voice.add_note(Note(60, onset, onset + 0.9, 0.8))
    piece.add_voice(voice)
    return piece


def voice_with_spurious_rearticulations() -> Voice:
    #4 deteccoes consecutivas da mesma altura, sem gaps reais e sem picos
    #de intensidade - C1 deve unir tudo em uma unica Nota
    voice = Voice()
    voice.add_note(Note(60, 0.00, 0.30, 0.70))
    voice.add_note(Note(60, 0.31, 0.60, 0.72))
    voice.add_note(Note(60, 0.61, 0.90, 0.68))
    voice.add_note(Note(60, 0.91, 1.20, 0.71))
    return voice


def voice_with_real_repeated_attack() -> Voice:
    #Nota curta e fraca seguida de outra, mesma altura, bem mais intensa -
    #novo ataque real, C1 nao deve unir
    voice = Voice()
    voice.add_note(Note(60, 0.00, 0.30, 0.30))
    voice.add_note(Note(60, 0.31, 0.60, 0.90))
    return voice


def notes_diatonic_in_d_major() -> list[Note]:
    #Escala de Re maior (I-VII) - usada para validar que Do# e Fa# sao
    #grafados como diatonicos (nao acidentes) sob a armadura de Re maior
    return [
        Note(62, 0.0, 0.5, 0.8),   # D
        Note(64, 0.5, 1.0, 0.8),   # E
        Note(66, 1.0, 1.5, 0.8),   # F#
        Note(67, 1.5, 2.0, 0.8),   # G
        Note(69, 2.0, 2.5, 0.8),   # A
        Note(71, 2.5, 3.0, 0.8),   # B
        Note(73, 3.0, 3.5, 0.8),   # C#
        Note(74, 3.5, 4.0, 0.8),   # D
    ]


def notes_chromatic_ascending_and_descending() -> list[Note]:
    #Passagem ascendente C-C#-D e, mais tarde, passagem descendente D-Db-C,
    #ambas sobre uma armadura sem acidentes (Do maior) - usada para validar
    #C4: sustenido ao subir, bemol ao descer
    return [
        Note(60, 0.0, 0.5, 0.8),   # C
        Note(61, 0.5, 1.0, 0.8),   # C# - ascendente
        Note(62, 1.0, 1.5, 0.8),   # D
        Note(62, 2.0, 2.5, 0.8),   # D
        Note(61, 2.5, 3.0, 0.8),   # Db - descendente
        Note(60, 3.0, 3.5, 0.8),   # C
    ]