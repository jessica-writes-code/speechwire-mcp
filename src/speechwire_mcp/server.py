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
from typing import Callable, TypeVar

from mcp.server.fastmcp import FastMCP

try:
    from importlib.metadata import version as _get_version

    _server_version = _get_version("speechwire-mcp")
except Exception:
    _server_version = "0.1.0"

from speechwire_mcp.client import (
    ClientState,
    SpeechWireClient,
)
from speechwire_mcp.judges import (
    get_judge_list,
    get_judge_contact,
    get_judge_availability,
    get_judge_school,
    add_judge,
    get_judge_types,
)
from speechwire_mcp.schematics import (
    get_schematic_events,
    get_round_schematic,
)
from speechwire_mcp.login import get_accounts, get_tournaments
from speechwire_mcp.rooms import get_room_list, get_room_usage, get_room_counts
from speechwire_mcp.teams import get_team_list, get_team_entries, get_hybrid_entries
from speechwire_mcp.structure import get_groupings, get_timeslots
from speechwire_mcp.results import get_tab_sheet

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
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
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
        except Exception:
            logger.exception("Auto-authentication with provided IDs failed")
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
    except Exception:
        logger.exception(error_msg)
        return default


# ---------------------------------------------------------------------------
# Login Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def speechwire_list_user_accounts() -> list[dict]:
    """List SpeechWire accounts available to the authenticated user.

    Returns a list of records with: account_id (int), name (str).
    Call speechwire_select_user_account to choose one.
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

    Returns a status dict confirming the selection.
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

    Returns a list with: tournament_id (int), circuit_id (int | None),
    name (str), date (str | None), season (str: "current" or "past").
    Call speechwire_select_user_tournament to choose one.
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

    Parameters
    ----------
    tournament_id : int
        Tournament ID from speechwire_list_user_tournaments.
    circuit_id : int
        Circuit ID from speechwire_list_user_tournaments.

    After calling this, tournament-specific tools become available.
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

    Returns a list of records, each containing:
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

    Returns a dict with judge_id, email, and phone fields.
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

    Returns a list of timeslot records, each containing:
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

    Returns a dict with judge_id, school name, and team_id.
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
    judge_email: str = "",
    team_id: int = 0,
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
    judge_email : str
        Email address (optional).
    team_id : int
        Team/school ID (required). Get valid IDs from speechwire_list_teams.
    judge_type_id : int
        Judge type code. Values are tournament-specific; check the
        tournament's add-judge page for available options.
    is_clean : bool
        Whether the judge is a clean/neutral judge.
    is_coach : bool
        Whether the judge is a coach.
    is_priority : bool
        Whether the judge is a priority judge.
    available_slots : list[int] | None
        List of 1-indexed time slot numbers the judge is available for.
        If omitted, the judge is blocked for all slots.
        Get valid slot numbers from speechwire_list_timeslots.
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
def speechwire_list_judge_types() -> list[dict]:
    """List judge types configured for the tournament.

    Returns a list of records, each containing:
    - judge_type_id: int — numeric judge type identifier (use with speechwire_add_judge)
    - judge_type: str — judge type name (e.g., "A", "B", "Speech judge")
    - groupings: list[str] — grouping codes this type can judge
                 (e.g., ["J-CX", "NRP-CX", "RO-CX"])

    If no judge types are configured for the tournament, returns an empty list.
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

    Returns a list of records, each containing:
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

    Returns a list of records, each containing:
    - room_id: int — numeric room identifier
    - room_name: str — room display name
    - time_slots: list[dict] — per-slot records with:
        - slot_index: int — zero-based slot position
        - time_label: str — human-readable time label
        - status: str — one of "available", "timeblock", "unavailable", "assigned"
        - event_code: str | None — event code (only when status is "assigned")
        - round_number: int | None — round number (only when status is "assigned")
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

    Returns a list of records, each containing:
    - grouping_name: str — competition grouping (e.g., "JV Policy Debate")
    - rounds: list[dict] — per-round records with:
        - round_number: int — 1-based round number
        - rooms: int — number of rooms assigned
        - sections: int — number of sections needed
        - sufficient: bool — True when rooms >= sections
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

    Returns a list of records, each containing:
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

    Returns a list of entry records, each containing:
    - event_id: int — numeric event identifier
    - event_name: str | None — event name (e.g., "Policy Debate (Varsity/JV/...)")
    - entry_number: int — entry number within the event
    - entry_code: str | None — entry code (e.g., "Potomac Aca AB")
    - competitors: list[dict] — each with student_id (int), name (str),
      competitor_number (int)
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

    Returns a list of hybrid entry records, each containing:
    - comp_id: int — numeric competition entry identifier
    - event: str — event name (e.g., "Policy Debate")
    - division: str | None — division name (e.g., "JV", "Varsity")
    - students: list[dict] — each with name (str) and school (str | None).
    - code: str | None — entry code (e.g., "Hybrid Entries LyCr")
    - team_blocks: list[str] — list of school names for team blocking
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

    Returns a list of records, each containing:
    - slot_id: int — numeric timeslot identifier
    - time: str — human-readable time (e.g., "9:00 AM")
    - description: str | None — slot description (e.g., "Round 1")
    - date: str | None — date for this slot (e.g., "Mar. 21, 2026")
    - round_assignments: list[dict] — per-event assignments, each with:
        - event_name: str — event column name (e.g., "EVT-A", "EVT-B")
        - round_label: str | None — assigned round text (e.g., "Rd. 1") or None
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

    Returns a list of records, each containing:
    - grouping_id: int — numeric grouping identifier
    - name: str — full grouping name (e.g., "Varsity Lincoln-Douglas")
    - abbreviation: str — short code (e.g., "EVT-A")
    - event: str — event name (e.g., "Policy Debate")
    - divisions: str — division text (e.g., "Open")
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

    Returns a list of records, each containing:
    - grouping_id: int — numeric event identifier
    - name: str — event name (e.g., "Varsity Policy Debate")
    - rounds: list[int] — list of available round numbers for this event
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

    Returns a dict containing:
    - event_name: str — event name
    - round: int — round number
    - time: str | None — scheduled time for this round
    - unused_judges: list[dict] — judges not yet assigned to sections
    - sections: list[dict] — list of debate sections/rooms with assigned judges,
      rooms, and competitors
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

    Returns round-by-round outcomes (W/L/BYE/FORFEIT), per-speaker scores,
    win-loss records, total points, and final placements.

    Parameters
    ----------
    grouping_id : int
        Grouping identifier from speechwire_list_groupings.

    Returns a dict containing:
    - grouping_name: str — name of the grouping
    - round_names: list[str] — round column headers (e.g., "Round 1")
    - competitors: list[dict] — one per team, each with:
        - comp_id: int — competitor identifier
        - name: str — team display name
        - rounds: list[dict] — per-round results with result, opponent, side,
          judge, judge_number
        - record: str — e.g. "3-0"
        - total_points: float | None — combined speaker points
        - placement: str — e.g. "2nd"
        - speakers: list[dict] — individual speakers with name, round_scores,
          total_points, and placement
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
        host = os.environ.get("SPEECHWIRE_MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("SPEECHWIRE_MCP_PORT", "8080"))
        logger.info("Starting SpeechWire MCP server (SSE) on %s:%d", host, port)
        mcp.run(transport="sse", host=host, port=port)
    else:
        logger.info("Starting SpeechWire MCP server (stdio)")
        mcp.run(transport="stdio")
