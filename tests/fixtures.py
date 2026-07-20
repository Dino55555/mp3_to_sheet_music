from Compass.instrument import Instrument
from models.voice import Voice
from models.note import Note
from models.compass import(Compass, TimeSignature, KeySignature, TonalMode)
from Compass.piece import Piece


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