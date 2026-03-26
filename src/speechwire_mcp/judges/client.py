from typing import List, Dict

from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse
from speechwire_mcp.judges.parsers import (
    parse_judge_list_from_html,
    parse_judge_edit_contact_html,
    parse_availability_from_edit_html,
    parse_school_from_edit_html,
)


def get_judge_list(client: SpeechWireClient) -> List[Dict]:
    """Retrieve judge list with roster details from the dashboard."""

    # Local _parse wrapper filters out records with None judgeid (business logic,
    # not parsing) — this pattern is used when post-processing is needed after
    # HTML parsing. See get_judge_availability for comparison (no wrapper needed).
    def _parse(html: str) -> List[Dict]:
        records = parse_judge_list_from_html(html)
        return [r for r in records if r.get("judgeid") is not None]

    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/judges-activecheckin.php",
        _parse,
        default=[],
        context="judge dashboard for list",
    )


def get_judge_contact(judge_id: int, client: SpeechWireClient) -> Dict:
    """Fetch judge edit page and return contact information.

    Returns a dict with judgeid, email, phone.
    """

    # Local _parse wrapper injects the judgeid parameter into the result (business
    # logic, not parsing). The parser only extracts email/phone from HTML.
    def _parse(html: str) -> Dict:
        parsed = parse_judge_edit_contact_html(html)
        return {
            "judgeid": judge_id,
            "email": parsed.get("email"),
            "phone": parsed.get("phone"),
        }

    return _fetch_and_parse(
        client,
        f"https://manage.speechwire.com/tabroom/view-judge.php?judgeid={judge_id}",
        _parse,
        default={
            "judgeid": judge_id,
            "email": None,
            "phone": None,
        },
        context=f"judge contact for {judge_id}",
    )


def get_judge_availability(
    judge_id: int, client: SpeechWireClient
) -> List[Dict]:
    """Fetch and parse a judge's availability from their edit page."""
    return _fetch_and_parse(
        client,
        f"https://manage.speechwire.com/tabroom/judges-edit.php?judgeid={judge_id}",
        parse_availability_from_edit_html,
        default=[],
        context=f"availability for {judge_id}",
    )


def get_judge_school(judge_id: int, client: SpeechWireClient) -> Dict:
    """Fetch judge edit page and return school association.

    Returns a dict with judgeid, school, and team_id.
    """

    def _parse(html: str) -> Dict:
        parsed = parse_school_from_edit_html(html)
        return {
            "judgeid": judge_id,
            "school": parsed.get("school"),
            "team_id": parsed.get("team_id"),
        }

    return _fetch_and_parse(
        client,
        f"https://manage.speechwire.com/tabroom/judges-edit.php?judgeid={judge_id}",
        _parse,
        default={
            "judgeid": judge_id,
            "school": None,
            "team_id": None,
        },
        context=f"school for {judge_id}",
    )
