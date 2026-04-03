"""Pure parsers for SpeechWire login / discovery pages.

Each function takes an HTML string and returns structured data — no side
effects, no network calls.
"""

import logging
import re

from speechwire_mcp.parsing_helpers import make_soup, extract_int_query_param

logger = logging.getLogger(__name__)


def parse_account_list_html(html: str) -> list[dict]:
    """Parse the ``c-account-select.php`` page into a list of accounts.

    Looks for anchor tags whose ``href`` contains ``selectaccountid=``.
    The visible link text is used as the account name.

    Parameters
    ----------
    html : str
        Raw HTML of the account-select page.

    Returns
    -------
    list[dict]
        Each dict has ``account_id`` (int) and ``name`` (str).
    """
    soup = make_soup(html)
    accounts: list[dict] = []

    for a_tag in soup.find_all("a", href=re.compile(r"selectaccountid=")):
        account_id = extract_int_query_param(a_tag, "selectaccountid")
        if account_id is None:
            continue
        name = a_tag.get_text(strip=True) or f"Account {account_id}"
        accounts.append({"account_id": account_id, "name": name})

    return accounts


_DATE_IN_PARENS_RE = re.compile(
    r"\(([A-Z][a-z]+\.?\s+\d{1,2}(?:-\d{1,2})?,\s+\d{4})\)\s*$"
)


def _extract_date_from_name(name: str) -> str | None:
    """Extract a parenthesized date string from the end of a tournament name.

    Parameters
    ----------
    name : str
        Tournament name, possibly ending with ``"(Oct. 25, 2025)"``.

    Returns
    -------
    str | None
        The raw date string (e.g. ``"Oct. 25, 2025"``) or ``None``.
    """
    m = _DATE_IN_PARENS_RE.search(name)
    return m.group(1) if m else None


def parse_tournament_list_html(html: str) -> list[dict]:
    """Parse ``c-circuit-tournaments.php`` into current and past-season tournaments.

    Returns all tournaments from both the current-season form
    (``formaddexisting``) and the historical form (``formold``), each tagged
    with a ``season`` field.

    Uses three strategies in priority order:

    1. ``<select name="tournid">`` inside forms (real SpeechWire HTML).
       Processes **all** matching forms, not just the first.
    2. Anchor tags with ``tournid=`` & ``circuitid=`` query params in href.
    3. Forms with hidden ``<input name="tournid">`` fields.

    Parameters
    ----------
    html : str
        Raw HTML of the circuit-tournaments page.

    Returns
    -------
    list[dict]
        Each dict has ``tournament_id`` (int), ``circuit_id`` (int | None),
        ``name`` (str), ``date`` (str | None), and ``season`` (str, either
        ``"current"`` or ``"past"``).
    """
    soup = make_soup(html)
    tournaments: list[dict] = []
    seen: set[int] = set()

    # Strategy 1: <select name="tournid"> inside forms (real SpeechWire HTML).
    # Collect all forms containing a tournid select, processing
    # formaddexisting (current) before formold (past) so current wins dedup.
    all_forms = soup.find_all("form")
    select_forms: list[tuple] = []  # (form element, season str)
    for form in all_forms:
        select = form.find("select", {"name": "tournid"})
        if not select:
            continue
        form_name = (form.get("name") or "").strip()
        if form_name == "formold":
            season = "past"
        else:
            season = "current"
        select_forms.append((form, season))

    # Sort so "current" forms come first (current < past alphabetically)
    select_forms.sort(key=lambda t: t[1])

    for form, season in select_forms:
        select = form.find("select", {"name": "tournid"})
        circuit_id: int | None = None
        circuit_input = form.find("input", {"name": "circuitid"})
        if circuit_input:
            try:
                circuit_id = int(circuit_input.get("value", ""))
            except (ValueError, TypeError):
                pass

        for option in select.find_all("option"):
            val = (option.get("value") or "").strip()
            if not val or not val.isdigit():
                continue
            tourn_id = int(val)
            if tourn_id in seen:
                continue
            seen.add(tourn_id)
            name = option.get_text(strip=True) or f"Tournament {tourn_id}"
            date = _extract_date_from_name(name)
            tournaments.append({
                "tournament_id": tourn_id,
                "circuit_id": circuit_id,
                "name": name,
                "date": date,
                "season": season,
            })

    # Strategy 2: anchor tags with tournid & circuitid in the href
    if not tournaments:
        for a_tag in soup.find_all("a", href=re.compile(r"tournid=")):
            tourn_id = extract_int_query_param(a_tag, "tournid")
            cid = extract_int_query_param(a_tag, "circuitid")
            if tourn_id is None or cid is None:
                continue
            if tourn_id in seen:
                continue
            seen.add(tourn_id)
            name = a_tag.get_text(strip=True) or f"Tournament {tourn_id}"
            date = _extract_date_from_name(name)
            tournaments.append({
                "tournament_id": tourn_id,
                "circuit_id": cid,
                "name": name,
                "date": date,
                "season": "current",
            })

    # Strategy 3: forms with hidden inputs
    if not tournaments:
        for form in soup.find_all("form"):
            tourn_input = form.find("input", {"name": "tournid"})
            circuit_input = form.find("input", {"name": "circuitid"})
            if not tourn_input or not circuit_input:
                continue
            try:
                tourn_id = int(tourn_input.get("value", ""))
                cid = int(circuit_input.get("value", ""))
            except (ValueError, TypeError):
                continue
            if tourn_id in seen:
                continue
            seen.add(tourn_id)
            label = form.get_text(strip=True) or f"Tournament {tourn_id}"
            if len(label) > 120:
                label = label[:120].rsplit(" ", 1)[0] + "…"
            tournaments.append({
                "tournament_id": tourn_id,
                "circuit_id": cid,
                "name": label,
                "date": None,
                "season": "current",
            })

    return tournaments
