import logging

from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse
from speechwire_mcp.teams.parsers import (
    parse_team_list_html,
    parse_team_entries_html,
    parse_hybrid_entries_html,
)

logger = logging.getLogger(__name__)


def get_team_list(client: SpeechWireClient) -> list[dict]:
    """Retrieve team list from the dashboard.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client instance.

    Returns
    -------
    list[dict]
        Team records with team_id, name, code, is_invited, is_attending,
        is_checked_in, is_udl_member.
    """

    def _parse(html: str) -> list[dict]:
        records = parse_team_list_html(html)
        return [r for r in records if r.get("team_id") is not None]

    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/teams-list.php",
        _parse,
        default=[],
        context="team list",
    )


def get_team_entries(team_id: int, client: SpeechWireClient) -> list[dict]:
    """Retrieve entries for a specific team.

    Parameters
    ----------
    team_id : int
        Numeric team identifier.
    client : SpeechWireClient
        Authenticated client instance.

    Returns
    -------
    list[dict]
        Entry records with event_id, event_name, entry_number, entry_code,
        competitors, division, division_id, is_dropped.
    """
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/teams-entries.php",
        parse_team_entries_html,
        default=[],
        context=f"entries for team {team_id}",
        params={"teamid": str(team_id)},
    )


def get_hybrid_entries(client: SpeechWireClient) -> list[dict]:
    """Retrieve hybrid entries from the dashboard.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client instance.

    Returns
    -------
    list[dict]
        Hybrid entry records with comp_id, event, division, students, code,
        team_blocks.
    """
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/teams-hybrids.php",
        parse_hybrid_entries_html,
        default=[],
        context="hybrid entries",
    )
