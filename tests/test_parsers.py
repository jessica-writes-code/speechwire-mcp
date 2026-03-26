from fake_data import (
    DONNA_MOSS, MANCHESTER_PREP, ROSSLYN_ACADEMY, POTOMAC_ACADEMY, CHESAPEAKE_PREP,
)
from speechwire_mcp.judges.parsers import (
    parse_judge_edit_contact_html,
    parse_judge_list_from_html,
    parse_availability_from_edit_html,
    parse_school_from_edit_html,
)


SAMPLE_EMAIL_HTML = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>Test Judge Edit</title>
  </head>
  <body>
    <p class='pagetitle'>Edit judge</p>
    <form id="form1" name="form1" method="post" action="judges-edit.php">
      <p class='sectiontitle'>General information</p>
      <p>
        Name: <input class='swtext' id='judgename' type='text' name='judgename' value="Test Judge" size='30' maxlength='50'>
        Email address: <input class='swtext' id='judgeemail' type='text' name='judgeemail' value="test.user@example.org" size='30' maxlength='50'>
      </p>
    </form>
  </body>
</html>
"""


def test_parse_judge_edit_contact_html_prefers_input_value():
    parsed = parse_judge_edit_contact_html(SAMPLE_EMAIL_HTML)
    assert parsed["email"] == "test.user@example.org"


def test_parse_availability_basic():
    html = """
    <p class="sectiontitle">Availability by timeslot</p>
    <table class="dd">
      <tr class="tableheader">
        <td>Sat. 9:00 AM</td>
        <td>Sat. 10:45 AM</td>
        <td>Sat. 1:30 PM</td>
        <td>Sat. 3:30 PM</td>
      </tr>
      <tr>
        <td><input type="checkbox" name="slotunblock[1]" checked></td>
        <td><input type="checkbox" name="slotunblock[2]"></td>
        <td><input type="checkbox" name="slotunblock[3]" checked></td>
        <td><input type="checkbox" name="slotunblock[4]"></td>
      </tr>
    </table>
    """
    av = parse_availability_from_edit_html(html)
    assert isinstance(av, list)
    assert len(av) == 4
    assert av[0]["slot_index"] == 1 and av[0]["available"] is True and "9:00" in av[0]["label"]
    assert av[1]["slot_index"] == 2 and av[1]["available"] is False and "10:45" in av[1]["label"]
    assert av[2]["slot_index"] == 3 and av[2]["available"] is True and "1:30" in av[2]["label"]
    assert av[3]["slot_index"] == 4 and av[3]["available"] is False and "3:30" in av[3]["label"]


# ---------------------------------------------------------------------------
# Judge List (enriched) Tests
# ---------------------------------------------------------------------------

def _make_judge_row(
    judgeid=1,
    name="Test Judge",
    team="Test School",
    teamid=10,
    active_val="0",
    clean_val="0",
    priority_val="0",
    email="",
    unavail="",
    blocks=None,
    coach=False,
):
    """Build one <tr> of judge dashboard HTML."""
    coach_suffix = " (Coach)" if coach else ""
    team_cell = (
        f"<td><a href='teams-judges.php?teamid={teamid}'>{team}</a></td>"
        if team else "<td></td>"
    )
    email_cell = (
        f"<td>{email} <b><font color='green'>LINKED</font></b></td>"
        if email else "<td>&nbsp;</td>"
    )
    unavail_cell = f"<td>{unavail}</td>" if unavail else "<td></td>"
    blocks_html = "<br/>".join(blocks) if blocks else ""
    return (
        f"<tr>"
        f"<td><a href='view-judge.php?judgeid={judgeid}'>{name}</a>{coach_suffix}</td>"
        f"{team_cell}"
        f"<td></td>"  # edit button
        f"<td>N/A</td>"  # type
        f"<td><select name='judgeinactive[{judgeid}]'>"
        f"<option value='0'{' selected' if active_val == '0' else ''}>ACTIVE</option>"
        f"<option value='1'{' selected' if active_val == '1' else ''}></option>"
        f"</select></td>"
        f"<td><select name='judgeisclean[{judgeid}]'>"
        f"<option value='0'{' selected' if clean_val == '0' else ''}></option>"
        f"<option value='1'{' selected' if clean_val == '1' else ''}>CLEAN</option>"
        f"</select></td>"
        f"<td><select name='judgepriorityupd[{judgeid}]'>"
        f"<option value='0'{' selected' if priority_val == '0' else ''}></option>"
        f"<option value='1'{' selected' if priority_val == '1' else ''}>PRIORITY</option>"
        f"</select></td>"
        f"{email_cell}"
        f"{unavail_cell}"
        f"<td></td>"  # col 9: edit links
        f"<td>{blocks_html}</td>"  # col 10: blocks
        f"<td></td>"  # col 11: edit link
        f"</tr>"
    )


def _wrap_table(*rows):
    """Wrap rows in the expected table structure."""
    header = "<tr class='tableheader'><td>Name</td></tr>"
    return f"<table class='dd'>{header}{''.join(rows)}</table>"


def test_judge_list_happy_path():
    html = _wrap_table(_make_judge_row(
        judgeid=42, name="Jane Doe", team="Chesapeake Prep", teamid=7,
        active_val="0", clean_val="1", priority_val="1",
        email="jane@example.com", unavail="Sat., 8:00 AM-5:00 PM",
        blocks=["GROUPING: Varsity Policy Debate", "GROUPING: JV Policy Debate"],
    ))
    records = parse_judge_list_from_html(html)
    assert len(records) == 1
    r = records[0]
    assert r["judgeid"] == 42
    assert r["name"] == "Jane Doe"
    assert r["team"] == CHESAPEAKE_PREP
    assert r["team_id"] == 7
    assert r["is_active"] is True
    assert r["is_clean"] is True
    assert r["is_priority"] is True
    assert r["unavailability"] == "Sat., 8:00 AM-5:00 PM"
    assert r["blocks"] == ["GROUPING: Varsity Policy Debate", "GROUPING: JV Policy Debate"]
    assert r["is_coach"] is False


def test_judge_list_inactive_judge():
    html = _wrap_table(_make_judge_row(judgeid=5, active_val="1"))
    r = parse_judge_list_from_html(html)[0]
    assert r["is_active"] is False


def test_judge_list_no_team():
    html = _wrap_table(_make_judge_row(team=None))
    r = parse_judge_list_from_html(html)[0]
    assert r["team"] is None
    assert r["team_id"] is None


def test_judge_list_clean_and_priority_flags():
    html = _wrap_table(_make_judge_row(clean_val="1", priority_val="1"))
    r = parse_judge_list_from_html(html)[0]
    assert r["is_clean"] is True
    assert r["is_priority"] is True


def test_judge_list_not_clean_not_priority():
    html = _wrap_table(_make_judge_row(clean_val="0", priority_val="0"))
    r = parse_judge_list_from_html(html)[0]
    assert r["is_clean"] is False
    assert r["is_priority"] is False


def test_judge_list_empty_unavailability():
    html = _wrap_table(_make_judge_row(unavail=""))
    r = parse_judge_list_from_html(html)[0]
    assert r["unavailability"] is None


def test_judge_list_unavailability_present():
    html = _wrap_table(_make_judge_row(unavail="Sun., 1:00 PM-4:00 PM"))
    r = parse_judge_list_from_html(html)[0]
    assert r["unavailability"] == "Sun., 1:00 PM-4:00 PM"


def test_judge_list_minimal_row():
    """A row with only 2 columns should still parse name/id, defaults for rest."""
    html = (
        "<table class='dd'>"
        "<tr class='tableheader'><td>Name</td></tr>"
        "<tr><td><a href='view-judge.php?judgeid=99'>Minimal</a></td><td></td></tr>"
        "</table>"
    )
    r = parse_judge_list_from_html(html)[0]
    assert r["judgeid"] == 99
    assert r["name"] == "Minimal"
    assert r["team"] is None
    assert r["team_id"] is None
    assert r["is_active"] is True  # default when no select found
    assert r["is_clean"] is False
    assert r["is_priority"] is False
    assert r["unavailability"] is None
    assert r["blocks"] == []
    assert r["is_coach"] is False


# ---------------------------------------------------------------------------
# Coach indicator tests
# ---------------------------------------------------------------------------


def test_judge_list_coach_true():
    """Judge with (Coach) indicator should have is_coach=True."""
    html = _wrap_table(_make_judge_row(judgeid=102, name="Donna Moss", coach=True))
    r = parse_judge_list_from_html(html)[0]
    assert r["is_coach"] is True
    assert r["name"] == DONNA_MOSS


def test_judge_list_coach_false():
    """Judge without (Coach) indicator should have is_coach=False."""
    html = _wrap_table(_make_judge_row(judgeid=50, name="Regular Judge", coach=False))
    r = parse_judge_list_from_html(html)[0]
    assert r["is_coach"] is False
    assert r["name"] == "Regular Judge"


def test_judge_list_mixed_coach_and_non_coach():
    """Table with both coach and non-coach judges."""
    html = _wrap_table(
        _make_judge_row(judgeid=1, name="Coach Person", coach=True),
        _make_judge_row(judgeid=2, name="Volunteer Judge", coach=False),
        _make_judge_row(judgeid=3, name="Another Coach", coach=True),
    )
    records = parse_judge_list_from_html(html)
    assert len(records) == 3
    assert records[0]["is_coach"] is True
    assert records[1]["is_coach"] is False
    assert records[2]["is_coach"] is True


def test_judge_list_backward_compat():
    """Existing judgeid/name fields must remain present and correct."""
    html = _wrap_table(_make_judge_row(judgeid=33, name="Old Name"))
    r = parse_judge_list_from_html(html)[0]
    assert "judgeid" in r and r["judgeid"] == 33
    assert "name" in r and r["name"] == "Old Name"


def test_judge_list_empty_table():
    html = "<table class='dd'><tr class='tableheader'><td>Name</td></tr></table>"
    assert parse_judge_list_from_html(html) == []


def test_judge_list_no_table():
    assert parse_judge_list_from_html("<html><body>No table</body></html>") == []


def test_judge_list_multiple_rows():
    html = _wrap_table(
        _make_judge_row(judgeid=1, name="A", active_val="0"),
        _make_judge_row(judgeid=2, name="B", active_val="1"),
    )
    records = parse_judge_list_from_html(html)
    assert len(records) == 2
    assert records[0]["judgeid"] == 1 and records[0]["is_active"] is True
    assert records[1]["judgeid"] == 2 and records[1]["is_active"] is False


def test_judge_list_blocks_multiple():
    html = _wrap_table(_make_judge_row(
        blocks=["GROUPING: Varsity Lincoln-Douglas", "GROUPING: Varsity Policy Debate"],
    ))
    r = parse_judge_list_from_html(html)[0]
    assert r["blocks"] == ["GROUPING: Varsity Lincoln-Douglas", "GROUPING: Varsity Policy Debate"]


def test_judge_list_blocks_single():
    html = _wrap_table(_make_judge_row(blocks=["TEAM: Chesapeake Prep"]))
    r = parse_judge_list_from_html(html)[0]
    assert r["blocks"] == [f"TEAM: {CHESAPEAKE_PREP}"]


def test_judge_list_blocks_empty():
    html = _wrap_table(_make_judge_row(blocks=None))
    r = parse_judge_list_from_html(html)[0]
    assert r["blocks"] == []


# ---------------------------------------------------------------------------
# School (team association) parsing tests
# ---------------------------------------------------------------------------

SAMPLE_SCHOOL_HTML = """<!DOCTYPE html>
<html><head><title>SpeechWire</title></head>
<body>
<p class='pagetitle'>Edit judge</p>
<form id="form1" name="form1" method="post" action="judges-edit.php">
<p class='sectiontitle'>General information</p>
<p>Name: <input class='swtext' id='judgename' type='text' name='judgename'
   value="Josh Lyman" size='30' maxlength='50'>
Email address: <input class='swtext' id='judgeemail' type='text' name='judgeemail'
   value="josh.lyman@example.com" size='30' maxlength='50'></p>
<p>Team: <select id='teamid' name='teamid'>
  <option value='69'>Potomac Academy</option>
  <option selected value='24'>Manchester Prep</option>
  <option value='36'>Sagamore Prep</option>
  <option value='85'>Rosslyn Academy</option>
</select></p>
</form>
</body></html>
"""


def test_parse_school_happy_path():
    result = parse_school_from_edit_html(SAMPLE_SCHOOL_HTML)
    assert result["school"] == MANCHESTER_PREP
    assert result["team_id"] == 24


def test_parse_school_first_option_selected():
    html = """
    <select id='teamid' name='teamid'>
      <option selected value='69'>Potomac Academy</option>
      <option value='24'>Manchester Prep</option>
    </select>
    """
    result = parse_school_from_edit_html(html)
    assert result["school"] == POTOMAC_ACADEMY
    assert result["team_id"] == 69


def test_parse_school_last_option_selected():
    html = """
    <select id='teamid' name='teamid'>
      <option value='69'>Potomac Academy</option>
      <option value='24'>Manchester Prep</option>
      <option selected value='85'>Rosslyn Academy</option>
    </select>
    """
    result = parse_school_from_edit_html(html)
    assert result["school"] == ROSSLYN_ACADEMY
    assert result["team_id"] == 85


def test_parse_school_no_select():
    html = "<html><body><p>No team select here</p></body></html>"
    result = parse_school_from_edit_html(html)
    assert result["school"] is None
    assert result["team_id"] is None


def test_parse_school_no_selected_option():
    html = """
    <select id='teamid' name='teamid'>
      <option value='69'>Potomac Academy</option>
      <option value='24'>Manchester Prep</option>
    </select>
    """
    result = parse_school_from_edit_html(html)
    assert result["school"] is None
    assert result["team_id"] is None


def test_parse_school_empty_html():
    result = parse_school_from_edit_html("")
    assert result["school"] is None
    assert result["team_id"] is None


def test_parse_school_name_attribute_fallback():
    """Falls back to name='teamid' when id is missing."""
    html = """
    <select name='teamid'>
      <option value='10'>Fallback School</option>
      <option selected value='20'>Selected School</option>
    </select>
    """
    result = parse_school_from_edit_html(html)
    assert result["school"] == "Selected School"
    assert result["team_id"] == 20


def test_parse_school_non_numeric_value():
    html = """
    <select id='teamid' name='teamid'>
      <option selected value='abc'>Some School</option>
    </select>
    """
    result = parse_school_from_edit_html(html)
    assert result["school"] == "Some School"
    assert result["team_id"] is None
