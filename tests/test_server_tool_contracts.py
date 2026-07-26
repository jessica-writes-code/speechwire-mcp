import re

from speechwire_mcp.server import mcp


def test_all_mcp_tool_parameters_have_typed_docstring_entries():
    for tool in mcp._tool_manager._tools.values():
        assert tool.description
        for parameter_name in tool.parameters.get("properties", {}):
            typed_entry = rf"(?m)^\s*{re.escape(parameter_name)}\s*:\s*\S+"
            assert re.search(typed_entry, tool.description), (
                f"{tool.name}.{parameter_name} lacks a typed docstring entry"
            )


def test_add_judge_schema_requires_discoverable_identifiers():
    tool = mcp._tool_manager._tools["speechwire_add_judge"]

    assert set(tool.parameters["required"]) == {"judge_name", "team_id"}
    assert "speechwire_list_teams" in tool.description
    assert "speechwire_list_judge_types" in tool.description
    assert "speechwire_list_timeslots" in tool.description
    assert "slot_id" in tool.description
