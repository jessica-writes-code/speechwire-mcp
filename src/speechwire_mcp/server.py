"""SpeechWire MCP server — exposes SpeechWire tournament data as MCP tools.

Supports stdio and SSE transports. Configure via environment variables:

    SPEECHWIRE_EMAIL          (required)
    SPEECHWIRE_PASSWORD       (required)
    SPEECHWIRE_ACCOUNT_ID     (optional — discovered after login)
    SPEECHWIRE_CIRCUIT_ID     (optional — discovered after login)
    SPEECHWIRE_TOURNAMENT_ID  (optional — discovered after login)
"""

import logging
import os
from collections.abc import Callable
from typing import TypeVar

from mcp.server.fastmcp import FastMCP

try:
    from importlib.metadata import version as _get_version

    _server_version = _get_version("speechwire-mcp")
except Exception:  # noqa: BLE001
    _server_version = "0.1.2"

from speechwire_mcp.client import (
    ClientState,
    SpeechWireClient,
)
from speechwire_mcp.judges import (
    add_judge,
    get_judge_availability,
    get_judge_contact,
    get_judge_list,
    get_judge_school,
    get_judge_types,
    update_judge_availability,
    update_judge_email,
    update_judge_school,
)
from speechwire_mcp.login import get_accounts, get_tournaments
from speechwire_mcp.results import get_tab_sheet
from speechwire_mcp.rooms import get_room_counts, get_room_list, get_room_usage
from speechwire_mcp.schematics import (
    get_round_schematic,
    get_schematic_events,
)
from speechwire_mcp.structure import get_groupings, get_timeslots
from speechwire_mcp.teams import get_hybrid_entries, get_team_entries, get_team_list

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "SpeechWire MCP Server",
    instructions="Access SpeechWire tournament judge data via the Model Context Protocol",
)
mcp._mcp_server.version = _server_version

_client: SpeechWireClient | None = None

T = TypeVar("T")


def _get_client() -> SpeechWireClient:
    """Lazily initialize the SpeechWire client from environment variables.

    Only email and password are required.  Account, circuit, and tournament
    IDs are passed through when present but are no longer mandatory — they
    can be discovered after login via the discovery tools.
    """
    global _client
    if _client is None:
        required = ["SPEECHWIRE_EMAIL", "SPEECHWIRE_PASSWORD"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        _client = SpeechWireClient(
            email=os.environ["SPEECHWIRE_EMAIL"],
            password=os.environ["SPEECHWIRE_PASSWORD"],
            account_id=os.environ.get("SPEECHWIRE_ACCOUNT_ID"),
            circuit_id=os.environ.get("SPEECHWIRE_CIRCUIT_ID"),
            tournament_id=os.environ.get("SPEECHWIRE_TOURNAMENT_ID"),
        )
    return _client


def _require_tournament(client: SpeechWireClient) -> dict | None:
    """Return an error dict if the client has not reached TOURNAMENT_ACTIVE.

    When all three IDs (account, circuit, tournament) were provided via
    environment variables the client will still be UNAUTHENTICATED at first
    call.  In that case we automatically run the full auth flow so that
    existing env-var users are not broken by the new state machine.

    Returns ``None`` when the guard passes and the caller may proceed.
    """
    if client.state == ClientState.TOURNAMENT_ACTIVE:
        return None

    # Backward-compat: auto-authenticate when the user supplied all IDs.
    if client.account_id and client.circuit_id and client.tournament_id:
        try:
            client.ensure_tournament_session()
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Auto-authentication with provided IDs failed: %s", type(exc).__name__
            )
        if client.state == ClientState.TOURNAMENT_ACTIVE:
            return None

    return {
        "error": "no_tournament_selected",
        "message": (
            "No tournament is active. Follow this sequence: "
            "1) speechwire_list_user_accounts → 2) speechwire_select_user_account → "
            "3) speechwire_list_user_tournaments → 4) speechwire_select_user_tournament."
        ),
        "available_tools": [
            "speechwire_list_user_accounts",
            "speechwire_select_user_account",
            "speechwire_list_user_tournaments",
            "speechwire_select_user_tournament",
        ],
    }


def _safe_tool_call(
    func: Callable[[], T],
    error_msg: str,
    default: T,
    ensure_login: bool = False,
    require_tournament: bool = False,
) -> T:
    """Execute an MCP tool function with standard error handling patterns.

    Parameters
    ----------
    func : Callable[[], T]
        The data-fetching function to execute (should accept no args).
    error_msg : str
        Log message prefix for exceptions.
    default : T
        Value to return on error (typically [] or {}).
    ensure_login : bool
        If True, ensure client is logged in before calling func.
    require_tournament : bool
        If True, check tournament guard before calling func.

    Returns
    -------
    T
        Result from func(), or default on error, or guard dict if tournament check fails.
    """
    try:
        client = _get_client()
        if ensure_login and client.state == ClientState.UNAUTHENTICATED:
            client.login()

        if require_tournament:
            guard = _require_tournament(client)
            if guard:
                # Wrap guard dict in list for list-returning tools
                if isinstance(default, list):
                    return [guard]  # type: ignore[return-value]
                return guard  # type: ignore[return-value]

        return func()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s: %s", error_msg, type(exc).__name__)
        return default


# ---------------------------------------------------------------------------
# Login Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def speechwire_list_user_accounts() -> list[dict]:
    """List SpeechWire accounts available to the authenticated user.

    Call speechwire_select_user_account to choose one.

    Returns
    -------
    list[dict]
        Account records containing ``account_id`` (int) and ``name`` (str).
    """
    return _safe_tool_call(
        lambda: get_accounts(_get_client()),
        "Failed to list accounts",
        default=[],
        ensure_login=True,
    )


@mcp.tool()
def speechwire_select_user_account(account_id: int) -> dict:
    """Select a SpeechWire account to work with.

    Parameters
    ----------
    account_id : int
        Account ID from speechwire_list_user_accounts.

    Returns
    -------
    dict
        Status record containing ``status`` (str) and ``account_id`` (int).
    """

    def _select() -> dict:
        client = _get_client()
        client.select_account(account_id)
        return {"status": "ok", "account_id": account_id}

    return _safe_tool_call(
        _select,
        f"Failed to select account {account_id}",
        default={"error": "account_selection_failed", "account_id": account_id},
        ensure_login=True,
    )


@mcp.tool()
def speechwire_list_user_tournaments() -> list[dict]:
    """List all tournaments (current and past seasons) for the selected account.

    Call speechwire_select_user_tournament to choose one.

    Returns
    -------
    list[dict]
        Tournament records containing ``tournament_id`` (int), ``circuit_id``
        (int | None), ``name`` (str), ``date`` (str | None), and ``season``
        (str: ``"current"`` or ``"past"``).
    """
    return _safe_tool_call(
        lambda: get_tournaments(_get_client()),
        "Failed to list tournaments",
        default=[],
        ensure_login=True,
    )


@mcp.tool()
def speechwire_select_user_tournament(tournament_id: int, circuit_id: int) -> dict:
    """Select a tournament to work with.

    After calling this, tournament-specific tools become available.

    Parameters
    ----------
    tournament_id : int
        Tournament ID from speechwire_list_user_tournaments.
    circuit_id : int
        Circuit ID from speechwire_list_user_tournaments.

    Returns
    -------
    dict
        Status record containing ``status`` (str), ``tournament_id`` (int), and
        ``circuit_id`` (int).
    """

    def _select() -> dict:
        client = _get_client()
        client.select_tournament(tournament_id, circuit_id)
        return {
            "status": "ok",
            "tournament_id": tournament_id,
            "circuit_id": circuit_id,
        }

    return _safe_tool_call(
        _select,
        f"Failed to select tournament {tournament_id}/{circuit_id}",
        default={"error": "tournament_selection_failed"},
        ensure_login=True,
    )


# ---------------------------------------------------------------------------
# Judge Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def speechwire_list_judges() -> list[dict]:
    """List all judges registered for the tournament with roster details.

    Returns
    -------
    list[dict]
        Judge records containing:
        - judge_id: int — numeric judge identifier
        - name: str — judge's full name
        - team: str | None — school or team name
        - team_id: int | None — numeric team identifier
        - is_coach: bool — whether the judge is marked as a coach
        - is_active: bool — whether the judge is active
        - is_clean: bool — whether the judge is marked clean
        - is_priority: bool — whether the judge is marked priority
        - email: str | None — judge's email address (if present on the roster page)
        - unavailability: str | None — unavailability summary text
        - blocks: list[str] — event/team blocks (e.g. "GROUPING: Varsity Policy Debate")
    """
    return _safe_tool_call(
        lambda: get_judge_list(_get_client()),
        "Failed to list judges",
        default=[],
        require_tournament=True,
    )


@mcp.tool()
def speechwire_get_judge_contact(judge_id: int) -> dict:
    """Get a judge's email and phone contact information.

    Parameters
    ----------
    judge_id : int
        Numeric judge identifier from speechwire_list_judges.

    Returns
    -------
    dict
        Contact record containing ``judge_id`` (int), ``email`` (str | None), and
        ``phone`` (str | None).
    """
    return _safe_tool_call(
        lambda: get_judge_contact(judge_id, _get_client()),
        f"Failed to get contact for judge {judge_id}",
        default={"error": "contact_fetch_failed", "judge_id": judge_id},
        require_tournament=True,
    )


@mcp.tool()
def speechwire_get_judge_availability(judge_id: int) -> list[dict]:
    """Get a judge's availability by timeslot.

    Parameters
    ----------
    judge_id : int
        Numeric judge identifier from speechwire_list_judges.

    Returns
    -------
    list[dict]
        Timeslot records containing:
        - slot_index: int — internal slot identifier
        - label: str — human-readable time slot description
        - available: bool — whether the judge is available
    """
    return _safe_tool_call(
        lambda: get_judge_availability(judge_id, _get_client()),
        f"Failed to get availability for judge {judge_id}",
        default=[],
        require_tournament=True,
    )


@mcp.tool()
def speechwire_get_judge_school(judge_id: int) -> dict:
    """Get the school (team) a judge is associated with.

    Parameters
    ----------
    judge_id : int
        Numeric judge identifier from speechwire_list_judges.

    Returns
    -------
    dict
        School record containing ``judge_id`` (int), ``school`` (str | None), and
        ``team_id`` (int | None).
    """
    return _safe_tool_call(
        lambda: get_judge_school(judge_id, _get_client()),
        f"Failed to get school for judge {judge_id}",
        default={"error": "school_fetch_failed", "judge_id": judge_id},
        require_tournament=True,
    )


@mcp.tool()
def speechwire_add_judge(
    judge_name: str,
    team_id: int,
    judge_email: str = "",
    judge_type_id: int = 0,
    is_clean: bool = False,
    is_coach: bool = False,
    is_priority: bool = False,
    available_slots: list[int] | None = None,
) -> dict:
    """Add a new judge to the tournament.

    Parameters
    ----------
    judge_name : str
        Judge's full name (required).
    team_id : int
        Team/school ID (required). Get valid IDs from speechwire_list_teams.
    judge_email : str
        Email address (optional).
    judge_type_id : int
        Tournament-specific judge type ID from speechwire_list_judge_types.
        Use 0 when no configured judge type is selected.
    is_clean : bool
        Whether the judge is a clean/neutral judge.
    is_coach : bool
        Whether the judge is a coach.
    is_priority : bool
        Whether the judge is a priority judge.
    available_slots : list[int] | None
        Provider slot_id values from speechwire_list_timeslots for which the
        judge is available.
        If omitted, the judge is blocked for all slots.

    Returns
    -------
    dict
        ``{"success": bool, "judge_id": int | None, "error": str | None}``
    """
    return _safe_tool_call(
        lambda: add_judge(
            _get_client(),
            judge_name=judge_name,
            judge_email=judge_email,
            team_id=team_id,
            judge_type_id=judge_type_id,
            is_clean=is_clean,
            is_coach=is_coach,
            is_priority=is_priority,
            available_slots=available_slots,
        ),
        "Failed to add judge",
        default={"success": False, "judge_id": None, "error": "unexpected error"},
        require_tournament=True,
    )


@mcp.tool()
def speechwire_update_judge_email(judge_id: int, email: str) -> dict:
    """Update a judge's email address.

    Replaces the email while preserving the judge's other values.

    Parameters
    ----------
    judge_id : int
        ID of the judge to update.
    email : str
        New email address for the judge.

    Returns
    -------
    dict
        ``{"success": bool, "judge_id": int | None, "error": str | None}``
    """
    return _safe_tool_call(
        lambda: update_judge_email(judge_id, email, _get_client()),
        f"Failed to update email for judge {judge_id}",
        default={"success": False, "judge_id": None, "error": "unexpected error"},
        require_tournament=True,
    )


@mcp.tool()
def speechwire_update_judge_availability(
    judge_id: int, available_slots: list[int]
) -> dict:
    """Replace a judge's availability slots while preserving other values.

    Parameters
    ----------
    judge_id : int
        ID of the judge to update.
    available_slots : list[int]
        Provider slot_id values from speechwire_list_timeslots for which the
        judge should be available. Replaces all current availability.

    Returns
    -------
    dict
        ``{"success": bool, "judge_id": int | None, "error": str | None}``
    """
    return _safe_tool_call(
        lambda: update_judge_availability(judge_id, available_slots, _get_client()),
        f"Failed to update availability for judge {judge_id}",
        default={"success": False, "judge_id": None, "error": "unexpected error"},
        require_tournament=True,
    )


@mcp.tool()
def speechwire_update_judge_school(judge_id: int, team_id: int) -> dict:
    """Update a judge's school (team) affiliation.

    Replaces the team affiliation while preserving the judge's other values.

    Parameters
    ----------
    judge_id : int
        ID of the judge to update.
    team_id : int
        New team/school ID. Get valid IDs from speechwire_list_teams.

    Returns
    -------
    dict
        ``{"success": bool, "judge_id": int | None, "error": str | None}``
    """
    return _safe_tool_call(
        lambda: update_judge_school(judge_id, team_id, _get_client()),
        f"Failed to update school for judge {judge_id}",
        default={"success": False, "judge_id": None, "error": "unexpected error"},
        require_tournament=True,
    )


@mcp.tool()
def speechwire_list_judge_types() -> list[dict]:
    """List judge types configured for the tournament.

    If no judge types are configured for the tournament, returns an empty list.

    Returns
    -------
    list[dict]
        Judge type records containing:
        - judge_type_id: int — identifier to use with speechwire_add_judge
        - judge_type: str — name (e.g., "A", "B", "Speech judge")
        - groupings: list[str] — grouping codes this type can judge
    """
    return _safe_tool_call(
        lambda: get_judge_types(_get_client()),
        "Failed to list judge types",
        default=[],
        require_tournament=True,
    )


# ---------------------------------------------------------------------------
# Room Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def speechwire_list_rooms() -> list[dict]:
    """List all rooms configured for the tournament.

    Returns
    -------
    list[dict]
        Room records containing:
        - room_id: int — numeric room identifier
        - name: str — room display name
        - has_constraints: bool — whether the room has availability constraints
    """
    return _safe_tool_call(
        lambda: get_room_list(_get_client()),
        "Failed to list rooms",
        default=[],
        require_tournament=True,
    )


@mcp.tool()
def speechwire_get_room_usage() -> list[dict]:
    """Get room time-slot usage showing assignments for every room.

    Returns
    -------
    list[dict]
        Room usage records containing:
        - room_id: int — numeric room identifier
        - room_name: str — room display name
        - time_slots: list[dict] — per-slot records with slot_index, time_label,
          status, event_code, and round_number
    """
    return _safe_tool_call(
        lambda: get_room_usage(_get_client()),
        "Failed to get room usage",
        default=[],
        require_tournament=True,
    )


@mcp.tool()
def speechwire_get_room_counts() -> list[dict]:
    """Get room vs. section counts per grouping and round.

    Shows how many rooms are assigned versus how many sections are needed
    for each competition grouping in each round.  Useful for identifying
    rounds that are short on rooms.

    Returns
    -------
    list[dict]
        Grouping records containing:
        - grouping_name: str — competition grouping (e.g., "JV Policy Debate")
        - rounds: list[dict] — per-round room and section counts with a
          ``sufficient`` boolean
    """
    return _safe_tool_call(
        lambda: get_room_counts(_get_client()),
        "Failed to get room counts",
        default=[],
        require_tournament=True,
    )


# ---------------------------------------------------------------------------
# Team Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def speechwire_list_teams() -> list[dict]:
    """List all teams registered for the tournament.

    Returns
    -------
    list[dict]
        Team records containing:
        - team_id: int — numeric team identifier
        - name: str — team/school name
        - code: str | None — team code abbreviation
        - is_invited: bool — whether the team is invited
        - is_attending: bool — whether the team is attending
        - is_checked_in: bool — whether the team is checked in
        - is_udl_member: bool — whether the team is a UDL member
    """
    return _safe_tool_call(
        lambda: get_team_list(_get_client()),
        "Failed to list teams",
        default=[],
        require_tournament=True,
    )


@mcp.tool()
def speechwire_get_team_entries(team_id: int) -> list[dict]:
    """Get entries for a specific team.

    Parameters
    ----------
    team_id : int
        Numeric team identifier from speechwire_list_teams.

    Returns
    -------
    list[dict]
        Entry records containing:
        - event_id: int — numeric event identifier
        - event_name: str | None — event name
        - entry_number: int — entry number within the event
        - entry_code: str | None — entry code
        - competitors: list[dict] — student_id, name, and competitor_number
        - division: str | None — division name
        - division_id: int | None — numeric division identifier
        - is_dropped: bool — whether the entry is dropped
    """
    return _safe_tool_call(
        lambda: get_team_entries(team_id, _get_client()),
        f"Failed to get entries for team {team_id}",
        default=[],
        require_tournament=True,
    )


@mcp.tool()
def speechwire_list_hybrid_entries() -> list[dict]:
    """List all hybrid entries (cross-school team entries) for the tournament.

    Returns
    -------
    list[dict]
        Hybrid entry records containing:
        - comp_id: int — numeric competition entry identifier
        - event: str — event name
        - division: str | None — division name
        - students: list[dict] — student name and school records
        - code: str | None — entry code
        - team_blocks: list[str] — school names for team blocking
    """
    return _safe_tool_call(
        lambda: get_hybrid_entries(_get_client()),
        "Failed to list hybrid entries",
        default=[],
        require_tournament=True,
    )


# ---------------------------------------------------------------------------
# Structure Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def speechwire_list_timeslots() -> list[dict]:
    """List the tournament schedule timeslots.

    Returns
    -------
    list[dict]
        Timeslot records containing:
        - slot_id: int — numeric timeslot identifier
        - time: str — human-readable time (e.g., "9:00 AM")
        - description: str | None — slot description
        - date: str | None — date for this slot
        - round_assignments: list[dict] — event_name and round_label records
    """
    return _safe_tool_call(
        lambda: get_timeslots(_get_client()),
        "Failed to list timeslots",
        default=[],
        require_tournament=True,
    )


@mcp.tool()
def speechwire_list_groupings() -> list[dict]:
    """List competition groupings configured for the tournament.

    Returns
    -------
    list[dict]
        Grouping records containing:
        - grouping_id: int — numeric grouping identifier
        - name: str — full grouping name
        - abbreviation: str — short code
        - event: str — event name
        - divisions: str — division text
    """
    return _safe_tool_call(
        lambda: get_groupings(_get_client()),
        "Failed to list groupings",
        default=[],
        require_tournament=True,
    )


# ---------------------------------------------------------------------------
# Schematic / Pairing Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def speechwire_list_schematic_events() -> list[dict]:
    """List all schematic events (debate/speech groupings) with available rounds.

    Returns
    -------
    list[dict]
        Event records containing:
        - grouping_id: int — numeric event identifier
        - name: str — event name
        - rounds: list[int] — available round numbers
    """
    return _safe_tool_call(
        lambda: get_schematic_events(_get_client()),
        "Failed to list schematic events",
        default=[],
        require_tournament=True,
    )


@mcp.tool()
def speechwire_get_round_schematic(grouping_id: int, round_number: int) -> dict | list:
    """Get the full schematic (pairings/sections) for a specific event round.

    Parameters
    ----------
    grouping_id : int
        Event grouping identifier from speechwire_list_schematic_events.
    round_number : int
        Round number for this event.

    Returns
    -------
    dict | list
        Schematic containing:
        - event_name: str — event name
        - round: int — round number
        - time: str | None — scheduled time
        - unused_judges: list[dict] — unassigned judges
        - sections: list[dict] — sections with judges, rooms, and competitors
    """
    return _safe_tool_call(
        lambda: get_round_schematic(grouping_id, round_number, _get_client()),
        f"Failed to get schematic for grouping {grouping_id} round {round_number}",
        default={},
        require_tournament=True,
    )


# ---------------------------------------------------------------------------
# Results / Tab Sheet Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def speechwire_get_tab_sheet(grouping_id: int) -> dict | list:
    """Get the results tab sheet for a competition grouping.

    Includes round-by-round outcomes (W/L/BYE/FORFEIT), per-speaker scores,
    win-loss records, total points, and final placements.

    Parameters
    ----------
    grouping_id : int
        Grouping identifier from speechwire_list_groupings.

    Returns
    -------
    dict | list
        Tab sheet containing:
        - grouping_name: str — grouping name
        - round_names: list[str] — round column headers
        - competitors: list[dict] — team results, records, points, placements,
          and speaker results
    """
    return _safe_tool_call(
        lambda: get_tab_sheet(grouping_id, _get_client()),
        f"Failed to get tab sheet for grouping {grouping_id}",
        default={},
        require_tournament=True,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Run the SpeechWire MCP server."""
    transport = os.environ.get("SPEECHWIRE_MCP_TRANSPORT", "stdio").lower()

    if transport == "sse":
        host = os.environ.get("SPEECHWIRE_MCP_HOST", "127.0.0.1")
        port = int(os.environ.get("SPEECHWIRE_MCP_PORT", "8080"))
        logger.info("Starting SpeechWire MCP server (SSE) on %s:%d", host, port)
        mcp.run(transport="sse", host=host, port=port)
    else:
        logger.info("Starting SpeechWire MCP server (stdio)")
        mcp.run(transport="stdio")
