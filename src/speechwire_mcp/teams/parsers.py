import logging
import re
from speechwire_mcp.parsing_helpers import make_soup, td_safe, extract_int_query_param

logger = logging.getLogger(__name__)


def _yes_no_to_bool(text: str | None, uppercase: bool = False) -> bool:
    """Convert 'Yes'/'No' or 'YES'/'NO' text to boolean."""
    if text is None:
        return False
    text = text.strip()
    if uppercase:
        return text.upper() == "YES"
    return text.lower() == "yes"


def parse_team_list_html(html: str) -> list[dict]:
    """Parse SpeechWire team list HTML into structured team records.

    Parameters
    ----------
    html : str
        Raw HTML from teams-list.php page.

    Returns
    -------
    list[dict]
        Each record contains: team_id (int), name (str), code (str | None),
        is_invited (bool), is_attending (bool), is_checked_in (bool),
        is_udl_member (bool).
    """
    soup = make_soup(html)
    table = soup.find("table", class_="dd")
    if table is None:
        return []

    records: list[dict] = []

    for tr in table.find_all("tr"):
        if "tableheader" in (tr.get("class") or []):
            continue

        tds = tr.find_all("td")
        if not tds:
            continue

        # Col 0: Team name + team_id
        name = None
        team_id: int | None = None
        name_td = td_safe(tds, 0)
        if name_td:
            name_link = name_td.find("a")
            if name_link:
                name = name_link.get_text(strip=True) or None
                team_id = extract_int_query_param(name_link, "teamid")

        # Skip rows without valid team_id
        if team_id is None:
            continue

        # Col 1: Team code
        code = None
        code_td = td_safe(tds, 1)
        if code_td:
            code_text = code_td.get_text(strip=True)
            code = code_text if code_text else None

        # Col 2: Invited? (Yes/No)
        invited_td = td_safe(tds, 2)
        is_invited = _yes_no_to_bool(
            invited_td.get_text(strip=True) if invited_td else None
        )

        # Col 3: Attending? (Yes/No)
        attending_td = td_safe(tds, 3)
        is_attending = _yes_no_to_bool(
            attending_td.get_text(strip=True) if attending_td else None
        )

        # Col 4: Checked in? (YES/NO - uppercase)
        checked_in_td = td_safe(tds, 4)
        is_checked_in = _yes_no_to_bool(
            checked_in_td.get_text(strip=True) if checked_in_td else None,
            uppercase=True,
        )

        # Col 8: UDL member? (Yes/No)
        udl_td = td_safe(tds, 8)
        is_udl_member = _yes_no_to_bool(
            udl_td.get_text(strip=True) if udl_td else None
        )

        records.append({
            "team_id": team_id,
            "name": name,
            "code": code,
            "is_invited": is_invited,
            "is_attending": is_attending,
            "is_checked_in": is_checked_in,
            "is_udl_member": is_udl_member,
        })

    return records


def parse_hybrid_entries_html(html: str) -> list[dict]:
    """Parse SpeechWire hybrid entries HTML into structured entry records.

    Parameters
    ----------
    html : str
        Raw HTML from teams-hybrids.php page.

    Returns
    -------
    list[dict]
        Each record contains: comp_id (int), event (str), division (str | None),
        students (list[dict] with name and school), code (str | None),
        team_blocks (list[str]). Each student dict includes a ``school`` field
        parsed from the "Name (School)" format in the HTML, reflecting the
        individual school affiliation for each competitor in the hybrid pairing.
    """
    soup = make_soup(html)
    table = soup.find("table", class_="dd")
    if table is None:
        return []

    records: list[dict] = []

    for tr in table.find_all("tr"):
        if "tableheader" in (tr.get("class") or []):
            continue

        tds = tr.find_all("td")
        if not tds:
            continue

        # Col 0: Event
        event = None
        event_td = td_safe(tds, 0)
        if event_td:
            event = event_td.get_text(strip=True) or None

        # Col 1: Division
        division = None
        division_td = td_safe(tds, 1)
        if division_td:
            division_text = division_td.get_text(strip=True)
            division = division_text if division_text else None

        # Col 2: Students (Name (School)<br />Name (School))
        students: list[dict] = []
        students_td = td_safe(tds, 2)
        if students_td:
            # Get the HTML content and split by <br /> or <br> tags
            html_content = str(students_td)
            # Split by br tags
            parts = re.split(r'<br\s*/?>', html_content, flags=re.IGNORECASE)
            for part in parts:
                # Strip HTML tags and get text
                text = make_soup(part).get_text(strip=True)
                if not text:
                    continue
                # Parse "Name (School)" format
                match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', text)
                if match:
                    name = match.group(1).strip()
                    school = match.group(2).strip() or None
                    students.append({"name": name, "school": school})
                else:
                    # No school in parentheses
                    students.append({"name": text, "school": None})

        # Col 3: Code
        code = None
        code_td = td_safe(tds, 3)
        if code_td:
            code = code_td.get_text(strip=True) or None

        # Col 4: Edit button (extract comp_id)
        comp_id: int | None = None
        edit_td = td_safe(tds, 4)
        if edit_td:
            edit_button = edit_td.find("input", {"type": "button", "value": "Edit"})
            if edit_button:
                # BeautifulSoup normalizes HTML attributes to lowercase
                onclick = edit_button.get("onclick", "")
                # Extract compid from teams-hybrids-edit.php?compid=NNN
                match = re.search(r'compid=(\d+)', onclick)
                if match:
                    comp_id = int(match.group(1))

        # Col 6: Team blocks (School<br />School)
        team_blocks: list[str] = []
        blocks_td = td_safe(tds, 6)
        if blocks_td:
            # Split by br tags
            html_content = str(blocks_td)
            parts = re.split(r'<br\s*/?>', html_content, flags=re.IGNORECASE)
            for part in parts:
                text = make_soup(part).get_text(strip=True)
                if text:
                    team_blocks.append(text)

        records.append({
            "comp_id": comp_id,
            "event": event,
            "division": division,
            "students": students,
            "code": code,
            "team_blocks": team_blocks,
        })

    return records


def parse_team_entries_html(html: str) -> list[dict]:
    """Parse SpeechWire team entries HTML into structured entry records.

    Parameters
    ----------
    html : str
        Raw HTML from teams-entries.php?teamid=X page.

    Returns
    -------
    list[dict]
        Each record contains: event_id (int), event_name (str | None),
        entry_number (int), entry_code (str | None),
        competitors (list[dict] with student_id, name, competitor_number),
        division (str | None), division_id (int | None), is_dropped (bool).
    """
    soup = make_soup(html)
    form = soup.find("form", {"name": "form1"})
    if not form:
        return []

    records: list[dict] = []
    current_event_name: str | None = None

    # Pattern to extract IDs from select names:
    # oldcompinput[eventid][entrynum][compnum]
    # olddivinput[eventid][entrynum]
    # oldcompdrop[eventid][entrynum]
    comp_pattern = re.compile(r"oldcompinput\[(\d+)\]\[(\d+)\]\[(\d+)\]")
    div_pattern = re.compile(r"olddivinput\[(\d+)\]\[(\d+)\]")
    drop_pattern = re.compile(r"oldcompdrop\[(\d+)\]\[(\d+)\]")

    # Track entries we've already processed (event_id, entry_number) pairs
    processed_entries: dict[tuple[int, int], dict] = {}

    # Iterate through form children to find section titles and entry divs
    for child in form.children:
        if not hasattr(child, "name"):
            continue

        # Update current event name from section titles
        if child.name == "div" and "sectiontitle" in (child.get("class") or []):
            current_event_name = child.get_text(strip=True) or None
            continue

        # Look for entry divs (direct children with selects)
        if child.name == "div":
            selects = child.find_all("select")
            if not selects:
                continue

            # Extract entry code from text before first select
            entry_code: str | None = None
            first_select = selects[0]
            # Get all text nodes before the first select
            for item in child.contents:
                if item == first_select:
                    break
                if isinstance(item, str):
                    text = item.strip()
                    if text and ":" in text:
                        entry_code = text.rstrip(":")
                        break

            # Process each select in this div
            for select in selects:
                name = select.get("name", "")
                if not name:
                    continue

                # Competitor select
                comp_match = comp_pattern.match(name)
                if comp_match:
                    event_id = int(comp_match.group(1))
                    entry_number = int(comp_match.group(2))
                    competitor_number = int(comp_match.group(3))

                    selected_option = select.find("option", selected=True)
                    if not selected_option:
                        continue

                    student_id_val = selected_option.get("value")
                    if not student_id_val or not str(student_id_val).isdigit():
                        continue

                    student_id = int(student_id_val)
                    competitor_name = selected_option.get_text(strip=True) or None

                    # Get or create entry record
                    key = (event_id, entry_number)
                    if key not in processed_entries:
                        processed_entries[key] = {
                            "event_id": event_id,
                            "event_name": current_event_name,
                            "entry_number": entry_number,
                            "entry_code": entry_code,
                            "competitors": [],
                            "division": None,
                            "division_id": None,
                            "is_dropped": False,
                        }

                    # Add competitor to entry
                    processed_entries[key]["competitors"].append({
                        "student_id": student_id,
                        "name": competitor_name,
                        "competitor_number": competitor_number,
                    })

                # Division select
                div_match = div_pattern.match(name)
                if div_match:
                    event_id = int(div_match.group(1))
                    entry_number = int(div_match.group(2))

                    selected_option = select.find("option", selected=True)
                    if selected_option:
                        division_id_val = selected_option.get("value")
                        division_id = (
                            int(division_id_val)
                            if division_id_val and str(division_id_val).isdigit()
                            else None
                        )
                        division_name = selected_option.get_text(strip=True) or None

                        # Get or create entry record
                        key = (event_id, entry_number)
                        if key not in processed_entries:
                            processed_entries[key] = {
                                "event_id": event_id,
                                "event_name": current_event_name,
                                "entry_number": entry_number,
                                "entry_code": entry_code,
                                "competitors": [],
                                "division": None,
                                "division_id": None,
                                "is_dropped": False,
                            }

                        processed_entries[key]["division"] = division_name
                        processed_entries[key]["division_id"] = division_id

                # Drop flag select
                drop_match = drop_pattern.match(name)
                if drop_match:
                    event_id = int(drop_match.group(1))
                    entry_number = int(drop_match.group(2))

                    selected_option = select.find("option", selected=True)
                    if selected_option:
                        drop_val = selected_option.get("value")
                        is_dropped = drop_val == "1"

                        # Get or create entry record
                        key = (event_id, entry_number)
                        if key not in processed_entries:
                            processed_entries[key] = {
                                "event_id": event_id,
                                "event_name": current_event_name,
                                "entry_number": entry_number,
                                "entry_code": entry_code,
                                "competitors": [],
                                "division": None,
                                "division_id": None,
                                "is_dropped": False,
                            }

                        processed_entries[key]["is_dropped"] = is_dropped

    # Sort competitors within each entry by competitor_number
    for entry in processed_entries.values():
        entry["competitors"].sort(key=lambda c: c["competitor_number"])

    # Convert to list and sort by event_id, entry_number
    records = list(processed_entries.values())
    records.sort(key=lambda e: (e["event_id"], e["entry_number"]))

    return records
