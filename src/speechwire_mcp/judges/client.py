from typing import List, Dict
import logging

from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse, _post_and_parse
from speechwire_mcp.judges.parsers import (
    parse_judge_list_from_html,
    parse_judge_edit_contact_html,
    parse_availability_from_edit_html,
    parse_school_from_edit_html,
    parse_add_judge_response,
)

logger = logging.getLogger(__name__)


def get_judge_list(client: SpeechWireClient) -> List[Dict]:
    """Retrieve judge list with roster details from the dashboard."""

    # Local _parse wrapper filters out records with None judge_id (business logic,
    # not parsing) — this pattern is used when post-processing is needed after
    # HTML parsing. See get_judge_availability for comparison (no wrapper needed).
    def _parse(html: str) -> List[Dict]:
        records = parse_judge_list_from_html(html)
        return [r for r in records if r.get("judge_id") is not None]

    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/judges-activecheckin.php",
        _parse,
        default=[],
        context="judge dashboard for list",
    )


def get_judge_contact(judge_id: int, client: SpeechWireClient) -> Dict:
    """Fetch judge edit page and return contact information.

    Returns a dict with judge_id, email, phone.
    """

    # Local _parse wrapper injects the judge_id parameter into the result (business
    # logic, not parsing). The parser only extracts email/phone from HTML.
    def _parse(html: str) -> Dict:
        parsed = parse_judge_edit_contact_html(html)
        return {
            "judge_id": judge_id,
            "email": parsed.get("email"),
            "phone": parsed.get("phone"),
        }

    return _fetch_and_parse(
        client,
        f"https://manage.speechwire.com/tabroom/view-judge.php?judgeid={judge_id}",
        _parse,
        default={
            "judge_id": judge_id,
            "email": None,
            "phone": None,
        },
        context=f"judge contact for {judge_id}",
    )


def get_judge_availability(judge_id: int, client: SpeechWireClient) -> List[Dict]:
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

    Returns a dict with judge_id, school, and team_id.
    """

    def _parse(html: str) -> Dict:
        parsed = parse_school_from_edit_html(html)
        return {
            "judge_id": judge_id,
            "school": parsed.get("school"),
            "team_id": parsed.get("team_id"),
        }

    return _fetch_and_parse(
        client,
        f"https://manage.speechwire.com/tabroom/judges-edit.php?judgeid={judge_id}",
        _parse,
        default={
            "judge_id": judge_id,
            "school": None,
            "team_id": None,
        },
        context=f"school for {judge_id}",
    )


_VALID_JUDGE_TYPE_IDS = {0, 10, 11, 12, 13, 14}


def add_judge(
    client: SpeechWireClient,
    judge_name: str,
    judge_email: str = "",
    team_id: int = 0,
    judge_type_id: int = 0,
    is_clean: bool = False,
    is_coach: bool = False,
    is_priority: bool = False,
    available_slots: list[int] | None = None,
) -> Dict:
    """Add a new judge to the active tournament.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with a tournament selected.
    judge_name : str
        Judge's full name (required, max 50 characters).
    judge_email : str
        Email address (optional, max 50 characters).
    team_id : int
        Team/school ID. Use 0 for no team.
    judge_type_id : int
        Judge type: 0=none, 10=A, 11=B, 12=C, 13=D, 14=E.
    is_clean : bool
        Clean/neutral judge flag.
    is_coach : bool
        Coach flag.
    is_priority : bool
        Priority judge flag.
    available_slots : list[int] | None
        1-indexed time slot numbers the judge is available for.
        If None or empty, judge is blocked for all slots.

    Returns
    -------
    dict
        ``{"success": bool, "judge_id": int | None, "error": str | None}``
    """
    # --- input validation ---
    if not judge_name.strip():
        return {"success": False, "judge_id": None, "error": "judge_name is required"}
    if len(judge_name.strip()) > 50:
        return {
            "success": False,
            "judge_id": None,
            "error": "judge_name must be 50 characters or fewer",
        }
    if len(judge_email.strip()) > 50:
        return {
            "success": False,
            "judge_id": None,
            "error": "judge_email must be 50 characters or fewer",
        }
    if judge_type_id not in _VALID_JUDGE_TYPE_IDS:
        return {
            "success": False,
            "judge_id": None,
            "error": "invalid judge_type_id; must be 0, 10, 11, 12, 13, or 14",
        }
    if not team_id:
        return {
            "success": False,
            "judge_id": None,
            "error": "team_id is required (use speechwire_list_teams to find valid IDs)",
        }

    # --- pre-fetch the add-judge form (required for server-side session state) ---
    _ADD_JUDGE_URL = "https://manage.speechwire.com/tabroom/judges-add.php"
    _EDIT_JUDGE_URL = "https://manage.speechwire.com/tabroom/judges-edit.php"
    try:
        client.session.get(_ADD_JUDGE_URL)
    except Exception:
        logger.warning("Failed to pre-fetch add-judge form")

    # --- build form data ---
    form_data: dict[str, str] = {
        "judgename": judge_name.strip(),
        "judgeemail": judge_email.strip(),
        "teamid": str(team_id),
        "judgetypeid": str(judge_type_id),
        "judgeisclean": "1" if is_clean else "0",
        "judgeiscoach": "1" if is_coach else "0",
        "judgeispriority": "1" if is_priority else "0",
        "mode": "addjudge",
        "Submit": "Create judge",
    }
    if available_slots:
        for slot in available_slots:
            form_data[f"slotunblock[{slot}]"] = "1"

    return _post_and_parse(
        client,
        _EDIT_JUDGE_URL,
        form_data,
        parse_add_judge_response,
        default={"success": False, "judge_id": None, "error": "request failed"},
        context="add judge",
    )
