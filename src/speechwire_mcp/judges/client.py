import logging
import re

from speechwire_mcp.client import SpeechWireClient, _fetch_and_parse, _post_and_parse
from speechwire_mcp.judges.parsers import (
    parse_judge_list_from_html,
    parse_judge_edit_contact_html,
    parse_availability_from_edit_html,
    parse_school_from_edit_html,
    parse_add_judge_response,
    parse_edit_form_values,
    parse_edit_judge_response,
    parse_judge_types_from_html,
)

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[\w\.\+\-]+@[\w\.\-]+\.\w+$")


def get_judge_list(client: SpeechWireClient) -> list[dict]:
    """Retrieve judge list with roster details from the dashboard."""

    # Local _parse wrapper filters out records with None judge_id (business logic,
    # not parsing) — this pattern is used when post-processing is needed after
    # HTML parsing. See get_judge_availability for comparison (no wrapper needed).
    def _parse(html: str) -> list[dict]:
        records = parse_judge_list_from_html(html)
        return [r for r in records if r.get("judge_id") is not None]

    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/judges-activecheckin.php",
        _parse,
        default=[],
        context="judge dashboard for list",
    )


def get_judge_contact(judge_id: int, client: SpeechWireClient) -> dict:
    """Fetch judge edit page and return contact information.

    Returns a dict with judge_id, email, phone.
    """

    # Local _parse wrapper injects the judge_id parameter into the result (business
    # logic, not parsing). The parser only extracts email/phone from HTML.
    def _parse(html: str) -> dict:
        parsed = parse_judge_edit_contact_html(html)
        return {
            "judge_id": judge_id,
            "email": parsed.get("email"),
            "phone": parsed.get("phone"),
        }

    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/view-judge.php",
        _parse,
        default={
            "judge_id": judge_id,
            "email": None,
            "phone": None,
        },
        context=f"judge contact for {judge_id}",
        params={"judgeid": str(judge_id)},
    )


def get_judge_availability(judge_id: int, client: SpeechWireClient) -> list[dict]:
    """Fetch and parse a judge's availability from their edit page."""
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/judges-edit.php",
        parse_availability_from_edit_html,
        default=[],
        context=f"availability for {judge_id}",
        params={"judgeid": str(judge_id)},
    )


def get_judge_school(judge_id: int, client: SpeechWireClient) -> dict:
    """Fetch judge edit page and return school association.

    Returns a dict with judge_id, school, and team_id.
    """

    def _parse(html: str) -> dict:
        parsed = parse_school_from_edit_html(html)
        return {
            "judge_id": judge_id,
            "school": parsed.get("school"),
            "team_id": parsed.get("team_id"),
        }

    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/judges-edit.php",
        _parse,
        default={
            "judge_id": judge_id,
            "school": None,
            "team_id": None,
        },
        context=f"school for {judge_id}",
        params={"judgeid": str(judge_id)},
    )


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
) -> dict:
    """Add a new judge to the active tournament.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with a tournament selected.
    judge_name : str
        Judge's full name (required).
    judge_email : str
        Email address (optional).
    team_id : int
        Team/school ID (required). Get valid IDs from speechwire_list_teams.
    judge_type_id : int
        Judge type code. Values are tournament-specific; check the
        tournament's add-judge page for available options.
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


def get_judge_types(client: SpeechWireClient) -> list[dict]:
    """Fetch and parse the judge types for the active tournament.

    Parameters
    ----------
    client : SpeechWireClient
        Authenticated client with a tournament selected.

    Returns
    -------
    list[dict]
        Each dict has ``judge_type_id`` (int), ``judge_type`` (str),
        and ``groupings`` (list[str]).
    """
    return _fetch_and_parse(
        client,
        "https://manage.speechwire.com/tabroom/judgetypes-list.php",
        parse_judge_types_from_html,
        default=[],
        context="judge types list",
    )


_EDIT_JUDGE_URL = "https://manage.speechwire.com/tabroom/judges-edit.php"


def _prefetch_edit_form(judge_id: int, client: SpeechWireClient) -> dict | None:
    """Prefetch the judge edit form and return current field values.

    Parameters
    ----------
    judge_id : int
        The judge to fetch.
    client : SpeechWireClient
        Authenticated client.

    Returns
    -------
    dict | None
        Parsed form values, or ``None`` on failure.
    """
    result = _fetch_and_parse(
        client,
        _EDIT_JUDGE_URL,
        parse_edit_form_values,
        default=None,
        context=f"edit form prefetch for judge {judge_id}",
        params={"judgeid": str(judge_id)},
    )
    return result


def _build_edit_form_data(
    judge_id: int,
    current: dict,
    available_slots: list[int],
) -> dict[str, str]:
    """Build the complete form payload for a judge edit POST.

    Parameters
    ----------
    judge_id : int
        The judge being edited.
    current : dict
        Current form values from ``parse_edit_form_values``.  Must include
        ``fields`` (all serialised form controls) and optionally
        ``hidden_fields`` (legacy key, merged for backward compatibility).
    available_slots : list[int]
        Slot indices to mark as available (checked).

    Returns
    -------
    dict[str, str]
        Form data ready for POST.
    """
    # Start with all serialised form fields (text, select, hidden inputs).
    form_data: dict[str, str] = dict(current.get("fields") or {})

    # Merge legacy hidden_fields key if present (earlier security fix).
    form_data.update(current.get("hidden_fields") or {})

    # Slot checkboxes
    for slot in available_slots:
        form_data[f"slotunblock[{slot}]"] = "1"

    # Explicit overrides — these must win regardless of serialised values.
    form_data["mode"] = "editjudge"
    form_data["judgeid"] = str(judge_id)
    form_data["Submit"] = "Save changes"

    return form_data


def update_judge_email(judge_id: int, email: str, client: SpeechWireClient) -> dict:
    """Update a judge's email address via the edit form.

    Uses a prefetch→merge→POST pattern because the SpeechWire edit form
    submits all fields together.

    Parameters
    ----------
    judge_id : int
        ID of the judge to update.
    email : str
        New email address.
    client : SpeechWireClient
        Authenticated client with a tournament selected.

    Returns
    -------
    dict
        ``{"success": bool, "judge_id": int | None, "error": str | None}``
    """
    _default: dict = {"success": False, "judge_id": None, "error": "unexpected error"}

    if not email or not email.strip():
        return {"success": False, "judge_id": None, "error": "email is required"}

    email = email.strip()
    if not _EMAIL_RE.match(email):
        return {"success": False, "judge_id": None, "error": "invalid email format"}

    current = _prefetch_edit_form(judge_id, client)
    if current is None:
        return {"success": False, "judge_id": None, "error": "failed to prefetch edit form"}

    form_data = _build_edit_form_data(judge_id, current, current["available_slots"])
    form_data["judgeemail"] = email.strip()

    return _post_and_parse(
        client,
        _EDIT_JUDGE_URL,
        form_data,
        parse_edit_judge_response,
        default=_default,
        context=f"update email for judge {judge_id}",
    )


def update_judge_availability(
    judge_id: int,
    available_slots: list[int],
    client: SpeechWireClient,
) -> dict:
    """Update a judge's availability slots via the edit form.

    Uses a prefetch→merge→POST pattern because the SpeechWire edit form
    submits all fields together.

    Parameters
    ----------
    judge_id : int
        ID of the judge to update.
    available_slots : list[int]
        Slot indices the judge should be available for. Replaces any
        previously checked slots.
    client : SpeechWireClient
        Authenticated client with a tournament selected.

    Returns
    -------
    dict
        ``{"success": bool, "judge_id": int | None, "error": str | None}``
    """
    _default: dict = {"success": False, "judge_id": None, "error": "unexpected error"}

    current = _prefetch_edit_form(judge_id, client)
    if current is None:
        return {"success": False, "judge_id": None, "error": "failed to prefetch edit form"}

    form_data = _build_edit_form_data(judge_id, current, available_slots)

    return _post_and_parse(
        client,
        _EDIT_JUDGE_URL,
        form_data,
        parse_edit_judge_response,
        default=_default,
        context=f"update availability for judge {judge_id}",
    )
