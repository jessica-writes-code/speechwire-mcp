"""HTTP retrieval functions for SpeechWire room data.

Each function wraps a parser with :func:`_fetch_and_parse` so that
HTTP errors and parse failures return safe defaults.
"""

import logging

from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse
from speechwire_mcp.rooms.parsers import (
    parse_room_list_from_html,
    parse_room_counts_from_html,
    parse_room_usage_from_html,
)

logger = logging.getLogger(__name__)


def get_room_list(client: SpeechWireClient) -> list[dict]:
    """Retrieve the list of rooms from the rooms-list page.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with an active tournament session.

    Returns
    -------
    list[dict]
        Room records with ``room_id``, ``name``, ``has_constraints``.
    """
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/rooms-list.php",
        parse_room_list_from_html,
        default=[],
        context="room list",
    )


def get_room_usage(client: SpeechWireClient) -> list[dict]:
    """Retrieve room time-slot usage from the rooms-usage page.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with an active tournament session.

    Returns
    -------
    list[dict]
        Room records with ``room_id``, ``room_name``, and ``time_slots``.
    """
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/rooms-usage.php",
        parse_room_usage_from_html,
        default=[],
        context="room usage",
    )


def get_room_counts(client: SpeechWireClient) -> list[dict]:
    """Retrieve per-grouping room vs. section counts from the rooms-counts page.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with an active tournament session.

    Returns
    -------
    list[dict]
        Records with ``grouping_name`` and ``rounds`` (list of per-round
        room/section counts with a ``sufficient`` flag).
    """
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/rooms-counts.php",
        parse_room_counts_from_html,
        default=[],
        context="room counts",
    )
