from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse
from speechwire_mcp.schematics.parsers import (
    parse_schematic_events_html,
    parse_round_schematic_html,
)


def get_schematic_events(client: SpeechWireClient) -> list[dict]:
    """Retrieve the list of schematic events with available rounds."""
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/schem-view.php",
        parse_schematic_events_html,
        default=[],
        context="schematic events list",
    )


def get_round_schematic(
    grouping_id: int, round_number: int, client: SpeechWireClient
) -> dict:
    """Retrieve the schematic for a specific event round.

    Parameters
    ----------
    grouping_id : int
        Event grouping identifier.
    round_number : int
        Round number.
    client : SpeechWireClient
        Authenticated client instance.

    Returns
    -------
    dict
        Round schematic with event name, time, unused judges, and sections.
    """
    url = (
        f"https://manage.speechwire.com/tabroom/schem-edit.php"
        f"?groupingid={grouping_id}&round={round_number}"
    )
    return _fetch_and_parse(
        client,
        url,
        parse_round_schematic_html,
        default={},
        context=f"round schematic for grouping {grouping_id} round {round_number}",
    )
