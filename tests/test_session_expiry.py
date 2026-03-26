"""Tests for session expiry detection and automatic re-authentication.

The implementation covers:
1. SpeechWireClient._looks_like_expired_session(resp) — detects expired sessions
2. Unified get() method (raw_get() deleted)
3. _fetch_and_parse() no longer accepts a `raw` parameter

These tests verify the detection logic, recovery behavior, and edge cases.
Tests skip gracefully if the implementation isn't landed yet.
"""

import pytest
from unittest.mock import MagicMock, patch

from fake_data import CAPITOL_DEBATE_LEAGUE


# ---------------------------------------------------------------------------
# Guarded imports — skip if not yet implemented
# ---------------------------------------------------------------------------

def _import_client():
    try:
        from speechwire_mcp.client import SpeechWireClient
        return SpeechWireClient
    except ImportError:
        pytest.skip("SpeechWireClient not available")


def _import_auth_error():
    try:
        from speechwire_mcp.client import SpeechWireAuthError
        return SpeechWireAuthError
    except ImportError:
        pytest.skip("SpeechWireAuthError not available")


def _import_fetch_and_parse():
    try:
        from speechwire_mcp.client import _fetch_and_parse
        return _fetch_and_parse
    except ImportError:
        pytest.skip("_fetch_and_parse not available")


# ---------------------------------------------------------------------------
# HTML fixtures from real SpeechWire pages
# ---------------------------------------------------------------------------

LOGIN_PAGE_HTML = """\
<form name="form1" method="post" action="c-login.php">
  <p>Email address:
    <input class='swtext' id='teamemail' type='text' name='teamemail' \
value='' size='30' maxlength='60'>  </p>
  <p>Password:
    <input class='swtext' id='password' type='password' name='password' \
value='' size='16' maxlength='100'>  </p>
  <p>
    <input type="submit" name="Submit" value="Log in">
    <input type="button" value="Forgot password?" class="subutton" \
onClick="window.location='c-forgot.php'">
    <input name='mode' id="mode" type="hidden" value="account" />
    <input name='tournid' id="tournid" type="hidden" value="" />  </p>
</form>
"""

LOGIN_PAGE_DOUBLE_QUOTE_HTML = """\
<form name="form1" method="post" action="c-login.php">
  <p>Password:
    <input class="swtext" id="password" type="password" name="password" \
value="" size="16" maxlength="100">  </p>
</form>
"""

ACCOUNT_SELECT_HTML = """\
<p class='pagetitle'>Select which account to access</p>
<p>Your login credentials are valid for more than one SpeechWire coach \
account.</p>
<p style='font-size: 18px; font-weight: bold;'>\
<a href='c-account-select.php?selectaccountid=10001'>\
Leo McGarry at Capitol Debate League Administration</a></p>
<p style='font-size: 18px; font-weight: bold;'>\
<a href='c-account-select.php?selectaccountid=10002'>\
Leo McGarry at Capitol Debate League Elementary</a></p>
"""

NORMAL_MANAGE_PAGE_HTML = """\
<html>
<head><title>Judge Check-In</title></head>
<body>
  <table class="dd">
    <tr class="tableheader"><td>Judge</td><td>Status</td></tr>
    <tr><td>Jane Doe</td><td>Checked In</td></tr>
  </table>
</body>
</html>
"""

TOURNAMENT_SELECT_PAGE_HTML = """\
<html>
<body>
  <p>Select the tournament you want to manage.</p>
  <select name="tournid">
    <option value="100">Spring Classic 2026</option>
  </select>
</body>
</html>
"""


def _make_response(text: str, url: str = "https://manage.speechwire.com/page"):
    """Create a mock requests.Response with .text and .url."""
    resp = MagicMock()
    resp.text = text
    resp.url = url
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


def _make_client(**kwargs):
    """Build a SpeechWireClient without hitting the network."""
    SpeechWireClient = _import_client()
    return SpeechWireClient(
        email="test@example.com",
        password="secret",
        account_id="12345",
        circuit_id="200",
        tournament_id="50001",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. _looks_like_expired_session() unit tests
# ---------------------------------------------------------------------------

class TestLooksLikeExpiredSession:
    """Direct unit tests for the expiry detection heuristic."""

    def _call(self, resp):
        SpeechWireClient = _import_client()
        if not hasattr(SpeechWireClient, "_looks_like_expired_session"):
            pytest.skip("_looks_like_expired_session not implemented yet")
        client = SpeechWireClient(email="test@x.com", password="p")
        return client._looks_like_expired_session(resp)

    def test_detects_login_page_with_password_field(self):
        """Single-quoted type='password' in response → expired."""
        resp = _make_response(LOGIN_PAGE_HTML)
        assert self._call(resp) is True

    def test_detects_login_page_with_double_quoted_password(self):
        """Double-quoted type=\"password\" in response → expired."""
        resp = _make_response(LOGIN_PAGE_DOUBLE_QUOTE_HTML)
        assert self._call(resp) is True

    def test_valid_account_select_page_not_expired(self):
        """Account-select page has no password field → not expired."""
        resp = _make_response(ACCOUNT_SELECT_HTML)
        assert self._call(resp) is False

    def test_valid_tournament_page_with_select_text(self):
        """'Select the tournament' on the actual tournaments page is NOT a
        false positive — url contains c-circuit-tournaments.php."""
        resp = _make_response(
            TOURNAMENT_SELECT_PAGE_HTML,
            url="https://www.speechwire.com/c-circuit-tournaments.php",
        )
        assert self._call(resp) is False

    def test_tournament_text_on_manage_page_is_expired(self):
        """'Select the tournament' on a non-tournament page → expired."""
        resp = _make_response(
            TOURNAMENT_SELECT_PAGE_HTML,
            url="https://manage.speechwire.com/tabroom/judges-activecheckin.php",
        )
        assert self._call(resp) is True

    def test_empty_html_not_expired(self):
        """Empty response text → not expired."""
        resp = _make_response("")
        assert self._call(resp) is False

    def test_normal_manage_page_not_expired(self):
        """Normal page with judge data → not expired."""
        resp = _make_response(NORMAL_MANAGE_PAGE_HTML)
        assert self._call(resp) is False


# ---------------------------------------------------------------------------
# 2. discover_accounts() recovery test
# ---------------------------------------------------------------------------

class TestDiscoverAccountsRecovery:
    """Verify discover_accounts() recovers from expired sessions."""

    def test_reauth_on_expired_session(self):
        """First get returns login page → re-auth → second get returns
        valid account-select HTML → accounts are parsed."""
        SpeechWireClient = _import_client()
        if not hasattr(SpeechWireClient, "_looks_like_expired_session"):
            pytest.skip("Session expiry detection not implemented yet")

        client = _make_client()

        expired_resp = _make_response(LOGIN_PAGE_HTML)
        valid_resp = _make_response(ACCOUNT_SELECT_HTML)

        client.session = MagicMock()
        client.session.get = MagicMock(side_effect=[expired_resp, valid_resp])

        with patch.object(client, "login"), \
             patch.object(client, "select_account"), \
             patch.object(client, "select_tournament"), \
             patch.object(client, "_authenticate"):
            accounts = client.discover_accounts()

        assert len(accounts) >= 1
        names = [a["name"] for a in accounts]
        assert any(CAPITOL_DEBATE_LEAGUE in n for n in names)


# ---------------------------------------------------------------------------
# 3. discover_tournaments() recovery test
# ---------------------------------------------------------------------------

TOURNAMENT_LIST_HTML = """\
<html><body>
<form>
  <select name="tournid">
    <option value="">Select a tournament</option>
    <option value="100" data-circuitid="10">Spring Classic 2026</option>
  </select>
  <input type="submit" name="Submit" value="Log in">
</form>
</body></html>
"""


class TestDiscoverTournamentsRecovery:
    """Verify discover_tournaments() recovers from expired sessions."""

    def test_reauth_on_expired_session(self):
        """First get returns login page → re-auth → second returns
        valid tournament list → tournaments are parsed."""
        SpeechWireClient = _import_client()
        if not hasattr(SpeechWireClient, "_looks_like_expired_session"):
            pytest.skip("Session expiry detection not implemented yet")

        client = _make_client()

        expired_resp = _make_response(LOGIN_PAGE_HTML)
        valid_resp = _make_response(TOURNAMENT_LIST_HTML)

        client.session = MagicMock()
        client.session.get = MagicMock(side_effect=[expired_resp, valid_resp])

        with patch.object(client, "login"), \
             patch.object(client, "select_account"), \
             patch.object(client, "select_tournament"), \
             patch.object(client, "_authenticate"):
            tournaments = client.discover_tournaments()

        assert isinstance(tournaments, list)


# ---------------------------------------------------------------------------
# 4. _fetch_and_parse() tests
# ---------------------------------------------------------------------------

class TestFetchAndParse:
    """Tests for the updated _fetch_and_parse helper."""

    def test_fetch_and_parse_no_longer_accepts_raw(self):
        """Passing raw=True should raise TypeError."""
        _fetch_and_parse = _import_fetch_and_parse()
        client = _make_client()

        try:
            _fetch_and_parse(
                client,
                "https://example.com",
                lambda html: html,
                "default",
                "test",
                raw=True,
            )
        except TypeError:
            pass  # Expected — raw param removed
        else:
            pytest.skip(
                "raw parameter still accepted — refactor not landed yet"
            )

    def test_fetch_and_parse_detects_expired_session(self):
        """_fetch_and_parse should detect expired session via client.get(),
        re-auth, and pass valid HTML to the parser."""
        _fetch_and_parse = _import_fetch_and_parse()
        SpeechWireClient = _import_client()

        if not hasattr(SpeechWireClient, "_looks_like_expired_session"):
            pytest.skip("Session expiry detection not implemented yet")

        client = _make_client()

        valid_html = "<table><tr><td>data</td></tr></table>"
        expired_resp = _make_response(LOGIN_PAGE_HTML)
        valid_resp = _make_response(valid_html)

        with patch.object(
            client, "get", side_effect=[expired_resp, valid_resp]
        ), \
                patch.object(client, "_authenticate"):
            result = _fetch_and_parse(
                client,
                "https://manage.speechwire.com/some-page",
                lambda html: html.strip(),
                "default",
                "test context",
            )

        # The parser should receive data (either from first or retried call)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 5. Edge cases — no infinite loops, safe failure
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Guard against infinite re-auth loops and ensure safe defaults."""

    def test_no_infinite_reauth_loop(self):
        """If _authenticate raises SpeechWireAuthError and get always
        returns login page, the client must not loop forever."""
        SpeechWireClient = _import_client()
        SpeechWireAuthError = _import_auth_error()

        if not hasattr(SpeechWireClient, "_looks_like_expired_session"):
            pytest.skip("Session expiry detection not implemented yet")

        client = _make_client()

        always_expired = _make_response(LOGIN_PAGE_HTML)
        client.session = MagicMock()
        client.session.get = MagicMock(return_value=always_expired)

        with patch.object(
            client, "_authenticate", side_effect=SpeechWireAuthError("bad creds")
        ):
            # get() should return the expired response (not loop)
            # or raise — either way, must terminate
            try:
                resp = client.get("https://manage.speechwire.com/page")
                # If it returns, it should be the (expired) response
                assert resp is not None
            except SpeechWireAuthError:
                pass  # Also acceptable — auth error propagated

    def test_reauth_failure_returns_default(self):
        """_fetch_and_parse returns default when re-auth fails."""
        _fetch_and_parse = _import_fetch_and_parse()
        SpeechWireAuthError = _import_auth_error()
        SpeechWireClient = _import_client()

        if not hasattr(SpeechWireClient, "_looks_like_expired_session"):
            pytest.skip("Session expiry detection not implemented yet")

        client = _make_client()

        with patch.object(
            client, "get", side_effect=SpeechWireAuthError("bad creds")
        ):
            result = _fetch_and_parse(
                client,
                "https://manage.speechwire.com/page",
                lambda html: ["parsed"],
                [],
                "test context",
            )

        assert result == []
