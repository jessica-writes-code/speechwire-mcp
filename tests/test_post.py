"""Tests for the POST infrastructure: SpeechWireClient.post() and _post_and_parse."""

import pytest
from unittest.mock import MagicMock, patch


def _import_client():
    try:
        from speechwire_mcp.client import SpeechWireClient

        return SpeechWireClient
    except ImportError:
        pytest.skip("SpeechWireClient not available")


def _import_post_and_parse():
    import importlib
    import sys

    mod_name = "speechwire_mcp.client"
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
        if hasattr(mod, "_post_and_parse"):
            return mod._post_and_parse
    try:
        mod = importlib.import_module(mod_name)
        return mod._post_and_parse
    except (ImportError, AttributeError):
        pytest.skip("_post_and_parse not implemented yet")


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


def _make_response(text="<html></html>", expired=False):
    """Create a mock response."""
    resp = MagicMock()
    resp.text = text
    resp.url = "https://manage.speechwire.com/page"
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# SpeechWireClient.post() tests
# ---------------------------------------------------------------------------


class TestPost:
    def test_post_returns_response(self):
        """post() returns the response from session.post when session is valid."""
        client = _make_client()
        if not hasattr(client, "post"):
            pytest.skip("post() not implemented yet")

        normal_resp = _make_response("<html>OK</html>")
        client.session = MagicMock()
        client.session.post = MagicMock(return_value=normal_resp)

        with patch.object(client, "_looks_like_expired_session", return_value=False):
            result = client.post("https://manage.speechwire.com/page", {"key": "val"})

        assert result is normal_resp
        client.session.post.assert_called_once()

    def test_post_retries_on_expired_session(self):
        """post() detects expired session, re-authenticates, and retries."""
        client = _make_client()
        if not hasattr(client, "post"):
            pytest.skip("post() not implemented yet")

        expired_resp = _make_response("<html>login</html>")
        valid_resp = _make_response("<html>OK</html>")

        client.session = MagicMock()
        client.session.post = MagicMock(side_effect=[expired_resp, valid_resp])

        call_count = [0]

        def fake_expired(resp):
            call_count[0] += 1
            return call_count[0] == 1  # first call expired, second not

        with (
            patch.object(client, "_looks_like_expired_session", side_effect=fake_expired),
            patch.object(client, "_authenticate") as mock_auth,
        ):
            resp = client.post("https://manage.speechwire.com/page", {"k": "v"})

        assert resp is not None
        assert client.session.post.call_count == 2
        mock_auth.assert_called_once()


# ---------------------------------------------------------------------------
# _post_and_parse() tests
# ---------------------------------------------------------------------------


class TestPostAndParse:
    def test_post_and_parse_success(self):
        """Parser result is returned when post succeeds."""
        _post_and_parse = _import_post_and_parse()
        client = MagicMock()
        resp = MagicMock()
        resp.text = "<html>data</html>"
        resp.raise_for_status = MagicMock()
        client.post = MagicMock(return_value=resp)

        def parser(html):
            return {"parsed": True}

        result = _post_and_parse(
            client, "https://example.com", {"k": "v"}, parser, {"parsed": False}, "test"
        )
        assert result == {"parsed": True}

    def test_post_and_parse_returns_default_on_http_error(self):
        """Default is returned when post raises an exception."""
        _post_and_parse = _import_post_and_parse()
        client = MagicMock()
        client.post = MagicMock(side_effect=Exception("connection error"))

        default = {"success": False, "judge_id": None, "error": "http error"}
        result = _post_and_parse(client, "https://example.com", {}, lambda h: h, default, "test")
        assert result is default

    def test_post_and_parse_returns_default_on_parse_error(self):
        """Default is returned when the parser raises."""
        _post_and_parse = _import_post_and_parse()
        client = MagicMock()
        resp = MagicMock()
        resp.text = "<html>data</html>"
        resp.raise_for_status = MagicMock()
        client.post = MagicMock(return_value=resp)

        def bad_parser(html):
            raise ValueError("parse failed")

        default = {"success": False}
        result = _post_and_parse(client, "https://example.com", {}, bad_parser, default, "test")
        assert result is default

    def test_post_and_parse_returns_default_when_no_client(self):
        """Default is returned when client is None."""
        _post_and_parse = _import_post_and_parse()

        default = {"success": False, "error": "no client"}
        result = _post_and_parse(None, "https://example.com", {}, lambda h: h, default, "test")
        assert result is default
