"""Strict error handling tests for public Python read APIs."""

import inspect
from unittest.mock import MagicMock

import pytest

from speechwire_mcp import SpeechWireAuthError, SpeechWireReadError
from speechwire_mcp.judges import client as judges_client
from speechwire_mcp.results import client as results_client
from speechwire_mcp.rooms import client as rooms_client
from speechwire_mcp.schematics import client as schematics_client
from speechwire_mcp.structure import client as structure_client
from speechwire_mcp.teams import client as teams_client

READ_CASES = [
    pytest.param(
        judges_client.get_judge_availability,
        judges_client,
        "parse_availability_from_edit_html",
        (17,),
        [],
        "availability for 17",
        id="judge-availability",
    ),
    pytest.param(
        rooms_client.get_room_counts,
        rooms_client,
        "parse_room_counts_from_html",
        (),
        [],
        "room counts",
        id="room-counts",
    ),
    pytest.param(
        structure_client.get_groupings,
        structure_client,
        "parse_groupings_from_html",
        (),
        [],
        "groupings",
        id="groupings",
    ),
    pytest.param(
        teams_client.get_team_entries,
        teams_client,
        "parse_team_entries_html",
        (17,),
        [],
        "entries for team 17",
        id="team-entries",
    ),
    pytest.param(
        teams_client.get_hybrid_entries,
        teams_client,
        "parse_hybrid_entries_html",
        (),
        [],
        "hybrid entries",
        id="hybrid-entries",
    ),
    pytest.param(
        schematics_client.get_schematic_events,
        schematics_client,
        "parse_schematic_events_html",
        (),
        [],
        "schematic events list",
        id="schematic-events",
    ),
    pytest.param(
        results_client.get_tab_sheet,
        results_client,
        "parse_tab_sheet_from_html",
        (23,),
        {},
        "tab sheet for grouping 23",
        id="tab-sheet",
    ),
]


def _response(html: str = "<html></html>") -> MagicMock:
    response = MagicMock()
    response.text = html
    return response


@pytest.mark.parametrize(
    ("reader", "module", "parser_name", "leading_args", "default", "context"),
    READ_CASES,
)
def test_raise_on_error_is_keyword_only(
    reader, module, parser_name, leading_args, default, context
):
    parameter = inspect.signature(reader).parameters["raise_on_error"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is False
    assert parameter.annotation is bool


@pytest.mark.parametrize(
    ("reader", "module", "parser_name", "leading_args", "default", "context"),
    READ_CASES,
)
def test_fetch_failure_returns_default(
    reader, module, parser_name, leading_args, default, context
):
    client = MagicMock()
    client.get.side_effect = RuntimeError("provider unavailable")

    assert reader(*leading_args, client) == default


@pytest.mark.parametrize(
    ("reader", "module", "parser_name", "leading_args", "default", "context"),
    READ_CASES,
)
def test_parse_failure_returns_default(
    monkeypatch, reader, module, parser_name, leading_args, default, context
):
    client = MagicMock()
    client.get.return_value = _response()
    parser = MagicMock(side_effect=ValueError("unexpected markup"))
    monkeypatch.setattr(module, parser_name, parser)

    assert reader(*leading_args, client) == default


@pytest.mark.parametrize(
    ("reader", "module", "parser_name", "leading_args", "default", "context"),
    READ_CASES,
)
def test_strict_fetch_failure_preserves_cause(
    reader, module, parser_name, leading_args, default, context
):
    client = MagicMock()
    cause = RuntimeError("provider unavailable")
    client.get.side_effect = cause

    with pytest.raises(SpeechWireReadError) as error:
        reader(*leading_args, client, raise_on_error=True)

    assert str(error.value) == f"Failed to fetch {context}"
    assert error.value.__cause__ is cause


@pytest.mark.parametrize(
    ("reader", "module", "parser_name", "leading_args", "default", "context"),
    READ_CASES,
)
def test_strict_auth_failure_preserves_cause(
    reader, module, parser_name, leading_args, default, context
):
    client = MagicMock()
    cause = SpeechWireAuthError("session expired")
    client.get.side_effect = cause

    with pytest.raises(SpeechWireReadError) as error:
        reader(*leading_args, client, raise_on_error=True)

    assert str(error.value) == f"Failed to fetch {context}"
    assert error.value.__cause__ is cause


@pytest.mark.parametrize(
    ("reader", "module", "parser_name", "leading_args", "default", "context"),
    READ_CASES,
)
def test_strict_parse_failure_preserves_cause(
    monkeypatch, reader, module, parser_name, leading_args, default, context
):
    client = MagicMock()
    client.get.return_value = _response()
    cause = ValueError("unexpected markup")
    parser = MagicMock(side_effect=cause)
    monkeypatch.setattr(module, parser_name, parser)

    with pytest.raises(SpeechWireReadError) as error:
        reader(*leading_args, client, raise_on_error=True)

    assert str(error.value) == f"Failed to parse {context}"
    assert error.value.__cause__ is cause


@pytest.mark.parametrize(
    ("reader", "module", "parser_name", "leading_args", "default", "context"),
    READ_CASES,
)
def test_strict_read_allows_successfully_parsed_empty_data(
    monkeypatch, reader, module, parser_name, leading_args, default, context
):
    client = MagicMock()
    client.get.return_value = _response()
    monkeypatch.setattr(module, parser_name, MagicMock(return_value=default))

    assert reader(*leading_args, client, raise_on_error=True) == default
