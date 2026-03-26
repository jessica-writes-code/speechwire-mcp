"""Parsers for SpeechWire tournament structure pages.

Pure functions that convert HTML strings into structured data.
No side effects — safe for unit testing with fixture HTML.
"""

import logging

from bs4 import Tag

from speechwire_mcp.parsing_helpers import make_soup, extract_int_query_param

logger = logging.getLogger(__name__)


def _parse_event_headers(header_row: Tag) -> list[str]:
    """Extract event names from a tableheader row.

    Parameters
    ----------
    header_row : Tag
        A ``<tr class="tableheader">`` containing event column headers.

    Returns
    -------
    list[str]
        Event names (e.g., ``["EVT-A", "EVT-B", "EVT-C"]``).
    """
    tds = header_row.find_all("td")
    # First cell is the "Time" column header; remaining cells are events
    return [td.get_text(strip=True) for td in tds[1:] if td.get_text(strip=True)]


def _parse_round_assignments(row: Tag, event_names: list[str]) -> list[dict]:
    """Extract round assignments from a timeslot's second row.

    The second row of each timeslot pair contains ``<select>`` elements
    for each event's round assignment. The currently-selected ``<option>``
    shows what round (if any) is assigned to this event in this slot.

    Parameters
    ----------
    row : Tag
        The second ``<tr>`` of a timeslot pair.
    event_names : list[str]
        Column header event names, in order.

    Returns
    -------
    list[dict]
        Each dict has ``event_name`` (str) and ``round_label`` (str | None).
    """
    assignments: list[dict] = []
    selects = row.find_all("select")

    for i, event_name in enumerate(event_names):
        round_label: str | None = None
        if i < len(selects):
            selected = selects[i].find("option", selected=True)
            if selected:
                text = selected.get_text(strip=True)
                value = selected.get("value", "0")
                if text and str(value) != "0":
                    round_label = text
        assignments.append(
            {
                "event_name": event_name,
                "round_label": round_label,
            }
        )

    return assignments


def parse_timeslots_from_html(html: str) -> list[dict]:
    """Parse the slots-list.php page into a list of timeslot records.

    Extracts the "Current tournament schedule" table from ``<form name="form2">``.
    Date headers, event column headers, and paired timeslot rows are processed
    to produce structured records.

    Parameters
    ----------
    html : str
        Raw HTML from the slots-list page.

    Returns
    -------
    list[dict]
        Each record contains:
        - ``slot_id`` (int) — from the slotid query parameter
        - ``time`` (str) — e.g., ``"9:00 AM"``
        - ``description`` (str | None) — e.g., ``"Round 1"``
        - ``date`` (str | None) — e.g., ``"Mar. 21, 2026"``
        - ``round_assignments`` (list[dict]) — each with ``event_name`` (str)
          and ``round_label`` (str | None)
    """
    soup = make_soup(html)

    form = soup.find("form", attrs={"name": "form2"})
    if not form:
        return []

    table = form.find("table", class_="dd")
    if not table:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    records: list[dict] = []
    current_date: str | None = None
    event_names: list[str] = []

    i = 0
    while i < len(rows):
        tr = rows[i]
        row_classes = tr.get("class") or []

        # Date header row
        if "tablemajorheader" in row_classes:
            date_text = tr.get_text(strip=True)
            if date_text:
                current_date = date_text
            i += 1
            continue

        # Event column header row
        if "tableheader" in row_classes:
            names = _parse_event_headers(tr)
            if names:
                event_names = names
            i += 1
            continue

        # Timeslot pair: first row has time + description
        time_td = tr.find("td", attrs={"rowspan": "2"})
        if time_td:
            time_link = time_td.find("a")
            if not time_link:
                i += 1
                continue

            slot_id = extract_int_query_param(time_link, "slotid")
            if slot_id is None:
                i += 1
                continue

            time_text = time_link.get_text(strip=True)

            # Description is in a colspan cell
            desc_td = tr.find("td", attrs={"colspan": True})
            description: str | None = None
            if desc_td:
                desc_text = desc_td.get_text(strip=True)
                if desc_text:
                    description = desc_text

            # Second row has round assignment selects
            round_assignments: list[dict] = []
            if i + 1 < len(rows):
                round_assignments = _parse_round_assignments(rows[i + 1], event_names)
                i += 2
            else:
                i += 1

            records.append(
                {
                    "slot_id": slot_id,
                    "time": time_text,
                    "description": description,
                    "date": current_date,
                    "round_assignments": round_assignments,
                }
            )
            continue

        i += 1

    return records


def parse_groupings_from_html(html: str) -> list[dict]:
    """Parse the groupings-manage.php page into a list of grouping records.

    Finds the ``<table class="dd">`` whose ``tableheader`` row contains
    "Grouping name" and extracts one record per data row.

    Parameters
    ----------
    html : str
        Raw HTML from the groupings-manage page.

    Returns
    -------
    list[dict]
        Each record contains:
        - ``grouping_id`` (int) — from the ``groupingid`` query parameter
        - ``name`` (str) — full grouping name (e.g., ``"Varsity Lincoln-Douglas"``)
        - ``abbreviation`` (str) — short code (e.g., ``"EVT-A"``)
        - ``event`` (str) — event name (e.g., ``"Policy Debate"``)
        - ``divisions`` (str) — division text, whitespace-stripped (e.g., ``"JV, Varsity"``)
    """
    soup = make_soup(html)

    # Locate the correct table by finding the tableheader with "Grouping name"
    target_table = None
    for table in soup.find_all("table", class_="dd"):
        header = table.find("tr", class_="tableheader")
        if header and "Grouping name" in header.get_text():
            target_table = table
            break

    if not target_table:
        return []

    rows = target_table.find_all("tr")
    records: list[dict] = []

    for row in rows:
        if "tableheader" in (row.get("class") or []):
            continue

        tds = row.find_all("td")
        if len(tds) < 4:
            continue

        name_link = tds[0].find("a")
        grouping_id = extract_int_query_param(name_link, "groupingid")
        if grouping_id is None:
            continue

        name = name_link.get_text(strip=True) if name_link else ""
        abbreviation = tds[1].get_text(strip=True)
        event = tds[2].get_text(strip=True)
        divisions = tds[3].get_text(strip=True)

        records.append(
            {
                "grouping_id": grouping_id,
                "name": name,
                "abbreviation": abbreviation,
                "event": event,
                "divisions": divisions,
            }
        )

    return records
