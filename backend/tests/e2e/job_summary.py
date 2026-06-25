"""Gera GitHub Job Summary em markdown a partir dos resultados E2E de accuracy."""

import json
import os
import sys
from pathlib import Path

from tests.e2e.intent_matrix import IntentCase, load_intent_matrix

DEFAULT_RESULTS_PATH = "e2e-accuracy-results.json"


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _format_expected(case: IntentCase | None) -> str:
    if case is None:
        return "—"
    if not case.expected_tools:
        return "— (sem tool)"
    return ", ".join(case.expected_tools)


def _format_result(outcome: dict[str, object]) -> str:
    if outcome["passed"]:
        return "✅"
    detail = outcome.get("detail")
    if detail:
        return f"❌ {detail}"
    return "❌"


def build_markdown(results_path: Path) -> str:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    cases_by_id = {case.id: case for case in load_intent_matrix()}

    lines: list[str] = []
    for provider in sorted(data["providers"]):
        outcomes: list[dict[str, object]] = data["providers"][provider]
        passed = sum(1 for item in outcomes if item["passed"])
        total = len(outcomes)
        pct = (passed / total * 100) if total else 0.0

        lines.append(f"## Chat intent accuracy ({provider})")
        lines.append("")
        lines.append(f"**{passed}/{total}** ({pct:.1f}%)")
        lines.append("")
        lines.append("| Caso | Pergunta | Esperado | Resultado |")
        lines.append("| --- | --- | --- | --- |")

        for outcome in outcomes:
            case_id = str(outcome["case_id"])
            case = cases_by_id.get(case_id)
            question = case.question if case else "—"
            lines.append(
                f"| {_escape_md(case_id)} | {_escape_md(question)} | "
                f"{_escape_md(_format_expected(case))} | "
                f"{_escape_md(_format_result(outcome))} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_job_summary(results_path: Path) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    markdown = build_markdown(results_path)

    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(markdown)
            handle.write("\n")
        return

    print(markdown)


def main() -> None:
    raw_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("E2E_RESULTS_JSON", DEFAULT_RESULTS_PATH)
    results_path = Path(raw_path)

    if not results_path.is_file():
        print(f"No results file at {results_path}, skipping job summary")
        return

    write_job_summary(results_path)


if __name__ == "__main__":
    main()
