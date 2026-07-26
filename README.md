# SpeechWire MCP Server

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.11%2B-blue)](#) [![PyPI](https://img.shields.io/pypi/v/speechwire-mcp)](#)

A [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that provides AI assistants with secure, authenticated access to [SpeechWire](https://www.speechwire.com/) tournament data for speech-and-debate (forensics) competitions.

The server scrapes manage.speechwire.com behind an authenticated session and exposes structured tournament data through MCP tools, enabling AI assistants to help tournament directors manage judge assignments, rooms, teams, entries, and round pairings.

## Features

- **Judge management** — list judges, contact info, availability, school associations, judge types, and add new judges
- **Team & entry data** — team rosters, entries by team, hybrid/cross-school entries
- **Room management** — room lists, usage grids, room-vs-section counts
- **Schematics** — event lists, round-by-round pairings with judges, rooms, and competitors
- **Tournament structure** — timeslots, competition groupings
- **Results** — tab sheets with round outcomes, speaker scores, and placements
- **Account discovery** — list and select accounts and tournaments interactively
- **Session management** — automatic re-authentication on session expiry

## Installation

```bash
pip install speechwire-mcp
```

Set your SpeechWire credentials as environment variables:

```bash
export SPEECHWIRE_EMAIL="your-email@example.com"
export SPEECHWIRE_PASSWORD="your-password"
```

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `speechwire_list_user_accounts` | List accounts available after login |
| `speechwire_select_user_account` | Select an account to work with |
| `speechwire_list_user_tournaments` | List tournaments for the selected account |
| `speechwire_select_user_tournament` | Select a tournament to activate |
| `speechwire_list_judges` | List all judges with roster details |
| `speechwire_get_judge_contact` | Get judge email and phone |
| `speechwire_get_judge_availability` | Get judge availability by timeslot |
| `speechwire_get_judge_school` | Get judge's school association |
| `speechwire_add_judge` | Add a new judge to the tournament |
| `speechwire_update_judge_email` | Update a judge's email address |
| `speechwire_update_judge_availability` | Update a judge's availability slots |
| `speechwire_update_judge_school` | Update a judge's school/team affiliation |
| `speechwire_list_judge_types` | List configured judge types |
| `speechwire_list_rooms` | List tournament rooms |
| `speechwire_get_room_usage` | Get room time-slot usage grid |
| `speechwire_get_room_counts` | Get rooms vs. sections per grouping/round |
| `speechwire_list_teams` | List registered teams |
| `speechwire_get_team_entries` | Get entries for a specific team |
| `speechwire_list_hybrid_entries` | List cross-school hybrid entries |
| `speechwire_list_timeslots` | List tournament schedule timeslots |
| `speechwire_list_groupings` | List competition groupings |
| `speechwire_list_schematic_events` | List schematic events with available rounds |
| `speechwire_get_round_schematic` | Get pairings for a specific event round |
| `speechwire_get_tab_sheet` | Get results tab sheet for a grouping |

## Documenting MCP Tools

An MCP tool docstring is a model-facing API contract. FastMCP publishes the
docstring as the tool description and generates the input schema from the Python
signature. An agent must be able to choose and call the tool correctly from
those two values without reading the implementation.

Use NumPy-style sections for every `@mcp.tool()` function:

```python
@mcp.tool()
def speechwire_get_example(record_id: int, include_details: bool = False) -> dict:
    """Get one example record from the active tournament.

    Parameters
    ----------
    record_id : int
        Required record ID from speechwire_list_examples.
    include_details : bool
        Whether to include nested detail records. Defaults to False.

    Returns
    -------
    dict
        Record containing ``record_id`` (int), ``name`` (str), and ``details``
        (list[dict]).
    """
```

Follow these rules:

- Start with one sentence that distinguishes the tool from neighboring tools.
- Add operational guidance before `Parameters`, including prerequisites or the
  tool that supplies an identifier.
- Give every input an exact `name : type` entry. State whether it is required,
  its default, valid values or source tool, units or indexing, and the meaning
  of `None`, an empty string, or an empty list when relevant.
- Add `Returns` to every tool, including tools with no parameters. State the
  top-level type and document fields an agent must interpret or reuse.
- For mutations, describe the side effect and whether collections replace,
  merge with, or append to existing values. Document meaningful failure and
  retry behavior.
- Keep implementation mechanics out of model-facing prose unless they change
  how the caller must use the tool.
- Keep the signature, required fields, defaults, docstring, and returned field
  names in agreement. Use exact MCP tool names in cross-references.

`tests/test_server_tool_contracts.py` enforces the common section structure and
typed parameter entries against FastMCP's registered tool descriptions. Add
focused assertions there when a tool has important identifier-source, default,
or mutation semantics that the generic contract cannot verify.

## License

[MIT](LICENSE)
