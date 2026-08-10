from __future__ import annotations
import os
from models.signaling import (Signaling, SeverityLevel)
from signaling.signaler import Signaler

_LEVEL_TITLES: dict[SeverityLevel, str] = {
    SeverityLevel.REQUIRES_DECISION: "REQUER DECISÃO",
    SeverityLevel.VERIFY: "VERIFICAR",
    SeverityLevel.INFORMATIONAL: "INFORMATIVO",
}

_LEVEL_ORDER: tuple[SeverityLevel, ...] = (
    SeverityLevel.REQUIRES_DECISION,
    SeverityLevel.VERIFY,
    SeverityLevel.INFORMATIONAL,
)


class ReportGenerator:

    def generate(self, signaler: Signaler, path: str) -> None:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        text = self._build_text(signaler.ordered_report())
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)

    def _build_text(self, signalings: list[Signaling]) -> str:
        header = "Relatório de Sinalizações\n" + "=" * 25 + "\n\n"
        if not signalings:
            return header + "Nenhum ponto sinalizado nesta conversão."

        sections: list[str] = []
        for level in _LEVEL_ORDER:
            level_signalings = [s for s in signalings if s.level == level]
            if not level_signalings:
                continue
            section_lines = [f"{self._level_title(level)} ({len(level_signalings)})"]
            section_lines.extend(self._format_line(s) for s in level_signalings)
            sections.append("\n".join(section_lines))

        return header + "\n\n".join(sections)

    def _level_title(self, level: SeverityLevel) -> str:
        return _LEVEL_TITLES[level]

    def _format_line(self, signaling: Signaling) -> str:
        return f"Compasso {signaling.compass_number}: {signaling.description}"