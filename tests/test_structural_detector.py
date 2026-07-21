import pytest
from tests.fixtures import create_example_piece
from models.raw_signals import RawSignals
from structure.structural_detector import StructuralDetector

def test_process_raises_without_raw_signals():
    piece = create_example_piece()
    piece.raw_signals = None

    with pytest.raises(ValueError):
        detector.process()