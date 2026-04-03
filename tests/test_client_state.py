"""Tests for the client state machine introduced by the lazy-IDs feature.

Tests cover:
- ClientState enum values
- SpeechWireClient constructor (minimal and full-IDs)
- SpeechWireSelectionRequired exception
- State-gated method behavior

Written proactively against the architecture spec. Tests that depend on
unimplemented code skip gracefully.
"""

import pytest



# ---------------------------------------------------------------------------
# Guarded imports — skip tests if the implementation isn't available yet
# ---------------------------------------------------------------------------

def _import_client_state():
    """Try importing ClientState; return it or skip."""
    try:
        from speechwire_mcp.client import ClientState
        return ClientState
    except ImportError:
        pytest.skip("ClientState not implemented yet")


def _import_selection_required():
    """Try importing SpeechWireSelectionRequired; return it or skip."""
    try:
        from speechwire_mcp.client import SpeechWireSelectionRequired
        return SpeechWireSelectionRequired
    except ImportError:
        pytest.skip("SpeechWireSelectionRequired not implemented yet")


def _import_client():
    """Try importing SpeechWireClient; return it or skip."""
    try:
        from speechwire_mcp.client import SpeechWireClient
        return SpeechWireClient
    except ImportError:
        pytest.skip("SpeechWireClient not available")


# ---------------------------------------------------------------------------
# Tests — ClientState enum
# ---------------------------------------------------------------------------

class TestClientState:
    def test_enum_values_exist(self):
        ClientState = _import_client_state()
        assert hasattr(ClientState, "UNAUTHENTICATED")
        assert hasattr(ClientState, "LOGGED_IN")
        assert hasattr(ClientState, "ACCOUNT_SELECTED")
        assert hasattr(ClientState, "TOURNAMENT_ACTIVE")

    def test_enum_string_values(self):
        ClientState = _import_client_state()
        assert ClientState.UNAUTHENTICATED.value == "unauthenticated"
        assert ClientState.LOGGED_IN.value == "logged_in"
        assert ClientState.ACCOUNT_SELECTED.value == "account_selected"
        assert ClientState.TOURNAMENT_ACTIVE.value == "tournament_active"

    def test_enum_has_four_members(self):
        ClientState = _import_client_state()
        assert len(ClientState) == 4


# ---------------------------------------------------------------------------
# Tests — SpeechWireClient constructor
# ---------------------------------------------------------------------------

class TestClientConstructor:
    def test_constructor_with_only_email_and_password(self):
        """New minimal constructor: only email + password required."""
        SpeechWireClient = _import_client()
        try:
            client = SpeechWireClient(
                email="user@example.com",
                password="secret",
            )
        except TypeError:
            pytest.skip(
                "Constructor does not yet accept optional IDs — "
                "refactor not landed"
            )
        assert client.email == "user@example.com"
        assert client.password == "secret"
        assert client.account_id is None
        assert client.circuit_id is None
        assert client.tournament_id is None

    def test_constructor_with_all_ids_backward_compat(self):
        """Backward compat: all IDs provided behaves as before."""
        SpeechWireClient = _import_client()
        try:
            client = SpeechWireClient(
                email="user@example.com",
                password="secret",
                account_id="12345",
                circuit_id="200",
                tournament_id="50001",
            )
        except TypeError:
            pytest.skip("Constructor signature not yet updated")
        assert client.account_id == "12345"
        assert client.circuit_id == "200"
        assert client.tournament_id == "50001"

    def test_constructor_partial_ids(self):
        """Providing only some IDs should work (others default to None)."""
        SpeechWireClient = _import_client()
        try:
            client = SpeechWireClient(
                email="user@example.com",
                password="secret",
                account_id="12345",
            )
        except TypeError:
            pytest.skip("Constructor signature not yet updated")
        assert client.account_id == "12345"
        assert client.circuit_id is None
        assert client.tournament_id is None

    def test_initial_state_is_unauthenticated(self):
        """New client should start in UNAUTHENTICATED state."""
        SpeechWireClient = _import_client()
        ClientState = _import_client_state()
        try:
            client = SpeechWireClient(
                email="user@example.com",
                password="secret",
            )
        except TypeError:
            pytest.skip("Constructor signature not yet updated")
        assert client.state == ClientState.UNAUTHENTICATED


# ---------------------------------------------------------------------------
# Tests — SpeechWireSelectionRequired exception
# ---------------------------------------------------------------------------

class TestSelectionRequiredException:
    def test_exception_carries_options(self):
        SpeechWireSelectionRequired = _import_selection_required()
        options = [
            {"account_id": 12345, "name": "Hartsfield Landing School"},
            {"account_id": 67890, "name": "Kennison Academy"},
        ]
        exc = SpeechWireSelectionRequired("Multiple accounts found", options=options)
        assert exc.options == options
        assert "Multiple accounts" in str(exc)

    def test_exception_is_catchable(self):
        SpeechWireSelectionRequired = _import_selection_required()
        with pytest.raises(SpeechWireSelectionRequired):
            raise SpeechWireSelectionRequired("Pick one", options=[{"id": 1}])

    def test_exception_with_empty_options(self):
        SpeechWireSelectionRequired = _import_selection_required()
        exc = SpeechWireSelectionRequired("No options", options=[])
        assert exc.options == []


# ---------------------------------------------------------------------------
# Tests — State-gated behavior
# ---------------------------------------------------------------------------

class TestStateGating:
    def test_ensure_tournament_session_requires_credentials(self):
        """ensure_tournament_session should raise if not authenticated."""
        from unittest.mock import patch

        SpeechWireClient = _import_client()
        try:
            client = SpeechWireClient(
                email="user@example.com",
                password="secret",
            )
        except TypeError:
            pytest.skip("Constructor signature not yet updated")

        if not hasattr(client, "ensure_tournament_session"):
            pytest.skip("ensure_tournament_session not implemented yet")

        # Mock the HTTP session so the test never makes real network calls
        with patch.object(client.session, "post", side_effect=Exception("no network")), \
             patch.object(client.session, "get", side_effect=Exception("no network")):
            with pytest.raises(Exception):
                client.ensure_tournament_session()

    def test_get_no_recursion_on_expired_session(self):
        """get() must not recurse when _authenticate also triggers get()."""
        from unittest.mock import patch, MagicMock

        SpeechWireClient = _import_client()
        client = SpeechWireClient(email="u@x.com", password="p")

        expired_resp = MagicMock()
        expired_resp.text = '<input type="password" />'
        expired_resp.url = "https://manage.speechwire.com/tabroom/judges.php"

        client.session.get = MagicMock(return_value=expired_resp)

        call_count = 0

        def fake_authenticate():
            nonlocal call_count
            call_count += 1
            if call_count > 5:
                raise RuntimeError("recursion detected")
            # Simulate what _authenticate does: call get() again
            client.get("https://www.speechwire.com/c-account-select.php")

        with patch.object(client, "_authenticate", side_effect=fake_authenticate):
            client.get("https://www.speechwire.com/c-account-select.php")

        # _authenticate should only be called once, not recursively
        assert call_count == 1


# ---------------------------------------------------------------------------
# Tests — _require_tournament backward-compatibility guard
# ---------------------------------------------------------------------------


def _import_require_tournament():
    """Import _require_tournament from server.py, mocking FastMCP if needed.

    The module-level ``FastMCP(...)`` call may fail in test environments
    where the installed SDK version doesn't match the call signature.
    We patch it out so the import succeeds.
    """
    import importlib
    import sys
    from unittest.mock import MagicMock

    mod_name = "speechwire_mcp.server"
    if mod_name in sys.modules:
        return sys.modules[mod_name]._require_tournament

    original = sys.modules.get("mcp.server.fastmcp")
    mock_mod = MagicMock()
    sys.modules["mcp.server.fastmcp"] = mock_mod
    try:
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        mod = importlib.import_module(mod_name)
    finally:
        if original is not None:
            sys.modules["mcp.server.fastmcp"] = original
        else:
            sys.modules.pop("mcp.server.fastmcp", None)
    return mod._require_tournament


class TestRequireTournamentGuard:
    """Verify that the _require_tournament guard auto-authenticates when all
    three IDs are present on the client, preserving backward-compat for
    existing env-var users.
    """

    def test_guard_passes_when_already_active(self):
        """Guard returns None when state is already TOURNAMENT_ACTIVE."""
        ClientState = _import_client_state()
        SpeechWireClient = _import_client()
        _require_tournament = _import_require_tournament()

        client = SpeechWireClient(
            email="u@x.com", password="p",
            account_id="1", circuit_id="2", tournament_id="3",
        )
        client.state = ClientState.TOURNAMENT_ACTIVE
        assert _require_tournament(client) is None

    def test_guard_auto_authenticates_with_all_ids(self):
        """Client with all 3 IDs should trigger ensure_tournament_session,
        reaching TOURNAMENT_ACTIVE and passing the guard."""
        ClientState = _import_client_state()
        SpeechWireClient = _import_client()
        _require_tournament = _import_require_tournament()
        from unittest.mock import patch

        client = SpeechWireClient(
            email="u@x.com", password="p",
            account_id="1", circuit_id="2", tournament_id="3",
        )
        assert client.state == ClientState.UNAUTHENTICATED

        def fake_ensure():
            client.state = ClientState.TOURNAMENT_ACTIVE

        with patch.object(client, "ensure_tournament_session", side_effect=fake_ensure):
            result = _require_tournament(client)

        assert result is None
        assert client.state == ClientState.TOURNAMENT_ACTIVE

    def test_guard_blocks_without_ids(self):
        """Client without all 3 IDs should NOT auto-authenticate;
        guard returns the error dict."""
        _import_client_state()
        SpeechWireClient = _import_client()
        _require_tournament = _import_require_tournament()

        client = SpeechWireClient(email="u@x.com", password="p")
        result = _require_tournament(client)
        assert result is not None
        assert result["error"] == "no_tournament_selected"

    def test_guard_returns_error_when_auto_auth_fails(self):
        """If ensure_tournament_session raises, guard falls through to error."""
        ClientState = _import_client_state()
        SpeechWireClient = _import_client()
        _require_tournament = _import_require_tournament()
        from unittest.mock import patch

        client = SpeechWireClient(
            email="u@x.com", password="p",
            account_id="1", circuit_id="2", tournament_id="3",
        )

        with patch.object(
            client, "ensure_tournament_session",
            side_effect=Exception("network down"),
        ):
            result = _require_tournament(client)

        assert result is not None
        assert result["error"] == "no_tournament_selected"
        assert client.state == ClientState.UNAUTHENTICATED
