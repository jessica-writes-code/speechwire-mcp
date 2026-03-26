"""Retrieval functions for the login / discovery workflow.

These sit between the MCP tool layer and the parsers, following the same
``_fetch_and_parse`` pattern used by ``judges/client.py``.
"""

import logging

from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse
from speechwire_mcp.login.parsers import (
    parse_account_list_html,
    parse_tournament_list_html,
)

logger = logging.getLogger(__name__)


def get_accounts(client: SpeechWireClient) -> list[dict]:
    """Fetch and parse the accounts available to the authenticated user.

    The client must be in ``LOGGED_IN`` (or later) state.

    Parameters
    ----------
    client : SpeechWireClient
        An authenticated client instance.

    Returns
    -------
    list[dict]
        Each dict has ``account_id`` (int) and ``name`` (str).
    """
    return _fetch_and_parse(
        client,
        "https://www.speechwire.com/c-account-select.php",
        parse_account_list_html,
        default=[],
        context="account list",
    )


def get_tournaments(client: SpeechWireClient) -> list[dict]:
    """Fetch and parse the tournaments for the selected account.

    The client must be in ``ACCOUNT_SELECTED`` (or later) state.

    Parameters
    ----------
    client : SpeechWireClient
        An authenticated client instance with an account selected.

    Returns
    -------
    list[dict]
        Each dict has ``tournament_id`` (int), ``circuit_id`` (int),
        ``name`` (str), and ``date`` (str | None).
    """
    return _fetch_and_parse(
        client,
        "https://www.speechwire.com/c-circuit-tournaments.php",
        parse_tournament_list_html,
        default=[],
        context="tournament list",
    )
