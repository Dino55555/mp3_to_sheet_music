from __future__ import annotations
import sys
from music21 import converter, stream

TOLERANCE_OFFSET_QL: float = 0.1


def extract_note_events(path: str, part_index: int = 0) -> list[dict]:
    score = converter.parse(path)
    parts = list(score.getElementsByClass(stream.Part))
    if part_index >= len(parts):
        raise ValueError(f"Arquivo {path} tem só {len(parts)} parte(s), pediu índice {part_index}")
    part = parts[part_index]

    events = []
    for n in part.recurse().notes:
        if not n.isNote:
            continue  # ignora acordes/pausas por enquanto - so notas simples
        offset = n.getOffsetInHierarchy(part)
        events.append({
            'offset': float(offset),
            'pitch_midi': n.pitch.midi,
            'pitch_name': n.pitch.nameWithOctave,
            'quarterLength': float(n.quarterLength),
        })
    events.sort(key=lambda e: e['offset'])
    return events


def compare_note_events(expected: list[dict], actual: list[dict], tolerance_offset: float = TOLERANCE_OFFSET_QL) -> dict:
    matched_actual_indices = set()
    missing = []
    mismatched = []

    for exp in expected:
        best_match_index = None
        best_distance = None
        for i, act in enumerate(actual):
            if i in matched_actual_indices:
                continue
            distance = abs(act['offset'] - exp['offset'])
            if distance > tolerance_offset:
                continue
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_match_index = i

        if best_match_index is None:
            missing.append(exp)
        else:
            matched_actual_indices.add(best_match_index)
            act = actual[best_match_index]
            if act['pitch_midi'] != exp['pitch_midi'] or abs(act['quarterLength'] - exp['quarterLength']) > 0.01:
                mismatched.append((exp, act))

    extra = [act for i, act in enumerate(actual) if i not in matched_actual_indices]

    return {'missing': missing, 'extra': extra, 'mismatched': mismatched}


def print_report(result: dict, label: str) -> None:
    print(f"\n=== {label} ===")
    print(f"Notas faltando (esperadas, ausentes na saída): {len(result['missing'])}")
    for m in result['missing']:
        print(f"   offset={m['offset']:.2f}, pitch={m['pitch_name']}, ql={m['quarterLength']}")

    print(f"Notas extras (na saída, não esperadas): {len(result['extra'])}")
    for e in result['extra']:
        print(f"   offset={e['offset']:.2f}, pitch={e['pitch_name']}, ql={e['quarterLength']}")

    print(f"Notas com altura ou duração diferente: {len(result['mismatched'])}")
    for exp, act in result['mismatched']:
        print(f"   offset={exp['offset']:.2f}: esperado pitch={exp['pitch_name']} ql={exp['quarterLength']} "
              f"| obtido pitch={act['pitch_name']} ql={act['quarterLength']}")

    total_expected = len(result['missing']) + len(result['mismatched']) + (0)  # aproximacao
    print(f"\nResumo: {len(result['missing'])} faltando, {len(result['extra'])} extras, "
          f"{len(result['mismatched'])} com valor diferente")


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python compare_musicxml.py gabarito.musicxml saida.musicxml [indice_da_parte]", file=sys.stderr)
        sys.exit(1)

    expected_path = sys.argv[1]
    actual_path = sys.argv[2]
    part_index = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    expected = extract_note_events(expected_path, part_index)
    actual = extract_note_events(actual_path, part_index)

    print(f"Gabarito: {len(expected)} notas na parte {part_index}")
    print(f"Saída: {len(actual)} notas na parte {part_index}")

    result = compare_note_events(expected, actual)
    print_report(result, f"Comparação (parte {part_index})")


if __name__ == "__main__":
    main()