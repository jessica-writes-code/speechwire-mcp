"""HTTP retrieval functions for SpeechWire tournament structure data.

Each function wraps a parser with :func:`_fetch_and_parse` so that
HTTP errors and parse failures return safe defaults.
"""

import logging

from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse
from speechwire_mcp.structure.parsers import (
    parse_groupings_from_html,
    parse_timeslots_from_html,
)

logger = logging.getLogger(__name__)


def get_timeslots(
    client: SpeechWireClient, *, raise_on_error: bool = False
) -> list[dict]:
    """Retrieve the tournament schedule (timeslots) from the slots-list page.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with an active tournament session.
    raise_on_error : bool
        Raise on provider read failure instead of returning an empty list.

    Returns
    -------
    list[dict]
        Timeslot records with ``slot_id``, ``time``, ``description``,
        ``date``, and ``round_assignments``.
    """
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/slots-list.php",
        parse_timeslots_from_html,
        default=[],
        context="timeslots",
        raise_on_error=raise_on_error,
    )


def get_groupings(
    client: SpeechWireClient, *, raise_on_error: bool = False
) -> list[dict]:
    """Retrieve competition groupings from the groupings-manage page.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with an active tournament session.
    raise_on_error : bool
        Raise on provider read failure instead of returning an empty list.

    Returns
    -------
    list[dict]
        Grouping records with ``grouping_id``, ``name``, ``abbreviation``,
        ``event``, and ``divisions``.
    """
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/groupings-manage.php",
        parse_groupings_from_html,
        default=[],
        context="groupings",
        raise_on_error=raise_on_error,
    )
