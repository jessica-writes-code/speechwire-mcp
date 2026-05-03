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

## License

[MIT](LICENSE)
