from speechwire_mcp.teams.parsers import (
    parse_team_list_html,
    parse_team_entries_html,
    parse_hybrid_entries_html,
)

from fake_data import (
    ABBEY_BARTLET,
    ANDREA_WYATT,
    ANNABETH_SCHOTT,
    ARNOLD_VINICK,
    BAILEY_HS,
    BARTLET_MIDDLE,
    BOB_RUSSELL,
    BRAM_HOWARD,
    BRUNO_GIANELLI,
    CREGG_MS,
    DEBBIE_FIDERER,
    ELLIE_BARTLET,
    GLEN_WALKEN,
    HAFFLEY_HS,
    HOLLIS_ACADEMY,
    JOSH_LYMAN,
    KATE_HARPER,
    LOU_THORNTON,
    LYMAN_HS,
    LYMAN_MS,
    MALLORY_OBRIEN,
    MANCHESTER_PREP,
    MANDY_HAMPTON,
    MARGARET_HOOPER,
    MATT_SANTOS,
    NANCY_MCNALLY,
    NASHUA_PREP,
    POTOMAC_ACADEMY,
    RITCHIE_HS,
    RONNA_BECKMAN,
    RON_BUTTERFIELD,
    RUSSELL_HS,
    SAGAMORE_PREP,
    SAM_SEABORN,
    SEABORN_HS,
    SANTOS_ACADEMY,
    SANTOS_HS,
    STACKHOUSE_ACADEMY,
    TOBY_ZIEGLER,
    VINICK_ACADEMY,
    WALKEN_HS,
    ZOEY_BARTLET,
)


# ---------------------------------------------------------------------------
# Team List Parser Tests
# ---------------------------------------------------------------------------

BASIC_TEAM_LIST_HTML = f"""
<table class="dd">
<tr class="tableheader"><td>Team name</td><td>Code</td><td>Invited?</td><td>Attending?</td><td>Checked in?(click to toggle)</td><td>Entries</td><td>Judges</td><td>Results</td><td>UDL member?</td></tr>
<tr><td><a href="teams-manage.php?teamid=69">{POTOMAC_ACADEMY}</a></td><td></td><td>Yes</td><td>Yes</td><td><a href="teams-list.php?mode=updatecheckin&amp;setcheckin=0&amp;checkinteamid=69">YES</a></td><td><input type="button" value="Entries" /></td><td><input type="button" value="Judges" /></td><td><input type="button" value="Results" /></td><td>Yes</td></tr>
<tr><td><a href="teams-manage.php?teamid=22">{NASHUA_PREP}</a></td><td>AD</td><td>Yes</td><td>No</td><td>NO</td><td><input type="button" value="Entries" /></td><td><input type="button" value="Judges" /></td><td><input type="button" value="Results" /></td><td>No</td></tr>
<tr><td><a href="teams-manage.php?teamid=105">{HOLLIS_ACADEMY}</a></td><td>BCC</td><td>Yes</td><td>Yes</td><td><a href="teams-list.php?mode=updatecheckin&amp;setcheckin=0&amp;checkinteamid=105">YES</a></td><td><input type="button" value="Entries" /></td><td><input type="button" value="Judges" /></td><td><input type="button" value="Results" /></td><td>Yes</td></tr>
</table>
"""


def test_parse_team_list_basic():
    """Test basic team list parsing with multiple teams."""
    teams = parse_team_list_html(BASIC_TEAM_LIST_HTML)
    assert len(teams) == 3

    # First team - Potomac Academy
    team1 = teams[0]
    assert team1["team_id"] == 69
    assert team1["name"] == POTOMAC_ACADEMY
    assert team1["code"] is None  # empty code column
    assert team1["is_invited"] is True
    assert team1["is_attending"] is True
    assert team1["is_checked_in"] is True
    assert team1["is_udl_member"] is True

    # Second team - Nashua Prep
    team2 = teams[1]
    assert team2["team_id"] == 22
    assert team2["name"] == NASHUA_PREP
    assert team2["code"] == "AD"
    assert team2["is_invited"] is True
    assert team2["is_attending"] is False
    assert team2["is_checked_in"] is False
    assert team2["is_udl_member"] is False

    # Third team - BCC
    team3 = teams[2]
    assert team3["team_id"] == 105
    assert team3["name"] == HOLLIS_ACADEMY
    assert team3["code"] == "BCC"
    assert team3["is_invited"] is True
    assert team3["is_attending"] is True
    assert team3["is_checked_in"] is True
    assert team3["is_udl_member"] is True


def test_parse_team_list_empty_table():
    """Test that an empty table returns an empty list."""
    html = """
    <table class="dd">
    <tr class="tableheader"><td>Team name</td><td>Code</td><td>Invited?</td></tr>
    </table>
    """
    teams = parse_team_list_html(html)
    assert teams == []


def test_parse_team_list_no_table():
    """Test that HTML without a table.dd returns an empty list."""
    html = "<html><body><p>No teams here</p></body></html>"
    teams = parse_team_list_html(html)
    assert teams == []


def test_parse_team_list_missing_columns():
    """Test that a row with fewer than 9 columns doesn't crash."""
    html = """
    <table class="dd">
    <tr class="tableheader"><td>Team name</td></tr>
    <tr><td><a href="teams-manage.php?teamid=10">Partial Team</a></td><td></td></tr>
    </table>
    """
    teams = parse_team_list_html(html)
    # Should either return empty list or a team with default values
    if teams:
        team = teams[0]
        assert team["team_id"] == 10
        assert team["name"] == "Partial Team"
        # Default values for missing columns
        assert "is_invited" in team
        assert "is_attending" in team
        assert "is_checked_in" in team
        assert "is_udl_member" in team


def test_parse_team_list_empty_code():
    """Test that an empty code column results in None."""
    html = """
    <table class="dd">
    <tr class="tableheader"><td>Team name</td><td>Code</td><td>Invited?</td><td>Attending?</td><td>Checked in?</td><td>Entries</td><td>Judges</td><td>Results</td><td>UDL member?</td></tr>
    <tr><td><a href="teams-manage.php?teamid=50">No Code Team</a></td><td></td><td>Yes</td><td>Yes</td><td>YES</td><td><input /></td><td><input /></td><td><input /></td><td>Yes</td></tr>
    </table>
    """
    teams = parse_team_list_html(html)
    assert len(teams) == 1
    assert teams[0]["code"] is None


def test_parse_team_list_not_attending():
    """Test that 'No' in attending column sets is_attending to False."""
    html = """
    <table class="dd">
    <tr class="tableheader"><td>Team name</td><td>Code</td><td>Invited?</td><td>Attending?</td><td>Checked in?</td><td>Entries</td><td>Judges</td><td>Results</td><td>UDL member?</td></tr>
    <tr><td><a href="teams-manage.php?teamid=30">Not Attending</a></td><td>NA</td><td>Yes</td><td>No</td><td>NO</td><td><input /></td><td><input /></td><td><input /></td><td>Yes</td></tr>
    </table>
    """
    teams = parse_team_list_html(html)
    assert len(teams) == 1
    assert teams[0]["is_attending"] is False


def test_parse_team_list_not_checked_in():
    """Test that 'NO' in checked-in column sets is_checked_in to False."""
    html = """
    <table class="dd">
    <tr class="tableheader"><td>Team name</td><td>Code</td><td>Invited?</td><td>Attending?</td><td>Checked in?</td><td>Entries</td><td>Judges</td><td>Results</td><td>UDL member?</td></tr>
    <tr><td><a href="teams-manage.php?teamid=40">Not Checked In</a></td><td>NCI</td><td>Yes</td><td>Yes</td><td>NO</td><td><input /></td><td><input /></td><td><input /></td><td>Yes</td></tr>
    </table>
    """
    teams = parse_team_list_html(html)
    assert len(teams) == 1
    assert teams[0]["is_checked_in"] is False


def test_parse_team_list_not_udl_member():
    """Test that 'No' in UDL column sets is_udl_member to False."""
    html = """
    <table class="dd">
    <tr class="tableheader"><td>Team name</td><td>Code</td><td>Invited?</td><td>Attending?</td><td>Checked in?</td><td>Entries</td><td>Judges</td><td>Results</td><td>UDL member?</td></tr>
    <tr><td><a href="teams-manage.php?teamid=60">Not UDL</a></td><td>NUDL</td><td>Yes</td><td>Yes</td><td>YES</td><td><input /></td><td><input /></td><td><input /></td><td>No</td></tr>
    </table>
    """
    teams = parse_team_list_html(html)
    assert len(teams) == 1
    assert teams[0]["is_udl_member"] is False


def test_parse_team_list_not_invited():
    """Test that 'No' in invited column sets is_invited to False."""
    html = """
    <table class="dd">
    <tr class="tableheader"><td>Team name</td><td>Code</td><td>Invited?</td><td>Attending?</td><td>Checked in?</td><td>Entries</td><td>Judges</td><td>Results</td><td>UDL member?</td></tr>
    <tr><td><a href="teams-manage.php?teamid=80">Not Invited</a></td><td>NI</td><td>No</td><td>Yes</td><td>YES</td><td><input /></td><td><input /></td><td><input /></td><td>Yes</td></tr>
    </table>
    """
    teams = parse_team_list_html(html)
    assert len(teams) == 1
    assert teams[0]["is_invited"] is False


def test_parse_team_list_missing_team_id_link():
    """Test that a team without an anchor tag is skipped or has None team_id."""
    html = """
    <table class="dd">
    <tr class="tableheader"><td>Team name</td><td>Code</td><td>Invited?</td><td>Attending?</td><td>Checked in?</td><td>Entries</td><td>Judges</td><td>Results</td><td>UDL member?</td></tr>
    <tr><td>No Link Team</td><td>NLT</td><td>Yes</td><td>Yes</td><td>YES</td><td><input /></td><td><input /></td><td><input /></td><td>Yes</td></tr>
    </table>
    """
    teams = parse_team_list_html(html)
    # Parser should either skip this row or include it with team_id=None
    # Based on judge parser pattern, likely skipped
    assert teams == [] or (len(teams) == 1 and teams[0]["team_id"] is None)


# ---------------------------------------------------------------------------
# Team Entries Parser Tests
# ---------------------------------------------------------------------------

BASIC_ENTRIES_HTML = f"""
<form name="form1" action="teams-entries.php">
<input type="hidden" name="mode" value="update" />
<input type="hidden" name="teamid" value="69" />
<div class="sectiontitle">Policy Debate (Varsity/JV)</div>
<div>
Potomac Aca AyCl:
<select name="oldcompinput[88][1][1]"><option value="804093" selected="selected">{ABBEY_BARTLET}</option><option value="797976">{ZOEY_BARTLET}</option></select>
<select name="oldcompinput[88][1][2]"><option value="804093">{ABBEY_BARTLET}</option><option value="797976" selected="selected">{ZOEY_BARTLET}</option></select>
<select name="olddivinput[88][1]"><option value="1" selected="selected">Varsity</option><option value="3">JV</option></select>
<select name="oldcompdrop[88][1]"><option value="0" selected="selected"></option><option value="1">Drop</option></select>
</div>
<div>
Potomac Aca IsAd:
<select name="oldcompinput[88][2][1]"><option value="804096" selected="selected">{ANNABETH_SCHOTT}</option></select>
<select name="oldcompinput[88][2][2]"><option value="804097" selected="selected">{NANCY_MCNALLY}</option></select>
<select name="olddivinput[88][2]"><option value="1" selected="selected">Varsity</option></select>
<select name="oldcompdrop[88][2]"><option value="0" selected="selected"></option><option value="1">Drop</option></select>
</div>
</form>
"""


def test_parse_team_entries_basic():
    """Test basic entries parsing with multiple entries in one event."""
    entries = parse_team_entries_html(BASIC_ENTRIES_HTML)
    assert len(entries) == 2

    # First entry - AyCl
    entry1 = entries[0]
    assert entry1["event_id"] == 88
    assert entry1["event_name"] == "Policy Debate (Varsity/JV)"
    assert entry1["entry_number"] == 1
    assert entry1["entry_code"] == "Potomac Aca AyCl"
    assert len(entry1["competitors"]) == 2
    assert entry1["competitors"][0]["student_id"] == 804093
    assert entry1["competitors"][0]["name"] == ABBEY_BARTLET
    assert entry1["competitors"][0]["competitor_number"] == 1
    assert entry1["competitors"][1]["student_id"] == 797976
    assert entry1["competitors"][1]["name"] == ZOEY_BARTLET
    assert entry1["competitors"][1]["competitor_number"] == 2
    assert entry1["division"] == "Varsity"
    assert entry1["division_id"] == 1
    assert entry1["is_dropped"] is False

    # Second entry - IsAd
    entry2 = entries[1]
    assert entry2["event_id"] == 88
    assert entry2["event_name"] == "Policy Debate (Varsity/JV)"
    assert entry2["entry_number"] == 2
    assert entry2["entry_code"] == "Potomac Aca IsAd"
    assert len(entry2["competitors"]) == 2
    assert entry2["competitors"][0]["student_id"] == 804096
    assert entry2["competitors"][0]["name"] == ANNABETH_SCHOTT
    assert entry2["competitors"][1]["student_id"] == 804097
    assert entry2["competitors"][1]["name"] == NANCY_MCNALLY
    assert entry2["division"] == "Varsity"
    assert entry2["division_id"] == 1
    assert entry2["is_dropped"] is False


def test_parse_team_entries_multiple_events():
    """Test entries from different events."""
    html = f"""
    <form name="form1" action="teams-entries.php">
    <input type="hidden" name="teamid" value="10" />
    <div class="sectiontitle">Lincoln-Douglas Debate (Varsity)</div>
    <div>
    School ABC Jo:
    <select name="oldcompinput[50][1][1]"><option value="100" selected="selected">John Doe</option></select>
    <select name="olddivinput[50][1]"><option value="1" selected="selected">Varsity</option></select>
    <select name="oldcompdrop[50][1]"><option value="0" selected="selected"></option></select>
    </div>
    <div class="sectiontitle">Original Oratory (Open)</div>
    <div>
    School ABC Sa:
    <select name="oldcompinput[60][1][1]"><option value="200" selected="selected">{DEBBIE_FIDERER}</option></select>
    <select name="olddivinput[60][1]"><option value="2" selected="selected">Open</option></select>
    <select name="oldcompdrop[60][1]"><option value="0" selected="selected"></option></select>
    </div>
    </form>
    """
    entries = parse_team_entries_html(html)
    assert len(entries) == 2
    assert entries[0]["event_id"] == 50
    assert entries[0]["event_name"] == "Lincoln-Douglas Debate (Varsity)"
    assert entries[1]["event_id"] == 60
    assert entries[1]["event_name"] == "Original Oratory (Open)"


def test_parse_team_entries_dropped():
    """Test that compdrop value of '1' sets is_dropped to True."""
    html = f"""
    <form name="form1" action="teams-entries.php">
    <input type="hidden" name="teamid" value="10" />
    <div class="sectiontitle">Congressional Debate (Varsity)</div>
    <div>
    School XYZ Ma:
    <select name="oldcompinput[70][1][1]"><option value="300" selected="selected">{MARGARET_HOOPER}</option></select>
    <select name="olddivinput[70][1]"><option value="1" selected="selected">Varsity</option></select>
    <select name="oldcompdrop[70][1]"><option value="1" selected="selected">Drop</option></select>
    </div>
    </form>
    """
    entries = parse_team_entries_html(html)
    assert len(entries) == 1
    assert entries[0]["is_dropped"] is True


def test_parse_team_entries_empty_form():
    """Test that a form with no entry selects returns an empty list."""
    html = """
    <form name="form1" action="teams-entries.php">
    <input type="hidden" name="teamid" value="10" />
    <p>No entries yet</p>
    </form>
    """
    entries = parse_team_entries_html(html)
    assert entries == []


def test_parse_team_entries_no_form():
    """Test that HTML without form1 returns an empty list."""
    html = "<html><body><p>No form here</p></body></html>"
    entries = parse_team_entries_html(html)
    assert entries == []


def test_parse_team_entries_single_competitor():
    """Test an event with single competitor per entry (not a duo)."""
    html = f"""
    <form name="form1" action="teams-entries.php">
    <input type="hidden" name="teamid" value="10" />
    <div class="sectiontitle">Impromptu Speaking (JV)</div>
    <div>
    School DEF Ka:
    <select name="oldcompinput[75][1][1]"><option value="400" selected="selected">{ANDREA_WYATT}</option></select>
    <select name="olddivinput[75][1]"><option value="3" selected="selected">JV</option></select>
    <select name="oldcompdrop[75][1]"><option value="0" selected="selected"></option></select>
    </div>
    </form>
    """
    entries = parse_team_entries_html(html)
    assert len(entries) == 1
    assert len(entries[0]["competitors"]) == 1
    assert entries[0]["competitors"][0]["student_id"] == 400
    assert entries[0]["competitors"][0]["name"] == ANDREA_WYATT
    assert entries[0]["competitors"][0]["competitor_number"] == 1


def test_parse_team_entries_entry_code_extraction():
    """Test that entry code (full prefix with team and code) is correctly extracted."""
    html = f"""
    <form name="form1" action="teams-entries.php">
    <input type="hidden" name="teamid" value="10" />
    <div class="sectiontitle">Public Forum Debate (Varsity)</div>
    <div>
    {SEABORN_HS} AbCd:
    <select name="oldcompinput[80][1][1]"><option value="500" selected="selected">{ELLIE_BARTLET}</option></select>
    <select name="oldcompinput[80][1][2]"><option value="501" selected="selected">{ARNOLD_VINICK}</option></select>
    <select name="olddivinput[80][1]"><option value="1" selected="selected">Varsity</option></select>
    <select name="oldcompdrop[80][1]"><option value="0" selected="selected"></option></select>
    </div>
    </form>
    """
    entries = parse_team_entries_html(html)
    assert len(entries) == 1
    assert entries[0]["entry_code"] == f"{SEABORN_HS} AbCd"


def test_parse_team_entries_event_name_from_section_title():
    """Test that event name is correctly associated with entries."""
    html = f"""
    <form name="form1" action="teams-entries.php">
    <input type="hidden" name="teamid" value="10" />
    <div class="sectiontitle">Dramatic Interpretation (Open)</div>
    <div>
    {LYMAN_MS} Em:
    <select name="oldcompinput[90][1][1]"><option value="600" selected="selected">{MANDY_HAMPTON}</option></select>
    <select name="olddivinput[90][1]"><option value="2" selected="selected">Open</option></select>
    <select name="oldcompdrop[90][1]"><option value="0" selected="selected"></option></select>
    </div>
    <div>
    {LYMAN_MS} Li:
    <select name="oldcompinput[90][2][1]"><option value="601" selected="selected">{BOB_RUSSELL}</option></select>
    <select name="olddivinput[90][2]"><option value="2" selected="selected">Open</option></select>
    <select name="oldcompdrop[90][2]"><option value="0" selected="selected"></option></select>
    </div>
    </form>
    """
    entries = parse_team_entries_html(html)
    assert len(entries) == 2
    assert entries[0]["event_name"] == "Dramatic Interpretation (Open)"
    assert entries[1]["event_name"] == "Dramatic Interpretation (Open)"


def test_parse_team_entries_division_parsing():
    """Test that division text and ID are correctly extracted."""
    html = f"""
    <form name="form1" action="teams-entries.php">
    <input type="hidden" name="teamid" value="10" />
    <div class="sectiontitle">Extemp Speaking (JV)</div>
    <div>
    School GHI No:
    <select name="oldcompinput[95][1][1]"><option value="700" selected="selected">{GLEN_WALKEN}</option></select>
    <select name="olddivinput[95][1]">
        <option value="1">Varsity</option>
        <option value="3" selected="selected">JV</option>
        <option value="4">Novice</option>
    </select>
    <select name="oldcompdrop[95][1]"><option value="0" selected="selected"></option></select>
    </div>
    </form>
    """
    entries = parse_team_entries_html(html)
    assert len(entries) == 1
    assert entries[0]["division"] == "JV"
    assert entries[0]["division_id"] == 3


def test_parse_team_entries_no_division():
    """Test handling of entry without a division select."""
    html = f"""
    <form name="form1" action="teams-entries.php">
    <input type="hidden" name="teamid" value="10" />
    <div class="sectiontitle">Some Event</div>
    <div>
    School JKL Ol:
    <select name="oldcompinput[100][1][1]"><option value="800" selected="selected">{LOU_THORNTON}</option></select>
    <select name="oldcompdrop[100][1]"><option value="0" selected="selected"></option></select>
    </div>
    </form>
    """
    entries = parse_team_entries_html(html)
    # Should either skip or have None for division fields
    if entries:
        assert entries[0]["division"] is None or entries[0]["division"] == ""
        assert entries[0]["division_id"] is None


# ---------------------------------------------------------------------------
# Hybrid Entries Parser Tests
# ---------------------------------------------------------------------------

BASIC_HYBRID_ENTRIES_HTML = f"""
<p class='pagetitle'>Hybrid entries</p>
<p class='sectiontitle'>Current hybrid entries</p>
<table class='dd'><tr class='tableheader'><td class='dd'>Event</td><td class='dd'>Division</td><td class='dd'>Students</td><td class='dd'>Code</td><td class='dd'>Edit</td><td class='dd'>Drop</td><td class='dd'>Team blocks</td></tr><tr><td class='dd'>Policy Debate</td><td class='dd'>JV</td><td class='dd'>{JOSH_LYMAN} ({MANCHESTER_PREP})<br />{MALLORY_OBRIEN} ({SAGAMORE_PREP})</td><td class='dd'>Hybrid Entries KaDu</td><td class='dd'><input type="button" value="Edit" class="subutton" onClick="window.location='teams-hybrids-edit.php?compid=158'"></td><td class='dd'><input type="button" value="Drop" class="subutton" onClick="window.location='teams-hybrids.php?compid=158&mode=drop'"></td><td class='dd'>{SAGAMORE_PREP}<br />{MANCHESTER_PREP}</td></tr><tr class = 'tar'><td class='dd'>Policy Debate</td><td class='dd'>Rookie</td><td class='dd'>{SAM_SEABORN} ({STACKHOUSE_ACADEMY})<br />{TOBY_ZIEGLER} ({SANTOS_ACADEMY})</td><td class='dd'>Hybrid Entries BrEm</td><td class='dd'><input type="button" value="Edit" class="subutton" onClick="window.location='teams-hybrids-edit.php?compid=162'"></td><td class='dd'><input type="button" value="Drop" class="subutton" onClick="window.location='teams-hybrids.php?compid=162&mode=drop'"></td><td class='dd'>{STACKHOUSE_ACADEMY}<br />{SANTOS_ACADEMY}</td></tr><tr><td class='dd'>Policy Debate</td><td class='dd'>Rookie</td><td class='dd'>{KATE_HARPER} ({BARTLET_MIDDLE})<br />{MATT_SANTOS} ({VINICK_ACADEMY})</td><td class='dd'>Hybrid Entries ScLe</td><td class='dd'><input type="button" value="Edit" class="subutton" onClick="window.location='teams-hybrids-edit.php?compid=164'"></td><td class='dd'><input type="button" value="Drop" class="subutton" onClick="window.location='teams-hybrids.php?compid=164&mode=drop'"></td><td class='dd'>{BARTLET_MIDDLE}<br />{VINICK_ACADEMY}</td></tr></table>
"""


def test_parse_hybrid_entries_basic():
    """Test basic hybrid entries parsing with multiple entries."""
    entries = parse_hybrid_entries_html(BASIC_HYBRID_ENTRIES_HTML)
    assert len(entries) == 3

    # First entry - KaDu
    entry1 = entries[0]
    assert entry1["comp_id"] == 158
    assert entry1["event"] == "Policy Debate"
    assert entry1["division"] == "JV"
    assert entry1["code"] == "Hybrid Entries KaDu"
    assert len(entry1["students"]) == 2
    assert entry1["students"][0]["name"] == JOSH_LYMAN
    assert entry1["students"][0]["school"] == MANCHESTER_PREP
    assert entry1["students"][1]["name"] == MALLORY_OBRIEN
    assert entry1["students"][1]["school"] == SAGAMORE_PREP
    assert len(entry1["team_blocks"]) == 2
    assert entry1["team_blocks"][0] == SAGAMORE_PREP
    assert entry1["team_blocks"][1] == MANCHESTER_PREP

    # Second entry - BrEm
    entry2 = entries[1]
    assert entry2["comp_id"] == 162
    assert entry2["event"] == "Policy Debate"
    assert entry2["division"] == "Rookie"
    assert entry2["code"] == "Hybrid Entries BrEm"
    assert len(entry2["students"]) == 2
    assert entry2["students"][0]["name"] == SAM_SEABORN
    assert entry2["students"][0]["school"] == STACKHOUSE_ACADEMY
    assert entry2["students"][1]["name"] == TOBY_ZIEGLER
    assert entry2["students"][1]["school"] == SANTOS_ACADEMY
    assert len(entry2["team_blocks"]) == 2
    assert entry2["team_blocks"][0] == STACKHOUSE_ACADEMY
    assert entry2["team_blocks"][1] == SANTOS_ACADEMY

    # Third entry - ScLe
    entry3 = entries[2]
    assert entry3["comp_id"] == 164
    assert entry3["event"] == "Policy Debate"
    assert entry3["division"] == "Rookie"
    assert entry3["code"] == "Hybrid Entries ScLe"
    assert len(entry3["students"]) == 2
    assert entry3["students"][0]["name"] == KATE_HARPER
    assert entry3["students"][0]["school"] == BARTLET_MIDDLE
    assert entry3["students"][1]["name"] == MATT_SANTOS
    assert entry3["students"][1]["school"] == VINICK_ACADEMY
    assert len(entry3["team_blocks"]) == 2
    assert entry3["team_blocks"][0] == BARTLET_MIDDLE
    assert entry3["team_blocks"][1] == VINICK_ACADEMY


def test_parse_hybrid_entries_no_table():
    """Test that HTML without a table.dd returns an empty list."""
    html = "<html><body><p>No hybrid entries here</p></body></html>"
    entries = parse_hybrid_entries_html(html)
    assert entries == []


def test_parse_hybrid_entries_empty_table():
    """Test that a table with only header row returns an empty list."""
    html = """
    <table class='dd'>
    <tr class='tableheader'><td class='dd'>Event</td><td class='dd'>Division</td><td class='dd'>Students</td><td class='dd'>Code</td><td class='dd'>Edit</td><td class='dd'>Drop</td><td class='dd'>Team blocks</td></tr>
    </table>
    """
    entries = parse_hybrid_entries_html(html)
    assert entries == []


def test_parse_hybrid_entries_single_student():
    """Test entry with only one student (no <br />)."""
    html = f"""
    <table class='dd'>
    <tr class='tableheader'><td class='dd'>Event</td><td class='dd'>Division</td><td class='dd'>Students</td><td class='dd'>Code</td><td class='dd'>Edit</td><td class='dd'>Drop</td><td class='dd'>Team blocks</td></tr>
    <tr><td class='dd'>Impromptu Speaking</td><td class='dd'>Open</td><td class='dd'>{BRUNO_GIANELLI} ({LYMAN_HS})</td><td class='dd'>Hybrid Entries JoSm</td><td class='dd'><input type="button" value="Edit" class="subutton" onClick="window.location='teams-hybrids-edit.php?compid=200'"></td><td class='dd'><input type="button" value="Drop" class="subutton" onClick="window.location='teams-hybrids.php?compid=200&mode=drop'"></td><td class='dd'>{LYMAN_HS}</td></tr>
    </table>
    """
    entries = parse_hybrid_entries_html(html)
    assert len(entries) == 1
    assert entries[0]["comp_id"] == 200
    assert len(entries[0]["students"]) == 1
    assert entries[0]["students"][0]["name"] == BRUNO_GIANELLI
    assert entries[0]["students"][0]["school"] == LYMAN_HS


def test_parse_hybrid_entries_missing_school():
    """Test student without parenthesized school name."""
    html = f"""
    <table class='dd'>
    <tr class='tableheader'><td class='dd'>Event</td><td class='dd'>Division</td><td class='dd'>Students</td><td class='dd'>Code</td><td class='dd'>Edit</td><td class='dd'>Drop</td><td class='dd'>Team blocks</td></tr>
    <tr><td class='dd'>Extemp Speaking</td><td class='dd'>Varsity</td><td class='dd'>Jane Doe<br />{RON_BUTTERFIELD} ({CREGG_MS})</td><td class='dd'>Hybrid Entries JaBo</td><td class='dd'><input type="button" value="Edit" class="subutton" onClick="window.location='teams-hybrids-edit.php?compid=250'"></td><td class='dd'><input type="button" value="Drop" class="subutton" onClick="window.location='teams-hybrids.php?compid=250&mode=drop'"></td><td class='dd'>{CREGG_MS}</td></tr>
    </table>
    """
    entries = parse_hybrid_entries_html(html)
    assert len(entries) == 1
    assert len(entries[0]["students"]) == 2
    assert entries[0]["students"][0]["name"] == "Jane Doe"
    assert entries[0]["students"][0]["school"] is None
    assert entries[0]["students"][1]["name"] == RON_BUTTERFIELD
    assert entries[0]["students"][1]["school"] == CREGG_MS


def test_parse_hybrid_entries_no_edit_button():
    """Test row without an Edit button (comp_id should be None)."""
    html = f"""
    <table class='dd'>
    <tr class='tableheader'><td class='dd'>Event</td><td class='dd'>Division</td><td class='dd'>Students</td><td class='dd'>Code</td><td class='dd'>Edit</td><td class='dd'>Drop</td><td class='dd'>Team blocks</td></tr>
    <tr><td class='dd'>Congressional Debate</td><td class='dd'>JV</td><td class='dd'>{ELLIE_BARTLET} ({BAILEY_HS})<br />{ARNOLD_VINICK} ({HAFFLEY_HS})</td><td class='dd'>Hybrid Entries AlCh</td><td class='dd'></td><td class='dd'><input type="button" value="Drop" /></td><td class='dd'>{BAILEY_HS}<br />{HAFFLEY_HS}</td></tr>
    </table>
    """
    entries = parse_hybrid_entries_html(html)
    assert len(entries) == 1
    assert entries[0]["comp_id"] is None
    assert entries[0]["event"] == "Congressional Debate"
    assert entries[0]["division"] == "JV"


def test_parse_hybrid_entries_empty_division():
    """Test row with empty division cell."""
    html = f"""
    <table class='dd'>
    <tr class='tableheader'><td class='dd'>Event</td><td class='dd'>Division</td><td class='dd'>Students</td><td class='dd'>Code</td><td class='dd'>Edit</td><td class='dd'>Drop</td><td class='dd'>Team blocks</td></tr>
    <tr><td class='dd'>Original Oratory</td><td class='dd'></td><td class='dd'>{RONNA_BECKMAN} ({RITCHIE_HS})<br />{BRAM_HOWARD} ({WALKEN_HS})</td><td class='dd'>Hybrid Entries EmLi</td><td class='dd'><input type="button" value="Edit" class="subutton" onClick="window.location='teams-hybrids-edit.php?compid=300'"></td><td class='dd'><input type="button" value="Drop" /></td><td class='dd'>{RITCHIE_HS}<br />{WALKEN_HS}</td></tr>
    </table>
    """
    entries = parse_hybrid_entries_html(html)
    assert len(entries) == 1
    assert entries[0]["comp_id"] == 300
    assert entries[0]["event"] == "Original Oratory"
    assert entries[0]["division"] is None


def test_parse_hybrid_entries_empty_team_blocks():
    """Test row with no team blocks."""
    html = f"""
    <table class='dd'>
    <tr class='tableheader'><td class='dd'>Event</td><td class='dd'>Division</td><td class='dd'>Students</td><td class='dd'>Code</td><td class='dd'>Edit</td><td class='dd'>Drop</td><td class='dd'>Team blocks</td></tr>
    <tr><td class='dd'>Public Forum Debate</td><td class='dd'>Novice</td><td class='dd'>{GLEN_WALKEN} ({RUSSELL_HS})<br />{LOU_THORNTON} ({SANTOS_HS})</td><td class='dd'>Hybrid Entries NoOl</td><td class='dd'><input type="button" value="Edit" class="subutton" onClick="window.location='teams-hybrids-edit.php?compid=350'"></td><td class='dd'><input type="button" value="Drop" /></td><td class='dd'></td></tr>
    </table>
    """
    entries = parse_hybrid_entries_html(html)
    assert len(entries) == 1
    assert entries[0]["comp_id"] == 350
    assert entries[0]["event"] == "Public Forum Debate"
    assert entries[0]["division"] == "Novice"
    assert entries[0]["team_blocks"] == []
