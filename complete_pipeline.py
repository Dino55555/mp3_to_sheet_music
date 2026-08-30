from __future__ import annotations
import os
import tempfile
from dataclasses import dataclass
from typing import Optional
from collections import Counter

from config import Config
from signaling.signaler import Signaler
from models.signaling import (Signaling, SeverityLevel)
from orchestrator import (Orchestrator, PipelineStage)
from cleaning.cleaner import Cleaner
from structure.structural_detector import StructuralDetector
from voices.voice_separator import VoiceSeparator
from voices.octave_corrector import OctaveCorrector
from rhythm.quantizer import Quantizer
from completeness.completeness_detector import CompletenessDetector
from playability.playability_checker import PlayabilityChecker
from notation.notator import Notator
from notation.musicxml_exporter import MusicXMLExporter
from signal_extractor.extraction_pipeline import extract_notes_from_mix
from signal_extractor.rhythmic_detection import BeatDetector
from signal_extractor.note_extraction import build_initial_piece
from mxl_packaging import package_mxl


class InvalidInputError(Exception):
    pass


@dataclass
class ProcessingResult:
    musicxml_path: str
    mxl_path: str
    report_path: str
    total_notes: int
    count_by_severity: dict[SeverityLevel, int]


def default_stages() -> list[PipelineStage]:
    #Unico lugar do projeto que declara a ordem definitiva das 8 etapas
    return [
        Cleaner(),
        StructuralDetector(),
        VoiceSeparator(),
        OctaveCorrector(),
        Quantizer(),
        CompletenessDetector(),
        PlayabilityChecker(),
        Notator(),
    ]


def _count_by_severity(signalings: list[Signaling]) -> dict[SeverityLevel, int]:
    return dict(Counter(signaling.level for signaling in signalings))


def _output_names(mp3_path: str, output_directory: str) -> tuple[str, str, str]:
    base_name = os.path.splitext(os.path.basename(mp3_path))[0]
    musicxml_path = os.path.join(output_directory, f"{base_name}.musicxml")
    mxl_path = os.path.join(output_directory, f"{base_name}.mxl")
    report_path = os.path.join(output_directory, f"{base_name}_relatorio.txt")
    return musicxml_path, mxl_path, report_path


def process_file(mp3_path: str, output_directory: str, config: Optional[Config] = None) -> ProcessingResult:
    #Checagem barata de existencia, antes de qualquer modelo ser carregado -
    #arquivo inexistente e um tipo de falha de entrada diferente de
    #"arquivo existe mas e ilegivel", que so se revela tentando processar
    if not os.path.isfile(mp3_path):
        raise InvalidInputError(f"Arquivo não encontrado: {mp3_path}")

    if config is None:
        config = Config()

    #Demucs/Basic Pitch (extracao de notas) e Beat This! (deteccao de
    #batidas) usam tres caminhos de decodificacao de audio diferentes -
    #um arquivo pode passar por um e falhar no outro, entao as duas
    #chamadas contam como uma unica fase conceitual de extracao, com o
    #mesmo tratamento de falha de entrada
    try:
        with tempfile.TemporaryDirectory() as temp_directory:
            notes = extract_notes_from_mix(mp3_path, temp_directory)
        raw_signals = BeatDetector().detect(mp3_path)
    except Exception as error:
        raise InvalidInputError(
            f"Não foi possível processar o arquivo de áudio: {mp3_path}"
        ) from error

    piece = build_initial_piece(notes, config.instrument)
    piece.raw_signals = raw_signals

    signaler = Signaler()
    orchestrator = Orchestrator(config, signaler)
    for stage in default_stages():
        orchestrator.add_stage(stage)
    piece = orchestrator.process(piece)

    os.makedirs(output_directory, exist_ok=True)
    musicxml_path, mxl_path, report_path = _output_names(mp3_path, output_directory)

    #Fora do Orquestrador: exportar e saida, nao transformacao - nao
    #devolve uma Peca, nao implementa o mesmo protocolo
    MusicXMLExporter().export(piece, musicxml_path, signaler, report_path, config)
    package_mxl(musicxml_path, mxl_path)

    return ProcessingResult(
        musicxml_path=musicxml_path,
        mxl_path=mxl_path,
        report_path=report_path,
        total_notes=len(piece.all_notes()),
        count_by_severity=_count_by_severity(signaler.all()),
    )