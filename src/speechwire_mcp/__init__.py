"""speechwire-mcp: Model Context Protocol server for SpeechWire tournament management."""

from speechwire_mcp.client import SpeechWireClient, SpeechWireAuthError
from speechwire_mcp.judges import (
    get_judge_list,
    get_judge_contact,
    get_judge_availability,
    get_judge_school,
)
from speechwire_mcp.login import get_accounts, get_tournaments
from speechwire_mcp.rooms import get_room_counts, get_room_list, get_room_usage
from speechwire_mcp.schematics import get_schematic_events, get_round_schematic
from speechwire_mcp.structure import get_groupings, get_timeslots
from speechwire_mcp.teams import get_team_list, get_team_entries, get_hybrid_entries

__all__ = [
    "SpeechWireClient",
    "SpeechWireAuthError",
    "get_judge_list",
    "get_judge_contact",
    "get_judge_availability",
    "get_judge_school",
    "get_accounts",
    "get_tournaments",
    "get_room_counts",
    "get_room_list",
    "get_room_usage",
    "get_schematic_events",
    "get_round_schematic",
    "get_groupings",
    "get_timeslots",
    "get_team_list",
    "get_team_entries",
    "get_hybrid_entries",
]
