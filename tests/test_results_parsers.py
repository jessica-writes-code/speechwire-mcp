"""Tests for speechwire_mcp.results.parsers — tab sheet / results parser.

Uses fictional West Wing character names per project conventions.
"""

from speechwire_mcp.results.parsers import parse_tab_sheet_from_html

from fake_data import (
    JED_BARTLET,
    LEO_MCGARRY,
    JOSH_LYMAN,
    SAM_SEABORN,
    TOBY_ZIEGLER,
    CJ_CREGG,
    CHARLIE_YOUNG,
    DONNA_MOSS,
    MANCHESTER_PREP,
    ROSSLYN_ACADEMY,
    HARTSFIELD_LANDING,
)


# ---------------------------------------------------------------------------
# Fixture HTML builders
# ---------------------------------------------------------------------------

def _build_tab_sheet_html(
    grouping_name: str,
    round_names: list[str],
    competitor_blocks: list[str],
) -> str:
    """Build a minimal tab-grouping.php HTML page for testing."""
    round_headers = "".join(
        f"<td class='dd centered'>{r}</td>" for r in round_names
    )
    rows = "\n".join(competitor_blocks)
    return (
        "<html><body>"
        f"<span class='pagesubtitle'>{grouping_name}</span>"
        "<table class='dd'>"
        "<tr class='tableheader'>"
        "<td class='dd centered'>Competitor</td>"
        f"{round_headers}"
        "<td class='dd centered'>Totals</td>"
        "<td class='dd centered'>Results</td>"
        "</tr>"
        f"{rows}"
        "</table>"
        "</body></html>"
    )


def _team_row(
    comp_id: int,
    name: str,
    round_cells: list[str],
    record: str,
    total_points: str,
    placement: str,
) -> str:
    """Build a team/competitor row."""
    cells = "".join(f"<td class='dd centered'>{c}</td>" for c in round_cells)
    return (
        "<tr>"
        f"<td class='dd centered'><strong>"
        f"<a href='view-comp.php?compid={comp_id}'>{name}</a>"
        f"</strong></td>"
        f"{cells}"
        f"<td rowspan='1' class='dd centered'><strong>{record}</strong>"
        f"<br /><span style='font-size: 10px;'>{total_points}</span></td>"
        f"<td rowspan='1' class='dd centered'><strong>{placement}</strong></td>"
        "</tr>"
    )


def _speaker_row(
    name: str,
    round_scores: list[str],
    total: str,
    placement: str,
) -> str:
    """Build a speaker row."""
    cells = "".join(f"<td class='dd centered'>{s}</td>" for s in round_scores)
    return (
        "<tr>"
        f"<td class='dd centered'>{name}</td>"
        f"{cells}"
        f"<td class='dd centered'>{total}</td>"
        f"<td class='dd centered'>{placement}</td>"
        "</tr>"
    )


def _win_cell(opponent: str, side: str, judge_num: int, judge_name: str) -> str:
    return (
        f"<strong>W</strong> - {opponent} - {side}"
        f"<br /><span style='font-size: 10px;'>{judge_num} {judge_name}</span>"
    )


def _loss_cell(opponent: str, side: str, judge_num: int, judge_name: str) -> str:
    return (
        f"<strong>L</strong> - {opponent} - {side}"
        f"<br /><span style='font-size: 10px;'>{judge_num} {judge_name}</span>"
    )


def _bye_cell() -> str:
    return "<strong>BYE</strong>&nbsp;"


def _forfeit_cell() -> str:
    return "<strong>FORFEIT</strong>"


def _empty_cell() -> str:
    return "&nbsp;"


# ---------------------------------------------------------------------------
# Full fixture: two teams, two rounds
# ---------------------------------------------------------------------------

SAMPLE_HTML = _build_tab_sheet_html(
    grouping_name="Varsity Policy Debate",
    round_names=["Round 1", "Round 2"],
    competitor_blocks=[
        _team_row(
            comp_id=42,
            name=f"{MANCHESTER_PREP} BALY",
            round_cells=[
                _win_cell(f"{ROSSLYN_ACADEMY} LYSE", "AFF", 5, JED_BARTLET),
                _win_cell(f"{HARTSFIELD_LANDING} CRYO", "Neg", 12, LEO_MCGARRY),
            ],
            record="2-0",
            total_points="170.5",
            placement="1st",
        ),
        _speaker_row(JOSH_LYMAN, ["29.00", "28.50"], "57.50", "3rd"),
        _speaker_row(SAM_SEABORN, ["28.50", "27.50"], "56.00", "8th"),
        _team_row(
            comp_id=99,
            name=f"{ROSSLYN_ACADEMY} LYSE",
            round_cells=[
                _loss_cell(f"{MANCHESTER_PREP} BALY", "Neg", 5, JED_BARTLET),
                _bye_cell(),
            ],
            record="1-1",
            total_points="82.0",
            placement="5th",
        ),
        _speaker_row(TOBY_ZIEGLER, ["27.00", "28.00"], "55.00", "12th"),
        _speaker_row(CJ_CREGG, ["27.00", "27.50"], "54.50", "15th"),
    ],
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_parse_tab_sheet_happy_path():
    """Full sample HTML produces two competitors with correct structure."""
    result = parse_tab_sheet_from_html(SAMPLE_HTML)

    assert result["grouping_name"] == "Varsity Policy Debate"
    assert result["round_names"] == ["Round 1", "Round 2"]
    assert len(result["competitors"]) == 2


def test_parse_tab_sheet_first_competitor():
    """First competitor has correct IDs, rounds, record, placement."""
    result = parse_tab_sheet_from_html(SAMPLE_HTML)
    comp = result["competitors"][0]

    assert comp["comp_id"] == 42
    assert comp["name"] == f"{MANCHESTER_PREP} BALY"
    assert comp["record"] == "2-0"
    assert comp["total_points"] == 170.5
    assert comp["placement"] == "1st"


def test_parse_tab_sheet_round_results():
    """Round-by-round results parse W/L with opponent, side, judge info."""
    result = parse_tab_sheet_from_html(SAMPLE_HTML)
    comp = result["competitors"][0]

    r1 = comp["rounds"][0]
    assert r1["round_number"] == 1
    assert r1["result"] == "W"
    assert r1["opponent"] == f"{ROSSLYN_ACADEMY} LYSE"
    assert r1["side"] == "AFF"
    assert r1["judge"] == JED_BARTLET
    assert r1["judge_number"] == 5

    r2 = comp["rounds"][1]
    assert r2["result"] == "W"
    assert r2["side"] == "Neg"
    assert r2["judge"] == LEO_MCGARRY
    assert r2["judge_number"] == 12


def test_parse_tab_sheet_speakers():
    """Speaker rows parse names, per-round scores, totals, and placement."""
    result = parse_tab_sheet_from_html(SAMPLE_HTML)
    comp = result["competitors"][0]

    assert len(comp["speakers"]) == 2

    s1 = comp["speakers"][0]
    assert s1["name"] == JOSH_LYMAN
    assert s1["round_scores"] == [29.0, 28.5]
    assert s1["total_points"] == 57.5
    assert s1["placement"] == "3rd"

    s2 = comp["speakers"][1]
    assert s2["name"] == SAM_SEABORN
    assert s2["round_scores"] == [28.5, 27.5]
    assert s2["total_points"] == 56.0
    assert s2["placement"] == "8th"


def test_parse_tab_sheet_bye_round():
    """BYE round is parsed correctly with no opponent/side/judge."""
    result = parse_tab_sheet_from_html(SAMPLE_HTML)
    comp = result["competitors"][1]

    r2 = comp["rounds"][1]
    assert r2["result"] == "BYE"
    assert r2["opponent"] is None
    assert r2["side"] is None
    assert r2["judge"] is None


def test_parse_tab_sheet_loss():
    """L result parses correctly with opponent and judge details."""
    result = parse_tab_sheet_from_html(SAMPLE_HTML)
    comp = result["competitors"][1]

    r1 = comp["rounds"][0]
    assert r1["result"] == "L"
    assert r1["opponent"] == f"{MANCHESTER_PREP} BALY"
    assert r1["judge"] == JED_BARTLET


def test_parse_tab_sheet_forfeit():
    """FORFEIT round is parsed correctly."""
    html = _build_tab_sheet_html(
        grouping_name="JV Lincoln-Douglas",
        round_names=["Round 1", "Round 2"],
        competitor_blocks=[
            _team_row(
                comp_id=77,
                name=f"{HARTSFIELD_LANDING} DOYO",
                round_cells=[
                    _win_cell(f"{MANCHESTER_PREP} BALY", "AFF", 3, DONNA_MOSS),
                    _forfeit_cell(),
                ],
                record="1-1",
                total_points="55.0",
                placement="10th",
            ),
            _speaker_row(CHARLIE_YOUNG, ["28.00", "&nbsp;"], "28.00", "20th"),
        ],
    )
    result = parse_tab_sheet_from_html(html)
    comp = result["competitors"][0]

    r2 = comp["rounds"][1]
    assert r2["result"] == "FORFEIT"
    assert r2["opponent"] is None

    # Speaker with empty round score
    spk = comp["speakers"][0]
    assert spk["round_scores"][1] is None


def test_parse_tab_sheet_empty_round_cell():
    """Empty round cell (no result at all) returns None for all fields."""
    html = _build_tab_sheet_html(
        grouping_name="Novice Debate",
        round_names=["Round 1", "Round 2"],
        competitor_blocks=[
            _team_row(
                comp_id=50,
                name=f"{ROSSLYN_ACADEMY} HABA",
                round_cells=[
                    _win_cell(f"{MANCHESTER_PREP} BALY", "Neg", 1, DONNA_MOSS),
                    _empty_cell(),
                ],
                record="1-0",
                total_points="55.0",
                placement="15th",
            ),
            _speaker_row(JOSH_LYMAN, ["28.00", "&nbsp;"], "28.00", "30th"),
        ],
    )
    result = parse_tab_sheet_from_html(html)
    comp = result["competitors"][0]

    r2 = comp["rounds"][1]
    assert r2["result"] is None
    assert r2["opponent"] is None


def test_parse_tab_sheet_three_rounds():
    """Parser handles three-round tournaments correctly."""
    html = _build_tab_sheet_html(
        grouping_name="Varsity Policy Debate",
        round_names=["Round 1", "Round 2", "Round 3"],
        competitor_blocks=[
            _team_row(
                comp_id=10,
                name=f"{MANCHESTER_PREP} BALY",
                round_cells=[
                    _win_cell(f"{ROSSLYN_ACADEMY} LYSE", "AFF", 1, JED_BARTLET),
                    _loss_cell(f"{HARTSFIELD_LANDING} CRYO", "Neg", 2, LEO_MCGARRY),
                    _bye_cell(),
                ],
                record="2-1",
                total_points="165.0",
                placement="3rd",
            ),
            _speaker_row(JOSH_LYMAN, ["29.00", "27.00", "28.00"], "84.00", "5th"),
            _speaker_row(SAM_SEABORN, ["28.00", "26.00", "27.00"], "81.00", "10th"),
        ],
    )
    result = parse_tab_sheet_from_html(html)

    assert result["round_names"] == ["Round 1", "Round 2", "Round 3"]
    comp = result["competitors"][0]
    assert len(comp["rounds"]) == 3
    assert comp["rounds"][0]["result"] == "W"
    assert comp["rounds"][1]["result"] == "L"
    assert comp["rounds"][2]["result"] == "BYE"

    assert len(comp["speakers"]) == 2
    assert comp["speakers"][0]["round_scores"] == [29.0, 27.0, 28.0]


def test_parse_tab_sheet_empty_html():
    """Empty HTML returns empty structure."""
    result = parse_tab_sheet_from_html("")
    assert result["grouping_name"] == ""
    assert result["round_names"] == []
    assert result["competitors"] == []


def test_parse_tab_sheet_no_table():
    """HTML without a results table returns empty competitors."""
    html = "<html><body><p>Nothing here</p></body></html>"
    result = parse_tab_sheet_from_html(html)
    assert result["competitors"] == []


def test_parse_tab_sheet_real_page_structure():
    """Parser handles the full page structure from the actual SpeechWire site."""
    # Minimal reproduction of the real page structure with wrapper elements
    html = (
        "<!DOCTYPE html><html><head><title>SpeechWire</title></head><body>"
        "<p class='pagetitle'>Grouping tab sheet</p>"
        "<form name='form1' method='get' action='tab-grouping.php'>"
        "<select id='groupingid' name='groupingid'>"
        "<option selected value='4'>Novice Debate</option>"
        "</select></form>"
        "<p><span class='pagesubtitle'>Novice Debate</span></p>"
        "<table class='dd'>"
        "<tr class='tableheader'>"
        "<td class='dd centered'>Competitor</td>"
        "<td class='dd centered'>Round 1</td>"
        "<td class='dd centered'>Totals</td>"
        "<td class='dd centered'>Results</td>"
        "</tr>"
        "<tr><td class='dd centered'><strong>"
        f"<a href='view-comp.php?compid=100'>{MANCHESTER_PREP} BALY</a>"
        "</strong></td>"
        "<td class='dd centered'><strong>BYE</strong>&nbsp;</td>"
        "<td rowspan='1' class='dd centered'><strong>1-0</strong>"
        "<br /><span style='font-size: 10px;'>56.0</span></td>"
        "<td rowspan='1' class='dd centered'><strong>1st</strong></td>"
        "</tr>"
        f"<tr><td class='dd centered'>{JOSH_LYMAN}</td>"
        "<td class='dd centered'>28.00</td>"
        "<td class='dd centered'>28.00</td>"
        "<td class='dd centered'>1st</td></tr>"
        "</table>"
        "</body></html>"
    )
    result = parse_tab_sheet_from_html(html)

    assert result["grouping_name"] == "Novice Debate"
    assert result["round_names"] == ["Round 1"]
    assert len(result["competitors"]) == 1

    comp = result["competitors"][0]
    assert comp["comp_id"] == 100
    assert comp["record"] == "1-0"
    assert comp["total_points"] == 56.0
    assert comp["placement"] == "1st"
    assert comp["rounds"][0]["result"] == "BYE"
    assert comp["speakers"][0]["name"] == JOSH_LYMAN
