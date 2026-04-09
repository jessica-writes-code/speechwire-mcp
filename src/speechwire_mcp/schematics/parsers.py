import logging
import re

from urllib.parse import urlparse, parse_qs

from speechwire_mcp.parsing_helpers import make_soup, td_safe, extract_int_query_param

logger = logging.getLogger(__name__)


def _parse_judge_from_link(link) -> dict | None:
    """Extract judge info from an anchor tag with "Name [N]" format.

    Parameters
    ----------
    link : bs4.element.Tag
        Anchor tag with ``firstjudgeid`` query param.

    Returns
    -------
    dict | None
        ``{"judge_id": int, "name": str, "rounds_judged": int | None}``
        or None if judge_id cannot be extracted.
    """
    judge_id = extract_int_query_param(link, "firstjudgeid")
    if judge_id is None:
        return None
    text = link.get_text(strip=True)
    name = None
    rounds_judged = None
    if "[" in text and "]" in text:
        parts = text.rsplit("[", 1)
        name = parts[0].strip()
        try:
            rounds_judged = int(parts[1].rstrip("]").strip())
        except ValueError:
            pass
    else:
        name = text
    return {"judge_id": judge_id, "name": name, "rounds_judged": rounds_judged}


_SIDE_RE = re.compile(r"\((?:aff|neg)\)", re.IGNORECASE)


def parse_schematic_events_html(html: str) -> list[dict]:
    """Parse schematic events from the schematic viewer page.

    Returns
    -------
    list[dict]
        Each record contains: grouping_id, name, rounds (list of round numbers).
    """
    soup = make_soup(html)

    # Find the select element with events
    select = soup.find("select", id="groupingid")
    if not select:
        select = soup.find("select", attrs={"name": "groupingid"})
    if not select:
        return []

    # Build base event list from select options
    events: dict[int, dict] = {}
    for option in select.find_all("option"):
        value = option.get("value", "")
        if not value or not str(value).isdigit():
            continue
        grouping_id = int(value)
        name = option.get_text(strip=True)
        events[grouping_id] = {
            "grouping_id": grouping_id,
            "name": name,
            "rounds": [],
        }

    # Find all editor links and extract rounds per event
    editor_links = soup.find_all("a", href=lambda h: h and "schem-edit.php" in h)
    for link in editor_links:
        href = link.get("href", "")
        try:
            q = parse_qs(urlparse(href).query)
            grouping_id_str = q.get("groupingid", [None])[0]
            round_str = q.get("round", [None])[0]
            if grouping_id_str and round_str:
                if str(grouping_id_str).isdigit() and str(round_str).isdigit():
                    gid = int(grouping_id_str)
                    rnd = int(round_str)
                    if gid in events and rnd not in events[gid]["rounds"]:
                        events[gid]["rounds"].append(rnd)
        except Exception:
            continue

    # Sort rounds for each event
    for event in events.values():
        event["rounds"].sort()

    return list(events.values())


def parse_round_schematic_html(html: str) -> dict:
    """Parse round schematic from the schematic editor page.

    Returns
    -------
    dict
        Contains: event_name, round, time, unused_judges (list), sections (list).
    """
    soup = make_soup(html)
    table = soup.find("table", class_="dd")
    if not table:
        return {}

    rows = table.find_all("tr")
    if len(rows) < 2:
        return {}

    # Parse header row (row 0)
    header_row = rows[0]
    header_tds = header_row.find_all("td")
    if len(header_tds) < 2:
        return {}

    # Cell 0: event name + round + time
    event_name = None
    round_number = None
    time = None
    header_text = header_tds[0].get_text(strip=True)
    # Format: "Event Name Round N - Time"
    parts = header_text.rsplit(" Round ", 1)
    if len(parts) == 2:
        event_name = parts[0].strip()
        round_and_time = parts[1].split(" - ")
        if len(round_and_time) >= 1:
            try:
                round_number = int(round_and_time[0].strip())
            except ValueError:
                pass
        if len(round_and_time) >= 2:
            time = round_and_time[1].strip()

    # Cell 1: unused judges
    unused_judges: list[dict] = []
    unused_cell = header_tds[1]
    unused_links = unused_cell.find_all("a", href=lambda h: h and "firstjudgeid=" in h)
    for link in unused_links:
        judge = _parse_judge_from_link(link)
        if judge:
            unused_judges.append(judge)

    # Skip row 1 (column labels)
    # Parse data rows (rows 2+)
    sections: list[dict] = []
    for row in rows[2:]:
        tds = row.find_all("td")
        if len(tds) < 4:
            continue

        # Cell 0: section label + section_id
        section_td = td_safe(tds, 0)
        section_id = None
        label = None
        if section_td:
            section_link = section_td.find("a", href=lambda h: h and "sectionid=" in h)
            if section_link:
                section_id = extract_int_query_param(section_link, "sectionid")
                label = section_link.get_text(strip=True)

        # Cell 1: judge (or None)
        judge_td = td_safe(tds, 1)
        judge = None
        if judge_td:
            judge_link = judge_td.find("a", href=lambda h: h and "firstjudgeid=" in h)
            if judge_link:
                judge = _parse_judge_from_link(judge_link)

        # Cell 2: room
        room_td = td_safe(tds, 2)
        room = None
        if room_td:
            room_link = room_td.find("a")
            if room_link:
                room = room_link.get_text(strip=True)

        # Cells 3+: competitors
        competitors: list[dict] = []
        for comp_idx in range(3, len(tds)):
            comp_td = td_safe(tds, comp_idx)
            if not comp_td:
                continue

            comp_link = comp_td.find("a", href=lambda h: h and "firstcompid=" in h)
            if not comp_link:
                continue

            competitor_id = extract_int_query_param(comp_link, "firstcompid")
            if competitor_id is None:
                continue

            # Parse text: "Name (Side) (Record)"
            text = comp_td.get_text(strip=True)
            name = None
            side = None
            record = None

            # Extract side (AFF or NEG), case-insensitive
            side_match = _SIDE_RE.search(text)
            if side_match:
                side = side_match.group(0)[1:-1].upper()

            # Remove side markers to get name and record
            clean_text = _SIDE_RE.sub("", text)

            # Find record pattern (W-L)
            record_match = re.search(r"\((\d+-\d+)\)", clean_text)
            if record_match:
                record = record_match.group(1)
                clean_text = clean_text.replace(f"({record})", "")

            name = clean_text.strip()

            competitors.append({
                "competitor_id": competitor_id,
                "name": name,
                "side": side,
                "record": record,
            })

        sections.append({
            "section_id": section_id,
            "label": label,
            "judge": judge,
            "room": room,
            "competitors": competitors,
        })

    return {
        "event_name": event_name,
        "round": round_number,
        "time": time,
        "unused_judges": unused_judges,
        "sections": sections,
    }
