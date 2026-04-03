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
        Each record contains: judge_id, name, team, team_id, is_coach,
        is_active, is_clean, is_priority, email, unavailability, blocks.
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

        # Col 0: Name + judge_id + optional (Coach) indicator
        name = None
        judge_id: Optional[int] = None
        is_coach = False
        name_td = td_safe(tds, 0)
        if name_td:
            name_link = name_td.find("a")
            if name_link:
                name = name_link.get_text(strip=True) or None
                judge_id = extract_int_query_param(name_link, "judgeid")
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

        # Col 7: Email address
        email: str | None = None
        email_td = td_safe(tds, 7)
        if email_td:
            email_match = _EMAIL_RE.search(email_td.get_text(" ", strip=True))
            if email_match:
                email = email_match.group(0).lower()

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

        records.append(
            {
                "judge_id": judge_id,
                "name": name,
                "team": team,
                "team_id": team_id,
                "is_coach": is_coach,
                "is_active": is_active,
                "is_clean": is_clean,
                "is_priority": is_priority,
                "email": email,
                "unavailability": unavailability,
                "blocks": blocks,
            }
        )

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

    select = soup.find("select", {"id": "teamid"}) or soup.find("select", {"name": "teamid"})
    if not select:
        return {"school": None, "team_id": None}

    option = select.find("option", selected=True)
    if not option:
        return {"school": None, "team_id": None}

    school = option.get_text(strip=True) or None
    raw_val = option.get("value", "")
    team_id = int(raw_val) if raw_val and str(raw_val).isdigit() else None

    return {"school": school, "team_id": team_id}


def parse_add_judge_response(html: str) -> Dict:
    """Parse the response from a judge-creation POST.

    Determines whether the judge was successfully created by looking for
    success indicators (judge links, list tables) and error indicators
    (form re-rendered, error text).

    Parameters
    ----------
    html : str
        Raw HTML response from ``judges-edit.php``.

    Returns
    -------
    dict
        ``{"success": bool, "judge_id": int | None, "error": str | None}``
    """
    soup = make_soup(html)

    # --- error signals ---
    mode_input = soup.find("input", {"name": "mode", "value": "addjudge"})
    error_texts: List[str] = []
    for tag in soup.find_all(["p", "div"]):
        text = tag.get_text(" ", strip=True)
        if text and "error" in text.lower():
            error_texts.append(text)

    no_judge = bool(soup.find(string=lambda s: s and "No judge specified" in s))
    has_error = bool(mode_input) or bool(error_texts) or no_judge

    # --- success signals ---
    judge_id: Optional[int] = None
    success_msg = soup.find("div", class_="successmsg")

    # Extract judge_id from hidden input or links
    judge_id_input = soup.find("input", {"name": "judgeid"})
    if judge_id_input:
        try:
            judge_id = int(judge_id_input.get("value", ""))
        except (ValueError, TypeError):
            pass

    if judge_id is None:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "judgeid=" in href:
                judge_id = extract_int_query_param(a, "judgeid")
                if judge_id is not None:
                    break

    body_text = soup.get_text(" ", strip=True).lower()
    has_success = (
        success_msg is not None
        or judge_id is not None
        or "judge added" in body_text
        or "added" in body_text
        or "saved" in body_text
    )

    # --- priority: error overrides success ---
    if has_error:
        return {
            "success": False,
            "judge_id": None,
            "error": error_texts[0] if error_texts else "form re-rendered (add failed)",
        }

    if has_success:
        return {"success": True, "judge_id": judge_id, "error": None}

    # ambiguous 200 — assume success
    return {"success": True, "judge_id": None, "error": None}


def parse_judge_types_from_html(html: str) -> List[Dict]:
    """Parse the judge types list page into structured records.

    Parameters
    ----------
    html : str
        Raw HTML of ``judgetypes-list.php``.

    Returns
    -------
    list[dict]
        Each dict has ``judge_type_id`` (int), ``judge_type`` (str),
        and ``groupings`` (list[str]).
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

        # Col 0: judge type name + judge_type_id from link
        name_td = td_safe(tds, 0)
        judge_type_id: Optional[int] = None
        judge_type: Optional[str] = None
        if name_td:
            link = name_td.find("a")
            if link:
                judge_type_id = extract_int_query_param(link, "judgetypeid")
                judge_type = link.get_text(strip=True) or None

        if judge_type_id is None:
            continue

        # Col 1: comma-separated grouping codes
        groupings_td = td_safe(tds, 1)
        groupings: List[str] = []
        if groupings_td:
            raw = groupings_td.get_text(strip=True)
            groupings = [g.strip() for g in raw.split(",") if g.strip()]

        records.append({
            "judge_type_id": judge_type_id,
            "judge_type": judge_type,
            "groupings": groupings,
        })

    return records
