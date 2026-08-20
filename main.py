from __future__ import annotations
import sys
import argparse
from complete_pipeline import (process_file, InvalidInputError)
from models.signaling import SeverityLevel

_SEVERITY_LABELS: dict[SeverityLevel, str] = {
    SeverityLevel.REQUIRES_DECISION: "requer decisão",
    SeverityLevel.VERIFY: "verificar",
    SeverityLevel.INFORMATIONAL: "informativo",
}


def _format_signaling_summary(count_by_severity: dict[SeverityLevel, int]) -> str:
    total = sum(count_by_severity.values())
    if total == 0:
        return "Nenhum ponto sinalizado."

    parts = []
    for level in (SeverityLevel.REQUIRES_DECISION, SeverityLevel.VERIFY, SeverityLevel.INFORMATIONAL):
        count = count_by_severity.get(level, 0)
        if count > 0:
            parts.append(f"{count} {_SEVERITY_LABELS[level]}")

    return f"{total} pontos sinalizados: " + ", ".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte um arquivo MP3 em partitura MusicXML")
    parser.add_argument("caminho_mp3", help="Caminho do arquivo MP3 de entrada")
    parser.add_argument("--saida", "-o", default=".", help="Diretório de saída (padrão: diretório atual)")
    args = parser.parse_args()

    try:
        result = process_file(args.caminho_mp3, args.saida)
    except InvalidInputError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

    print(f"MusicXML: {result.musicxml_path}")
    print(f"MXL: {result.mxl_path}")
    print(f"Relatório: {result.report_path}")
    print(_format_signaling_summary(result.count_by_severity))


if __name__ == "__main__":
    main()