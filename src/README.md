# Source Contributor Guide

This guide defines conventions for contributors changing code under `src/`.

## Python SDK: Grouping/Round Entry Counts

```python
from speechwire_mcp.rooms import GroupingRoundCounts, get_grouping_round_counts

counts: GroupingRoundCounts | None = get_grouping_round_counts(
    grouping_id, round_number, client, raise_on_error=True
)
```

The additive Python reader returns a `GroupingRoundCounts` TypedDict with four
required integer fields: `grouping_id`, `round_number`, `entries`, and `sections`.
It reads `rooms-groupings.php` with `params={"groupinground": "ID,ROUND"}` and
parses the summary sentence, for example:
`There are 8 sections in JV Policy Debate, Round 1. (20 entries)`.
Entry counts do not depend on assigned rooms or created sections; an unpaired
round can report zero sections and a nonzero entry count. Existing
`get_room_counts` behavior is unchanged. No new MCP tool is registered.

Supply a positive grouping ID from `get_groupings` and an applicable positive,
1-based numeric round. The reader checks the round in the summary, but the
summary does not contain a grouping ID: the result echoes the requested ID.
It does not discover applicable rounds, interpret elimination rounds, or
extrapolate a count from another round. Consumers must choose applicable rounds
from tournament structure rather than treating an unavailable round as empty.

Counts must be explicit nonnegative decimal integers, including valid zero.
Missing, malformed, ambiguous, or wrong-round summaries are failures, not zero.
With `raise_on_error=True`, fetch/authentication and parse failures raise the
existing `SpeechWireReadError` (with the original cause); otherwise failures
are logged and return `None`. Invalid nonpositive identifiers also follow this
strict/lenient policy. Consumers estimating debate demand can use
`(counts["entries"] + 1) // 2` for each division and sum those estimates, without
falling back to `sections`.

The endpoint URL is supported by existing room-count link fixtures; the detail
markup is tested with synthetic screenshot-style HTML, not a live authenticated
page. Other heading formats require verification before being supported.
This API is not in published 0.1.4. Until a release containing it is available,
integration requires installing this checkout (for example,
`pip install -e /path/to/this/worktree`) rather than relying on a version range
that can resolve to 0.1.4. No new dependencies are needed.

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