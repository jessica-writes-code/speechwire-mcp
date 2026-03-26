"""Parsers for SpeechWire room pages.

Pure functions that convert HTML strings into structured data.
No side effects — safe for unit testing with fixture HTML.
"""

import logging
import re

from bs4 import Tag

from speechwire_mcp.parsing_helpers import make_soup, td_safe, extract_int_query_param

logger = logging.getLogger(__name__)

_CONSTRAINTS_RE = re.compile(r"\s*\(has constraints\)\s*$", re.IGNORECASE)


def parse_room_list_from_html(html: str) -> list[dict]:
    """Parse the rooms-list.php page into a list of room records.

    Primary strategy: extract ``<option>`` elements from the ``<select>``
    inside the availability-schedule form (``form[action*="rooms-avail.php"]``).

    Fallback: if the availability form is missing, try the edit form
    (``form[action*="rooms-edit.php"]``); all rooms default to
    ``has_constraints=False``.

    Parameters
    ----------
    html : str
        Raw HTML from the rooms-list page.

    Returns
    -------
    list[dict]
        Each record contains ``room_id`` (int), ``name`` (str),
        ``has_constraints`` (bool).
    """
    soup = make_soup(html)

    # Primary: availability form
    avail_form = soup.find("form", action=re.compile(r"rooms-avail\.php"))
    if avail_form:
        return _parse_select_options(avail_form, detect_constraints=True)

    # Fallback: edit form
    edit_form = soup.find("form", action=re.compile(r"rooms-edit\.php"))
    if edit_form:
        return _parse_select_options(edit_form, detect_constraints=False)

    return []


def _parse_select_options(
    form: Tag, *, detect_constraints: bool
) -> list[dict]:
    """Extract room records from ``<option>`` elements inside a form's select.

    Parameters
    ----------
    form : Tag
        A BeautifulSoup ``<form>`` tag containing a ``<select>`` with room
        ``<option>`` elements.
    detect_constraints : bool
        When ``True``, check option text for "(has constraints)" suffix.
        When ``False``, all rooms get ``has_constraints=False``.

    Returns
    -------
    list[dict]
        Room records with ``room_id``, ``name``, ``has_constraints``.
    """
    select = form.find("select")
    if not select:
        return []

    records: list[dict] = []
    for option in select.find_all("option"):
        value = option.get("value", "")
        if not value or not str(value).isdigit():
            continue

        room_id = int(value)
        raw_text = option.get_text(strip=True)

        has_constraints = False
        name = raw_text
        if detect_constraints and _CONSTRAINTS_RE.search(raw_text):
            has_constraints = True
            name = _CONSTRAINTS_RE.sub("", raw_text).strip()

        records.append({
            "room_id": room_id,
            "name": name,
            "has_constraints": has_constraints,
        })

    return records


# ---------------------------------------------------------------------------
# Room usage parser
# ---------------------------------------------------------------------------


def _parse_time_slot_cell(td: Tag) -> tuple[str, str | None, int | None]:
    """Classify a single time-slot cell from the room-usage grid.

    Parameters
    ----------
    td : Tag
        A ``<td>`` element from a data row of the usage table.

    Returns
    -------
    tuple[str, str | None, int | None]
        ``(status, event_code, round_number)`` where *status* is one of
        ``"available"``, ``"timeblock"``, ``"unavailable"``, ``"assigned"``.
    """
    cell_text = td.get_text(separator=" ", strip=True)

    # Empty / whitespace / &nbsp;
    if not cell_text or cell_text == "\xa0":
        return ("available", None, None)

    strong = td.find("strong")

    # TIMEBLOCK pattern: <strong>TIME BLOCK</strong> or text containing TIMEBLOCK
    if "TIMEBLOCK" in cell_text.upper().replace(" ", ""):
        return ("timeblock", None, None)

    if strong:
        strong_text = strong.get_text(strip=True)

        # Unavailable: <strong>X</strong> only
        if strong_text == "X":
            return ("unavailable", None, None)

        # Assigned: <strong>{EVENT_CODE}</strong> optionally followed by Round {N}
        round_match = re.search(r"Round\s+(\d+)", cell_text)
        round_number = int(round_match.group(1)) if round_match else None
        return ("assigned", strong_text, round_number)

    return ("available", None, None)


def parse_room_usage_from_html(html: str) -> list[dict]:
    """Parse the rooms-usage.php page into room-level time-slot assignments.

    Parameters
    ----------
    html : str
        Raw HTML from the rooms-usage page.

    Returns
    -------
    list[dict]
        Each record contains:
        - ``room_id`` (int) — numeric room identifier
        - ``room_name`` (str) — display name
        - ``time_slots`` (list[dict]) — per-slot records with ``slot_index``,
          ``time_label``, ``status``, ``event_code``, ``round_number``
    """
    soup = make_soup(html)
    table = soup.find("table", class_="dd")
    if table is None:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    # Extract time labels from the first tableheader row whose cells have
    # no colspan attributes (the date header uses colspans to span columns;
    # the time-label header does not).
    time_labels: list[str] = []
    header_row_indices: set[int] = set()
    for i, tr in enumerate(rows):
        if "tableheader" in (tr.get("class") or []):
            header_row_indices.add(i)
            if not time_labels:
                tds = tr.find_all("td")
                has_colspan = any(
                    int(td.get("colspan", 1)) > 1 for td in tds
                )
                if not has_colspan and len(tds) >= 2:
                    time_labels = [
                        td.get_text(strip=True) for td in tds
                    ]

    if not time_labels:
        logger.warning("Could not extract time labels from room usage table")
        return []

    records: list[dict] = []
    for i, tr in enumerate(rows):
        if i in header_row_indices:
            continue
        tds = tr.find_all("td")
        if not tds:
            continue

        # Col 0: room name + room_id from <a href="view-room.php?roomid=...">
        name_td = td_safe(tds, 0)
        if not name_td:
            continue
        room_link = name_td.find("a")
        if not room_link:
            continue
        room_name = room_link.get_text(strip=True)
        room_id = extract_int_query_param(room_link, "roomid")
        if room_id is None:
            continue

        # Cols 1–9: time slot cells
        time_slots: list[dict] = []
        for slot_idx in range(len(time_labels)):
            cell = td_safe(tds, slot_idx + 1)
            if cell is None:
                status, event_code, round_number = ("available", None, None)
            else:
                status, event_code, round_number = _parse_time_slot_cell(cell)

            time_slots.append({
                "slot_index": slot_idx,
                "time_label": time_labels[slot_idx],
                "status": status,
                "event_code": event_code,
                "round_number": round_number,
            })

        records.append({
            "room_id": room_id,
            "room_name": room_name,
            "time_slots": time_slots,
        })

    return records


# ---------------------------------------------------------------------------
# Room counts parser
# ---------------------------------------------------------------------------

_BLACKOUT_RE = re.compile(r"background-color\s*:\s*#000099", re.IGNORECASE)


def _is_blacked_out(td: Tag) -> bool:
    """Return True if a cell is blacked out (dark background)."""
    style = td.get("style", "") or ""
    return bool(_BLACKOUT_RE.search(style))


def _cell_int(td: Tag) -> int:
    """Extract an integer from a cell, checking for ``<a>`` links first.

    Returns 0 when the cell is empty, contains ``&nbsp;``, or is not numeric.
    """
    link = td.find("a")
    text = link.get_text(strip=True) if link else td.get_text(strip=True)
    if not text or text == "\xa0":
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def parse_room_counts_from_html(html: str) -> list[dict]:
    """Parse the rooms-counts.php page into per-grouping room/section counts.

    The page contains a ``<table class="dd">`` with two header rows and
    one data row per competition grouping.  Each round occupies a pair of
    columns (rooms, sections).  Blacked-out cells (``background-color:
    #000099``) indicate rounds that do not apply to a grouping and are
    skipped.

    Parameters
    ----------
    html : str
        Raw HTML from the rooms-counts page.

    Returns
    -------
    list[dict]
        Each record contains:
        - ``grouping_name`` (str) — e.g., ``"JV Policy Debate"``
        - ``rounds`` (list[dict]) — per-round records with:
          - ``round_number`` (int) — 1-based round number
          - ``rooms`` (int) — rooms assigned to this grouping/round
          - ``sections`` (int) — sections needed
          - ``sufficient`` (bool) — ``True`` when rooms ≥ sections
    """
    soup = make_soup(html)
    table = soup.find("table", class_="dd")
    if not table:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    # Identify header rows and extract round numbers from the first one.
    # Row 1 has "Grouping" (rowspan=2), "Round N" (colspan=2) cells, and a
    # trailing "Grouping" (rowspan=2).
    # Row 2 is the sub-header ("Rooms"/"Sections") — it may or may not carry
    # the ``tableheader`` class, but it always has fewer cells than data rows
    # because the rowspan-2 Grouping columns absorb its first/last positions.
    header_indices: set[int] = set()
    round_numbers: list[int] = []

    for i, tr in enumerate(rows):
        if "tableheader" in (tr.get("class") or []):
            header_indices.add(i)
            if not round_numbers:
                for td in tr.find_all("td"):
                    match = re.search(r"Round\s+(\d+)", td.get_text(strip=True))
                    if match:
                        round_numbers.append(int(match.group(1)))

    if not round_numbers:
        return []

    # Data rows must have at least 1 (grouping) + 2*N (round pairs) cells.
    # The sub-header row (Rooms/Sections) has only 2*N cells because the
    # rowspan-2 Grouping columns from the first header absorb its edges.
    min_data_cells = 1 + 2 * len(round_numbers)

    records: list[dict] = []
    for i, tr in enumerate(rows):
        if i in header_indices:
            continue

        tds = tr.find_all("td")
        if len(tds) < min_data_cells:
            continue

        grouping_name = tds[0].get_text(strip=True)
        if not grouping_name:
            continue

        rounds_data: list[dict] = []
        for r_idx, round_num in enumerate(round_numbers):
            rooms_idx = 1 + r_idx * 2
            sections_idx = rooms_idx + 1

            rooms_td = td_safe(tds, rooms_idx)
            sections_td = td_safe(tds, sections_idx)
            if rooms_td is None or sections_td is None:
                break

            if _is_blacked_out(rooms_td) or _is_blacked_out(sections_td):
                continue

            rooms_count = _cell_int(rooms_td)
            sections_count = _cell_int(sections_td)

            rounds_data.append({
                "round_number": round_num,
                "rooms": rooms_count,
                "sections": sections_count,
                "sufficient": rooms_count >= sections_count,
            })

        if rounds_data:
            records.append({
                "grouping_name": grouping_name,
                "rounds": rounds_data,
            })

    return records
