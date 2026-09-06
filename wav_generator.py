import sys, shutil, tempfile
sys.path.insert(0, ".")
from signal_extractor.separation import SourceSeparator

audio_path = "mp3/mp3_3.mp3"
output_path = "vocals_cache/mp3_3_vocals.wav"

with tempfile.TemporaryDirectory() as temp_dir:
    vocal_path, _ = SourceSeparator().separate(audio_path, temp_dir)
    shutil.copy(vocal_path, output_path)

print(f"salvo em {output_path}")