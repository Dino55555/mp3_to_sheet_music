from config import Config
from orchestrator import Orchestrator
from signaling.signaler import Signaler
from tests.fixtures import create_example_piece


def main():
    piece = create_example_piece()
    config = Config()
    signaler = Signaler()
    orchestrator = Orchestrator(config=config, signaler=signaler)
    print("Antes de processar:")
    print(piece.summary())
    processed_piece = orchestrator.process(piece)
    print()
    print("Depois de processar:")
    print(processed_piece.summary())

if __name__ == "__main__":
    main()