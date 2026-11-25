from unittest.mock import patch


def test_flask_cli_reuses_authorization_and_does_not_print_credentials(app):
    app.config.update(NOTES_GOOGLE_CLIENT_SECRETS="outside/client.json", NOTES_GOOGLE_TOKEN="outside/token.json")
    with patch("guided_notes.notes.cli.authorize", return_value=object()) as helper:
        result = app.test_cli_runner().invoke(args=["authorize-sheets"])
    assert result.exit_code == 0
    assert helper.call_args.kwargs["interactive"] is True
    assert "token.json" not in result.output


def test_flask_cli_sanitizes_authorization_errors(app):
    from guided_notes.notes.google_authorization import AuthError
    with patch("guided_notes.notes.cli.authorize", side_effect=AuthError("GOOGLE_REAUTH_REQUIRED")):
        result = app.test_cli_runner().invoke(args=["authorize-sheets"])
    assert result.exit_code != 0
    assert "GOOGLE_REAUTH_REQUIRED" in result.output
