from __future__ import annotations
import os
import wave
import numpy as np
from demucs.api import Separator

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
        #Converte o tensor float32 [-1,1] (canais, amostras) para PCM 16-bit
        #e grava via wave (stdlib) - evita depender de torchaudio.save, que
        #em versoes recentes exige torchcodec + FFmpeg instalado no sistema,
        #uma cadeia de dependencia bem mais pesada do que o esperado
        audio_np = audio.detach().cpu().numpy()
        num_channels, _ = audio_np.shape

        clipped = np.clip(audio_np, -1.0, 1.0)
        pcm16 = (clipped * 32767.0).astype(np.int16)

        #wave espera amostras intercaladas por canal: [L0,R0,L1,R1,...]
        interleaved = pcm16.T.flatten()

        with wave.open(path, 'w') as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(OUTPUT_SAMPLE_RATE)
            wav_file.writeframes(interleaved.tobytes())