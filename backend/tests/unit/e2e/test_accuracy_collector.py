from tests.e2e.accuracy import ACCURACY_THRESHOLD, AccuracyCollector, CaseOutcome


def test_accuracy_collector_report_formats_failures():
    collector = AccuracyCollector()
    detail = "expected ['get_run_volume'], got ['get_longest_run']"
    collector.record(
        "openai",
        CaseOutcome("intent_run_volume_this_week", False, detail),
    )
    collector.record("openai", CaseOutcome("intent_greeting", True))

    lines = collector.report()
    assert lines[0] == "Chat intent accuracy [openai]: 1/2 (50.0%)"
    assert "Failures:" in lines
    assert "intent_run_volume_this_week" in lines[2]


def test_below_threshold_at_ninety_percent_passes():
    collector = AccuracyCollector()
    for index in range(9):
        collector.record("groq", CaseOutcome(f"case_{index}", True))
    collector.record("groq", CaseOutcome("case_9", False, "wrong tool"))

    assert collector.below_threshold_providers() == []


def test_below_threshold_at_eighty_nine_percent_fails():
    collector = AccuracyCollector()
    for index in range(8):
        collector.record("openai", CaseOutcome(f"case_{index}", True))
    for index in range(2):
        collector.record("openai", CaseOutcome(f"fail_{index}", False, "wrong tool"))

    assert collector.below_threshold_providers() == ["openai"]
    assert ACCURACY_THRESHOLD == 0.90
