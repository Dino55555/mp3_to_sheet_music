import pytest
from vibrato.vibrato_detector import VibratoDetector
from models.note import Note
from models.voice import Voice
from models.compass import (Compass, TimeSignature, KeySignature, TonalMode)
from Compass.piece import Piece
from Compass.instrument import Instrument
from config import Config
from signaling.signaler import (Signaler, SignalingCategory, SeverityLevel)


def test_detectar_fragmentacao_oscilante_identifica_padrao_de_vibrato():
    detector = VibratoDetector()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice()
    voice.add_note(Note(74, 0.00, 0.10, 0.5))
    voice.add_note(Note(75, 0.12, 0.22, 0.5))
    voice.add_note(Note(74, 0.24, 0.34, 0.5))
    voice.add_note(Note(75, 0.36, 0.46, 0.5))
    piece.add_voice(voice)

    detector._detect_oscillating_fragmentation(voice, piece, signaler)

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].category == SignalingCategory.POSSIBLE_VIBRATO_FRAGMENTATION
    assert signals[0].level == SeverityLevel.VERIFY
    assert signals[0].note is voice.notes[0]

def test_detectar_fragmentacao_oscilante_ignora_sequencia_curta_demais():
    detector = VibratoDetector()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice()
    #so 2 notas curtas oscilando - abaixo do minimo de 3
    voice.add_note(Note(74, 0.00, 0.10, 0.5))
    voice.add_note(Note(75, 0.12, 0.22, 0.5))
    piece.add_voice(voice)

    detector._detect_oscillating_fragmentation(voice, piece, signaler)

    assert signaler.all() == []

def test_detectar_fragmentacao_oscilante_ignora_movimento_monotonico():
    detector = VibratoDetector()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice()
    #legato real ascendente, sem inversao de direcao - nao e oscilacao
    voice.add_note(Note(74, 0.00, 0.10, 0.5))
    voice.add_note(Note(75, 0.12, 0.22, 0.5))
    voice.add_note(Note(76, 0.24, 0.34, 0.5))
    voice.add_note(Note(77, 0.36, 0.46, 0.5))
    piece.add_voice(voice)

    detector._detect_oscillating_fragmentation(voice, piece, signaler)

    assert signaler.all() == []

def test_detectar_fragmentacao_oscilante_ignora_amplitude_grande_demais():
    detector = VibratoDetector()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice()
    #oscila (vai e volta), mas amplitude de 5 semitons - acima do limite de 4
    voice.add_note(Note(74, 0.00, 0.10, 0.5))
    voice.add_note(Note(79, 0.12, 0.22, 0.5))
    voice.add_note(Note(74, 0.24, 0.34, 0.5))
    piece.add_voice(voice)

    detector._detect_oscillating_fragmentation(voice, piece, signaler)

    assert signaler.all() == []

def test_detectar_fragmentacao_oscilante_nao_altera_nenhuma_nota():
    detector = VibratoDetector()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice()
    voice.add_note(Note(74, 0.00, 0.10, 0.5))
    voice.add_note(Note(75, 0.12, 0.22, 0.5))
    voice.add_note(Note(74, 0.24, 0.34, 0.5))
    voice.add_note(Note(75, 0.36, 0.46, 0.5))
    piece.add_voice(voice)

    notes_before = [(n.pitch, n.onset, n.offset) for n in voice.notes]

    detector._detect_oscillating_fragmentation(voice, piece, signaler)

    notes_after = [(n.pitch, n.onset, n.offset) for n in voice.notes]
    assert notes_before == notes_after

def test_process_gera_sinalizacao_com_compasso_correto():
    detector = VibratoDetector()
    signaler = Signaler()
    piece = Piece(instrument=Instrument.piano())
    piece.add_compass(Compass(1, 0.0, 4.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    piece.add_compass(Compass(2, 4.0, 8.0, TimeSignature(4, 4), KeySignature(0, "C", TonalMode.MAJOR)))
    voice = Voice()
    #padrao de vibrato dentro do segundo compasso
    voice.add_note(Note(74, 4.00, 4.10, 0.5))
    voice.add_note(Note(75, 4.12, 4.22, 0.5))
    voice.add_note(Note(74, 4.24, 4.34, 0.5))
    piece.add_voice(voice)

    detector.process(piece, Config(), signaler)

    signals = signaler.all()
    assert len(signals) == 1
    assert signals[0].compass_number == 2