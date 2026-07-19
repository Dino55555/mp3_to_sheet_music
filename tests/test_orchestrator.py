from config import Config
from orchestrator import Orchestrator
from signaling.signaler import Signaler
from tests.fixtures import create_example_piece


class FakeStage:
    
    def __init__(self):
        self.called = False

    def process(self, piece, config, signaler):
        self.called = True
        return piece


class OrderedStage:
    
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def process(self, piece, config, signaler):
        self.calls.append(self.name)
        return piece
    

def test_orchestrator_without_stages_returns_same_piece():
    piece = create_example_piece()
    orchestrator = Orchestrator(
        Config(),
        Signaler()
    )
    result = orchestrator.process(piece)

    assert result is piece

def test_single_stage_is_calles():
    piece = create_example_piece()
    stage = FakeStage()
    orchestrator = Orchestrator(
        Config(),
        Signaler()
    )
    orchestrator.add_stage(stage)
    orchestrator.process(piece)

    assert stage.called

def test_stages_executes_in_order():
    calls = []
    stage1 = OrderedStage("A", calls)
    stage2 = OrderedStage("B", calls)
    orchestrator = Orchestrator(Config(), Signaler())
    orchestrator.add_stage(stage1)
    orchestrator.add_stage(stage2)
    orchestrator.process(create_example_piece())

    assert calls == ["A", "B"]

def test_add_stage_after_construction():
    orchestrator = Orchestrator(Config(), Signaler())
    stage = FakeStage()
    orchestrator.add_stage(stage)
    orchestrator.process(create_example_piece())

    assert stage.called