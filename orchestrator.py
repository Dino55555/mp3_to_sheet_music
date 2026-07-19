from __future__ import annotations
from typing import Optional, Protocol
from config import Config
from Compass.piece import Piece
from signaling.signaler import Signaler


class PipelineStage(Protocol):
    def process(self, piece: Piece, config: Config, signaler: Signaler) -> Piece:
        ...


class Orchestrator:
    def __init__(self, config: Config, signaler: Signaler, stages: Optional[list[PipelineStage]] = None) -> None:
        self.config = config
        self.signaler = signaler
        self._stages = stages[:] if stages is not None else[]

    def add_stage(self, stage: PipelineStage) -> None:
        self._stages.append(stage)

    def process(self, piece: Piece) -> Piece:
        current_piece = piece
        for stage in self._stages:
            current_piece = stage.process(current_piece, self.config, self.signaler)

        return current_piece            