import inspect

from convertreino.infrastructure.strava.client import StravaActivitySummary, StravaApiClient


def test_strava_api_client_contract():
    # Arrange
    get_activity = StravaApiClient.get_activity
    list_activities = StravaApiClient.list_activities

    # Assert
    assert get_activity.__annotations__["access_token"] is str
    assert get_activity.__annotations__["activity_id"] is int
    assert get_activity.__annotations__["return"] is StravaActivitySummary
    assert list_activities.__annotations__["access_token"] is str
    assert list_activities.__annotations__["return"] == list[StravaActivitySummary]
    assert inspect.isclass(StravaApiClient)
