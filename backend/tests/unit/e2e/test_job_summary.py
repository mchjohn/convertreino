import json

from tests.e2e.job_summary import build_markdown


def test_build_markdown_renders_accuracy_table(tmp_path):
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "providers": {
                    "openai": [
                        {"case_id": "intent_greeting", "passed": True, "detail": None},
                        {
                            "case_id": "intent_run_volume_this_week",
                            "passed": False,
                            "detail": "expected ['get_run_volume'], got ['get_longest_run']",
                        },
                    ],
                },
            },
        ),
        encoding="utf-8",
    )

    markdown = build_markdown(results_path)

    assert "## Chat intent accuracy (openai)" in markdown
    assert "**1/2** (50.0%)" in markdown
    assert "| Caso | Pergunta | Esperado | Resultado |" in markdown
    assert "| intent_greeting | Olá! | — (sem tool) | ✅ |" in markdown
    assert "intent_run_volume_this_week" in markdown
    assert "Quanto corri essa semana?" in markdown
    assert "get_run_volume" in markdown
    assert "❌ expected ['get_run_volume'], got ['get_longest_run']" in markdown
