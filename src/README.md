# Source Contributor Guide

This guide defines conventions for contributors changing code under `src/`.

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