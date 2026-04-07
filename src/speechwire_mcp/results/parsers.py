"""Parsers for SpeechWire tournament results (tab sheet) pages.

Pure functions that convert HTML strings into structured data.
No side effects — safe for unit testing with fixture HTML.
"""

import logging
import re

from bs4 import Tag

from speechwire_mcp.parsing_helpers import make_soup, extract_int_query_param

logger = logging.getLogger(__name__)


def _parse_round_cell(td: Tag | None) -> dict:
    """Parse a single round-result cell from a team row.

    Parameters
    ----------
    td : Tag | None
        A ``<td>`` element containing a round result (W/L/BYE/FORFEIT/empty).

    Returns
    -------
    dict
        Keys: ``result`` (str | None), ``opponent`` (str | None),
        ``side`` (str | None), ``judge`` (str | None),
        ``judge_number`` (int | None).
    """
    empty = {
        "result": None,
        "opponent": None,
        "side": None,
        "judge": None,
        "judge_number": None,
    }
    if not td:
        return empty

    text = td.get_text(separator="|", strip=True)
    if not text or text == "\xa0":
        return empty

    strong = td.find("strong")
    if not strong:
        return empty

    result_text = strong.get_text(strip=True)

    if result_text == "BYE":
        return {**empty, "result": "BYE"}
    if result_text == "FORFEIT":
        return {**empty, "result": "FORFEIT"}

    if result_text not in ("W", "L"):
        return empty

    result: dict = {"result": result_text, "opponent": None, "side": None,
                    "judge": None, "judge_number": None}

    # The cell text after the strong tag looks like:
    # "W|  - Oyster Adams PIMA - Neg|2 Margaret Kepler"
    # Split on "|" to get segments
    segments = text.split("|")

    # Second segment has " - Opponent Name - Side"
    if len(segments) >= 2:
        match_text = segments[1].strip()
        # Strip leading " - "
        if match_text.startswith("- "):
            match_text = match_text[2:].strip()

        # Side is the last token after " - "
        parts = match_text.rsplit(" - ", 1)
        if len(parts) == 2:
            result["opponent"] = parts[0].strip()
            side_text = parts[1].strip()
            if side_text:
                result["side"] = side_text
        else:
            result["opponent"] = match_text or None

    # Third segment has judge info: "2 Margaret Kepler"
    if len(segments) >= 3:
        judge_text = segments[2].strip()
        judge_match = re.match(r"^(\d+)\s+(.+)$", judge_text)
        if judge_match:
            result["judge_number"] = int(judge_match.group(1))
            result["judge"] = judge_match.group(2).strip()
        elif judge_text:
            result["judge"] = judge_text

    return result


def _parse_speaker_scores(tds: list[Tag], num_rounds: int) -> list[float | None]:
    """Extract per-round speaker scores from a speaker row's cells.

    Parameters
    ----------
    tds : list[Tag]
        All ``<td>`` elements in the speaker row.
    num_rounds : int
        Number of round columns.

    Returns
    -------
    list[float | None]
        One score per round; ``None`` for empty cells.
    """
    scores: list[float | None] = []
    for i in range(1, num_rounds + 1):
        if i < len(tds):
            text = tds[i].get_text(strip=True)
            if text and text != "\xa0":
                try:
                    scores.append(float(text))
                except ValueError:
                    scores.append(None)
            else:
                scores.append(None)
        else:
            scores.append(None)
    return scores


def _parse_float(text: str) -> float | None:
    """Parse a float from stripped text, returning None on failure."""
    if not text or text == "\xa0":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_tab_sheet_from_html(html: str) -> dict:
    """Parse a tab-grouping.php page into structured results data.

    Parameters
    ----------
    html : str
        Raw HTML from the tab-grouping.php page.

    Returns
    -------
    dict
        Keys:
        - ``grouping_name`` (str) — name of the grouping
        - ``round_names`` (list[str]) — header labels for each round column
        - ``competitors`` (list[dict]) — one per team/competitor, containing:
            - ``comp_id`` (int) — from the ``compid`` query parameter
            - ``name`` (str) — team/competitor display name
            - ``rounds`` (list[dict]) — per-round results, each with:
                - ``round_number`` (int)
                - ``result`` (str | None) — "W", "L", "BYE", "FORFEIT", or None
                - ``opponent`` (str | None)
                - ``side`` (str | None) — "AFF", "Neg", or None
                - ``judge`` (str | None)
                - ``judge_number`` (int | None)
            - ``record`` (str) — e.g. "3-0"
            - ``total_points`` (float | None) — combined speaker points
            - ``placement`` (str) — e.g. "2nd"
            - ``speakers`` (list[dict]) — individual speakers, each with:
                - ``name`` (str)
                - ``round_scores`` (list[float | None])
                - ``total_points`` (float | None)
                - ``placement`` (str)
    """
    soup = make_soup(html)

    # Extract grouping name from the pagesubtitle span
    grouping_name = ""
    subtitle = soup.find("span", class_="pagesubtitle")
    if subtitle:
        grouping_name = subtitle.get_text(strip=True)

    # Find the results table (table.dd with a tableheader containing "Competitor")
    target_table = None
    for table in soup.find_all("table", class_="dd"):
        header = table.find("tr", class_="tableheader")
        if header and "Competitor" in header.get_text():
            target_table = table
            break

    if not target_table:
        return {"grouping_name": grouping_name, "round_names": [], "competitors": []}

    # Parse header to determine round column names
    header_row = target_table.find("tr", class_="tableheader")
    header_cells = header_row.find_all("td") if header_row else []
    # Columns: Competitor, Round 1, ..., Round N, Totals, Results
    # Round names are everything between "Competitor" and "Totals"
    round_names: list[str] = []
    for td in header_cells[1:]:
        text = td.get_text(strip=True)
        if text in ("Totals", "Results"):
            break
        if text:
            round_names.append(text)

    num_rounds = len(round_names)

    # Process data rows
    rows = target_table.find_all("tr")
    competitors: list[dict] = []
    current_competitor: dict | None = None

    for row in rows:
        if "tableheader" in (row.get("class") or []):
            continue

        tds = row.find_all("td")
        if not tds:
            continue

        first_cell = tds[0]
        # Team/competitor row: first cell contains <strong><a href='view-comp.php?compid=...'>
        team_link = first_cell.find(
            "a", href=lambda h: h and "view-comp.php" in h and "compid=" in h
        )

        if team_link and first_cell.find("strong"):
            # Save previous competitor
            if current_competitor is not None:
                competitors.append(current_competitor)

            comp_id = extract_int_query_param(team_link, "compid")
            name = team_link.get_text(strip=True)

            # Parse per-round results
            rounds: list[dict] = []
            for r_idx in range(num_rounds):
                td_idx = r_idx + 1
                round_td = tds[td_idx] if td_idx < len(tds) else None
                round_data = _parse_round_cell(round_td)
                round_data["round_number"] = r_idx + 1
                rounds.append(round_data)

            # Totals cell: <strong>3-0</strong><br/><span>171.3</span>
            totals_idx = num_rounds + 1
            record = ""
            total_points: float | None = None
            if totals_idx < len(tds):
                totals_td = tds[totals_idx]
                record_strong = totals_td.find("strong")
                if record_strong:
                    record = record_strong.get_text(strip=True)
                pts_span = totals_td.find("span")
                if pts_span:
                    total_points = _parse_float(pts_span.get_text(strip=True))

            # Results/placement cell
            results_idx = num_rounds + 2
            placement = ""
            if results_idx < len(tds):
                results_td = tds[results_idx]
                placement_strong = results_td.find("strong")
                if placement_strong:
                    placement = placement_strong.get_text(strip=True)
                else:
                    placement = results_td.get_text(strip=True)

            current_competitor = {
                "comp_id": comp_id,
                "name": name,
                "rounds": rounds,
                "record": record,
                "total_points": total_points,
                "placement": placement,
                "speakers": [],
            }
        elif current_competitor is not None:
            # Speaker row: plain name in first cell, scores in subsequent cells
            speaker_name = first_cell.get_text(strip=True)
            if not speaker_name or speaker_name == "\xa0":
                continue

            round_scores = _parse_speaker_scores(tds, num_rounds)

            # Total points cell
            total_idx = num_rounds + 1
            spk_total: float | None = None
            if total_idx < len(tds):
                spk_total = _parse_float(tds[total_idx].get_text(strip=True))

            # Placement cell
            placement_idx = num_rounds + 2
            spk_placement = ""
            if placement_idx < len(tds):
                spk_placement = tds[placement_idx].get_text(strip=True)

            current_competitor["speakers"].append({
                "name": speaker_name,
                "round_scores": round_scores,
                "total_points": spk_total,
                "placement": spk_placement,
            })

    # Don't forget the last competitor
    if current_competitor is not None:
        competitors.append(current_competitor)

    return {
        "grouping_name": grouping_name,
        "round_names": round_names,
        "competitors": competitors,
    }
