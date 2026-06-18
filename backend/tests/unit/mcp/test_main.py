from convertreino.mcp.__main__ import main


def test_main_runs_mcp_server_with_stdio_transport(monkeypatch):
    # Arrange
    calls: list[str] = []

    class FakeServer:
        def run(self) -> None:
            calls.append("run")

    monkeypatch.setattr("convertreino.mcp.__main__.create_mcp_server", lambda: FakeServer())

    # Act
    main()

    # Assert
    assert calls == ["run"]
