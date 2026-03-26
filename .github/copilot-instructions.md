# Copilot Instructions for SpeechWireMCP

## Project Overview

SpeechWireMCP is a Model Context Protocol (MCP) server that gives AI assistants
secure access to SpeechWire tournament judge data for speech-and-debate
(forensics) competitions. It scrapes manage.speechwire.com behind an
authenticated session and exposes structured data through MCP tools.

## Tech Stack

- **Python 3.11+** — use modern syntax (`X | Y` unions, `list[dict]`, etc.)
- **MCP SDK** (`mcp` package, `FastMCP`) — tool registration via `@mcp.tool()`
- **requests** — HTTP client with a stateful `requests.Session` for auth cookies
- **BeautifulSoup4** — HTML parsing of SpeechWire pages
- **Hatchling** — PEP 517 build backend
- **pytest** — testing
- **ruff** — linting (line-length 100, target py311)

## Architecture

```
src/speechwire_mcp/
├── server.py        # FastMCP server, tool definitions, lazy client init
├── client.py        # SpeechWireClient (4-step auth), _fetch_and_parse helper
└── judges/
    ├── client.py    # Judge data retrieval (list, contact, availability)
    └── parsers.py   # HTML → structured data parsing
```

- **server.py** is the MCP entry point. Tools are thin wrappers that delegate to
  `judges/` functions.
- **client.py** owns all HTTP and authentication logic. The client automatically
  re-authenticates when it detects a session expiry.
- **judges/parsers.py** contains pure functions that take HTML strings and return
  dicts/lists — keep them side-effect free for easy testing.
- **`_fetch_and_parse`** is the shared pattern: fetch a page, run a parser,
  return a safe default on any failure.

## Conventions

- **Error handling:** never raise from MCP tools. Log errors and return sensible
  defaults (empty list, `None`, etc.) so the AI client always gets a valid
  response.
- **Logging:** use `logging.getLogger(__name__)` in every module.
- **Privacy:** contact info (email, phone) should be treated carefully.
  Hash or redact PII when appropriate.
- **Type hints:** annotate all public functions. Use built-in generics
  (`list`, `dict`, `str | None`) — no `typing.List`/`typing.Optional`.
- **Docstrings:** use NumPy-style docstrings (`Parameters`, `Returns` sections).
- **Line length:** 100 characters max (enforced by ruff).
- **Tests:** parser functions get unit tests in `tests/` with sample HTML
  fixtures. Use `pytest`.

## Environment Variables

The server requires these at runtime (never hard-code credentials):

| Variable | Purpose |
|----------|---------|
| `SPEECHWIRE_EMAIL` | Account email |
| `SPEECHWIRE_PASSWORD` | Account password |
| `SPEECHWIRE_ACCOUNT_ID` | Numeric account ID |
| `SPEECHWIRE_CIRCUIT_ID` | Numeric circuit ID |
| `SPEECHWIRE_TOURNAMENT_ID` | Numeric tournament ID |
| `SPEECHWIRE_MCP_TRANSPORT` | `stdio` (default) or `sse` |
| `SPEECHWIRE_MCP_HOST` | SSE bind host (default `0.0.0.0`) |
| `SPEECHWIRE_MCP_PORT` | SSE bind port (default `8080`) |

## Development Workflow

```bash
pip install -e ".[dev]"   # editable install with dev deps
ruff check src/ tests/     # lint
pytest                     # test
```

CI runs on Python 3.11, 3.12, and 3.13. Publishing to PyPI is triggered by
pushing a `v*` tag.

## Adding a New MCP Tool

1. Add a parser in `judges/parsers.py` (pure function, HTML → data).
2. Add a retrieval function in `judges/client.py` using `_fetch_and_parse`.
3. Export it from `judges/__init__.py`.
4. Register the tool in `server.py` with `@mcp.tool()` and a clear docstring.
5. Write parser tests in `tests/`.
