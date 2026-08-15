from __future__ import annotations
import os
from demucs.api import Separator
import torchaudio

MODEL_NAME: str = "htdemucs"
OUTPUT_SAMPLE_RATE: int = 44100


class SourceSeparator:

    def separate(self, original_audio_path: str, output_directory: str) -> tuple[str, str]:
        separator = Separator(model=MODEL_NAME)
        _, stems = separator.separate_audio_file(original_audio_path)

        vocals = stems["vocals"]
        instrumental = self._combine_instrumental_stems(stems)

        os.makedirs(output_directory, exist_ok=True)
        vocal_path = os.path.join(output_directory, "vocals.wav")
        instrumental_path = os.path.join(output_directory, "instrumental.wav")

        self._save_wav(vocals, vocal_path)
        self._save_wav(instrumental, instrumental_path)

        return vocal_path, instrumental_path

    def _combine_instrumental_stems(self, stems):
        #Soma elemento a elemento drums + bass + other; ignora vocals por completo
        return stems["drums"] + stems["bass"] + stems["other"]

    def _save_wav(self, audio, path: str) -> None:
        torchaudio.save(path, audio, OUTPUT_SAMPLE_RATE)