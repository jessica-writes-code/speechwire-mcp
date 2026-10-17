"""HTTP retrieval functions for SpeechWire room data.

Each function wraps a parser with :func:`_fetch_and_parse` so that
HTTP errors and parse failures return safe defaults.
"""

import logging

from speechwire_mcp.client import SpeechWireClient, SpeechWireReadError, _fetch_and_parse
from speechwire_mcp.rooms.parsers import (
    GroupingRoundCounts,
    parse_grouping_round_counts_from_html,
    parse_room_counts_from_html,
    parse_room_list_from_html,
    parse_room_usage_from_html,
)

logger = logging.getLogger(__name__)


def get_grouping_round_counts(
    grouping_id: int,
    round_number: int,
    client: SpeechWireClient,
    *,
    raise_on_error: bool = False,
) -> GroupingRoundCounts | None:
    """Read entry and section totals from a grouping/round room-detail page.

    Parameters
    ----------
    grouping_id : int
        Positive grouping ID from ``get_groupings``.
    round_number : int
        Positive 1-based round number applicable to this grouping.
    client : SpeechWireClient
        Authenticated client with an active tournament session.
    raise_on_error : bool
        Raise ``SpeechWireReadError`` on invalid identifiers, fetch failures,
        or missing/malformed/mismatched summaries. Defaults to False.

    Returns
    -------
    GroupingRoundCounts | None
        ``grouping_id``, ``round_number``, ``entries`` and ``sections`` (ints).
        Explicit zero counts are valid. Returns None on failure in default mode;
        never infers entries from rooms, sections, or an absent summary.
    """
    if grouping_id <= 0 or round_number <= 0:
        message = "Grouping ID and round number must be positive integers"
        logger.error(message)
        if raise_on_error:
            raise SpeechWireReadError(message)
        return None

    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/rooms-groupings.php",
        lambda html: parse_grouping_round_counts_from_html(html, grouping_id, round_number),
        default=None,
        context=f"counts for grouping {grouping_id}, round {round_number}",
        params={"groupinground": f"{grouping_id},{round_number}"},
        raise_on_error=raise_on_error,
    )


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


def get_room_counts(
    client: SpeechWireClient, *, raise_on_error: bool = False
) -> list[dict]:
    """Retrieve per-grouping room vs. section counts from the rooms-counts page.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with an active tournament session.
    raise_on_error : bool
        Raise on provider read failure instead of returning an empty list.

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
        raise_on_error=raise_on_error,
    )
