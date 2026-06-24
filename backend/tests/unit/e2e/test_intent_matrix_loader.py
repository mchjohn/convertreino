from tests.e2e.intent_matrix import load_intent_matrix


def test_load_intent_matrix_has_ten_cases():
    cases = load_intent_matrix()
    assert len(cases) == 10
    assert {case.id for case in cases} == {
        "intent_longest_run",
        "intent_longest_run_vs_volume",
        "intent_run_volume_this_week",
        "intent_run_volume_year",
        "intent_longest_ride",
        "intent_ride_volume_year",
        "intent_ride_volume_this_week",
        "intent_longest_run_with_period",
        "intent_run_volume_count",
        "intent_greeting",
    }


def test_greeting_case_expects_no_tools():
    greeting = next(case for case in load_intent_matrix() if case.id == "intent_greeting")
    assert greeting.expected_tools == ()
    assert greeting.question == "Olá!"
