from __future__ import annotations
import torch
from beat_this.inference import File2Beats
from models.raw_signals import (Beat, RawSignals)

MODEL_CHECKPOINT: str = "checkpoints/final0.ckpt"
INSTANT_TOLERANCE_SECONDS: float = 0.01
REGULARITY_WINDOW_SIZE: int = 4
RELATIVE_REGULARITY_TOLERANCE: float = 0.15
LOW_CONFIDENCE: float = 0.3


class BeatDetector:

    def detect(self, audio_path: str) -> RawSignals:
        detector = File2Beats(
            checkpoint_path=MODEL_CHECKPOINT,
            device=self._available_device(),
            dbn=False,
        )
        raw_beats, raw_downbeats = detector(audio_path)
        beats = [float(b) for b in raw_beats]
        downbeats = [float(d) for d in raw_downbeats]
        return RawSignals(beats=self._build_beats(beats, downbeats))

    def _available_device(self) -> str:
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _is_downbeat(self, instant: float, downbeats: list[float]) -> bool:
        return any(abs(instant - downbeat) < INSTANT_TOLERANCE_SECONDS for downbeat in downbeats)

    def _estimate_confidence_by_regularity(self, index: int, beats: list[float]) -> float:
        #Nas duas bordas da sequencia (indice 0 ou ultimo), sem vizinho de
        #um dos lados - retorna 1.0 por padrao, sem penalizar
        if index == 0 or index == len(beats) - 1:
            return 1.0

        local_interval = beats[index] - beats[index - 1]

        start = max(0, index - REGULARITY_WINDOW_SIZE)
        end = min(len(beats), index + REGULARITY_WINDOW_SIZE + 1)
        window = beats[start:end]
        window_intervals = [window[i] - window[i - 1] for i in range(1, len(window))]

        sorted_intervals = sorted(window_intervals)
        count = len(sorted_intervals)
        if count % 2 == 1:
            median_interval = sorted_intervals[count // 2]
        else:
            median_interval = (sorted_intervals[count // 2 - 1] + sorted_intervals[count // 2]) / 2.0

        if median_interval == 0:
            return 1.0

        relative_deviation = abs(local_interval - median_interval) / median_interval
        return 1.0 if relative_deviation <= RELATIVE_REGULARITY_TOLERANCE else LOW_CONFIDENCE

    def _build_beats(self, beats: list[float], downbeats: list[float]) -> list[Beat]:
        return [
            Beat(
                instant=instant,
                is_strong_beat=self._is_downbeat(instant, downbeats),
                confidence=self._estimate_confidence_by_regularity(index, beats),
            )
            for index, instant in enumerate(beats)
        ]