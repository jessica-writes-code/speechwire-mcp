"""HTTP retrieval functions for SpeechWire tournament results data.

Each function wraps a parser with :func:`_fetch_and_parse` so that
HTTP errors and parse failures return safe defaults.
"""

import logging

from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse
from speechwire_mcp.results.parsers import parse_tab_sheet_from_html

logger = logging.getLogger(__name__)

_BASE = "https://manage.speechwire.com/tabroom/tab-grouping.php"


def get_tab_sheet(grouping_id: int, client: SpeechWireClient) -> dict:
    """Retrieve the results tab sheet for a specific grouping.

    Parameters
    ----------
    grouping_id : int
        Numeric grouping identifier (from ``speechwire_list_groupings``).
    client : SpeechWireClient
        Authenticated client with an active tournament session.

    Returns
    -------
    dict
        Parsed results containing ``grouping_name``, ``round_names``,
        and ``competitors`` with round-by-round outcomes, speaker
        scores, and placements.
    """
    url = f"{_BASE}"
    params = {
        "groupingid": str(grouping_id),
        "Submit": "View tab sheet",
        "sortby": "",
        "divisionrestrict": "",
    }
    return _fetch_and_parse(
        client,
        url,
        parse_tab_sheet_from_html,
        default={},
        context=f"tab sheet for grouping {grouping_id}",
        params=params,
    )
