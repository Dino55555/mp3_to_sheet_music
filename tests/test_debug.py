import sys, tempfile
sys.path.insert(0, ".")
from complete_pipeline import default_stages
from signal_extractor.extraction_pipeline import extract_notes_from_mix
from signal_extractor.rhythmic_detection import BeatDetector
from signal_extractor.note_extraction import build_initial_piece
from config import Config
from signaling.signaler import Signaler
from orchestrator import Orchestrator
from notation.musicxml_exporter import MusicXMLExporter
from music21 import duration as m21_duration

audio_path = "mp3/mp3_3.mp3"
config = Config()

with tempfile.TemporaryDirectory() as temp_dir:
    notes = extract_notes_from_mix(audio_path, temp_dir)
raw_signals = BeatDetector().detect(audio_path)

piece = build_initial_piece(notes, config.instrument)
piece.raw_signals = raw_signals

signaler = Signaler()
orchestrator = Orchestrator(config, signaler)
for stage in default_stages():
    orchestrator.add_stage(stage)
piece = orchestrator.process(piece)

exporter = MusicXMLExporter()

def check_quarterlength(label, ql):
    try:
        d = m21_duration.Duration()
        d.quarterLength = ql
        t = d.type
        if t in ('inexpressible', 'zero', 'complex'):
            print(f"PROBLEMA [{label}]: quarterLength={ql!r} -> type={t}")
    except Exception as e:
        print(f"ERRO [{label}]: quarterLength={ql!r} -> {type(e).__name__}: {e}")

print("--- checando duracao de cada nota (quarterLength) ---")
for voice in piece.voices:
    for note in voice.notes:
        compass = piece.compass_at_instant(note.onset)
        factor = exporter._quarterlength_factor_per_second(compass)
        ql = note.duration() * factor
        check_quarterlength(f"nota pitch={note.pitch} onset={note.onset!r}", ql)

print("--- checando vaos (viram pausa) dentro de cada voz ---")
for voice in piece.voices:
    for i in range(len(voice.notes) - 1):
        n1 = voice.notes[i]
        n2 = voice.notes[i + 1]
        gap_seconds = n2.onset - n1.offset
        if gap_seconds <= 0:
            continue
        compass = piece.compass_at_instant(n1.offset)
        factor = exporter._quarterlength_factor_per_second(compass)
        ql = gap_seconds * factor
        check_quarterlength(f"vao entre pitch={n1.pitch}(offset={n1.offset!r}) e pitch={n2.pitch}(onset={n2.onset!r})", ql)

print("--- checando vao do inicio do compasso ate a primeira nota ---")
for voice in piece.voices:
    for compass in piece.compasses:
        notes_here = voice.notes_on_interval(compass.begin_time, compass.end_time)
        if not notes_here:
            continue
        first = notes_here[0]
        gap_seconds = first.onset - compass.begin_time
        if gap_seconds <= 0:
            continue
        factor = exporter._quarterlength_factor_per_second(compass)
        ql = gap_seconds * factor
        check_quarterlength(f"vao inicio do compasso {compass.index} ate pitch={first.pitch}", ql)

print("--- fim ---")