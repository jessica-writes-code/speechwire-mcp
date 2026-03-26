from typing import Optional, List, Dict
import logging
import re
from bs4 import element

from speechwire_mcp.parsing_helpers import make_soup, td_safe, extract_int_query_param

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.IGNORECASE)


def _selected_value(td: Optional[element.Tag], select_name_prefix: str) -> Optional[str]:
    """Return the selected <option> value from a <select> inside a <td>."""
    if td is None:
        return None
    select = td.find("select", {"name": re.compile(rf"^{select_name_prefix}\[")})
    if not select:
        return None
    option = select.find("option", selected=True)
    return option.get("value") if option else None


def parse_judge_list_from_html(html: str) -> List[Dict]:
    """Parse SpeechWire judge dashboard HTML into structured judge records.

    The dashboard sometimes marks judges with a ``(Coach)`` indicator next
    to their name.  When present, the ``is_coach`` field is ``True`` and the
    indicator text is stripped from the returned ``name``.

    Returns
    -------
    list[dict]
        Each record contains: judgeid, name, team, team_id, is_coach,
        is_active, is_clean, is_priority, unavailability, blocks.
    """
    soup = make_soup(html)
    table = soup.find("table", class_="dd")
    if table is None:
        return []

    records: List[Dict] = []

    for tr in table.find_all("tr"):
        if "tableheader" in (tr.get("class") or []):
            continue

        tds = tr.find_all("td")
        if not tds:
            continue

        # Col 0: Name + judgeid + optional (Coach) indicator
        name = None
        judgeid: Optional[int] = None
        is_coach = False
        name_td = td_safe(tds, 0)
        if name_td:
            name_link = name_td.find("a")
            if name_link:
                name = name_link.get_text(strip=True) or None
                judgeid = extract_int_query_param(name_link, "judgeid")
            td_text = name_td.get_text(" ", strip=True)
            if "(Coach)" in td_text:
                is_coach = True

        # Col 1: Team name + team_id
        team: Optional[str] = None
        team_id: Optional[int] = None
        team_td = td_safe(tds, 1)
        if team_td:
            team_link = team_td.find("a")
            if team_link:
                team = team_link.get_text(strip=True) or None
                team_id = extract_int_query_param(team_link, "teamid")

        # Col 4: Active? (inverted: value="0" means active)
        active_val = _selected_value(td_safe(tds, 4), "judgeinactive")
        is_active = active_val == "0" if active_val is not None else True

        # Col 5: Clean? (value="1" means clean)
        clean_val = _selected_value(td_safe(tds, 5), "judgeisclean")
        is_clean = clean_val == "1" if clean_val is not None else False

        # Col 6: Priority? (value="1" means priority)
        prio_val = _selected_value(td_safe(tds, 6), "judgepriorityupd")
        is_priority = prio_val == "1" if prio_val is not None else False

        # Col 8: Unavailability text
        unavail_td = td_safe(tds, 8)
        unavailability: Optional[str] = None
        if unavail_td:
            text = unavail_td.get_text(strip=True)
            if text:
                unavailability = text

        # Col 10: Blocks (e.g. "GROUPING: Varsity Policy Debate")
        blocks: List[str] = []
        blocks_td = td_safe(tds, 10)
        if blocks_td:
            raw = blocks_td.decode_contents().strip()
            if raw and raw != "&nbsp;":
                blocks = [b.strip() for b in raw.split("<br/>") if b.strip()]

        records.append({
            "judgeid": judgeid,
            "name": name,
            "team": team,
            "team_id": team_id,
            "is_coach": is_coach,
            "is_active": is_active,
            "is_clean": is_clean,
            "is_priority": is_priority,
            "unavailability": unavailability,
            "blocks": blocks,
        })

    return records


def parse_availability_from_edit_html(html: str) -> List[Dict]:
    """Parse the 'Availability by timeslot' table from a judge edit HTML page."""
    soup = make_soup(html)

    p = soup.find(
        "p",
        class_="sectiontitle",
        string=lambda s: s and "Availability by timeslot" in s,
    )
    if not p:
        return []

    table = p.find_next("table", class_="dd")
    if not table:
        return []

    header = table.find("tr", class_="tableheader")
    labels: List[str] = []
    if header:
        header_tds = header.find_all("td")
        labels = [td.get_text(" ", strip=True) for td in header_tds]

    inputs = table.find_all("input", {"type": "checkbox"})
    availability: List[Dict] = []
    idx = 0
    for inp in inputs:
        name = inp.get("name", "") or ""
        m = re.match(r"slotunblock\[(\d+)\]", name)
        if not m:
            continue
        slot_index = int(m.group(1))
        available = inp.has_attr("checked")
        label = labels[idx] if idx < len(labels) else f"slot{slot_index}"
        availability.append(
            {"slot_index": slot_index, "label": label, "available": bool(available)}
        )
        idx += 1

    availability.sort(key=lambda x: x["slot_index"])
    return availability


def parse_phone_from_edit_html(html: str) -> Optional[str]:
    """Extract the cell phone text from a judge edit HTML page."""
    if not html:
        return None
    m = re.search(r"Cell phone:\s*([+\d()\-.\s]+)", html, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip()


def parse_judge_edit_contact_html(html: str) -> Dict:
    """Extract email and phone from a judge edit page HTML.

    Returns dict with keys: email, phone.
    """
    soup = make_soup(html)

    def _valid_email(val: Optional[str]) -> Optional[str]:
        if not val:
            return None
        val = val.strip()
        if not _EMAIL_RE.search(val):
            return None
        return val.lower()

    # 1) Prefer explicit judgeemail input value
    email_val: Optional[str] = None
    email_input = soup.find("input", {"id": "judgeemail"}) or soup.find(
        "input", {"name": "judgeemail"}
    )
    if email_input:
        email_val = _valid_email(email_input.get("value", "") or "")

    # 2) Fallback: collect all emails from the HTML and prefer non-support addresses
    if not email_val:
        all_matches = _EMAIL_RE.findall(html or "")
        candidates = [m.lower() for m in all_matches if m]
        non_support = [c for c in candidates if "support@" not in c]
        if non_support:
            email_val = non_support[0]
        elif candidates:
            email_val = candidates[0]
        else:
            email_val = None

    email = _valid_email(email_val)
    phone = parse_phone_from_edit_html(html)

    return {
        "email": email,
        "phone": phone,
    }


def parse_school_from_edit_html(html: str) -> Dict:
    """Extract the judge's school (team) association from a judge edit page.

    The school is determined by the selected ``<option>`` in the
    ``<select id="teamid">`` dropdown on the judge-edit form.

    Parameters
    ----------
    html : str
        Raw HTML of the judge edit page.

    Returns
    -------
    dict
        ``{"school": str | None, "team_id": int | None}``
    """
    soup = make_soup(html)

    select = soup.find("select", {"id": "teamid"}) or soup.find(
        "select", {"name": "teamid"}
    )
    if not select:
        return {"school": None, "team_id": None}

    option = select.find("option", selected=True)
    if not option:
        return {"school": None, "team_id": None}

    school = option.get_text(strip=True) or None
    raw_val = option.get("value", "")
    team_id = int(raw_val) if raw_val and str(raw_val).isdigit() else None

    return {"school": school, "team_id": team_id}
