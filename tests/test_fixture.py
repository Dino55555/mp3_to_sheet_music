from tests.fixtures import create_example_piece

piece = create_example_piece()

def test_fixture_piece_is_valid():
    piece = create_example_piece()

    assert len(piece.compasses) == 1
    assert len(piece.voices) == 1
    assert len(piece.all_notes()) == 3