from speechwire_mcp.schematics.parsers import (
    parse_schematic_events_html,
    parse_round_schematic_html,
)
from fake_data import (
    AINSLEY_HAYES,
    AMY_GARDNER,
    CHARLIE_YOUNG,
    DANNY_CONCANNON,
    DONNA_MOSS,
    JOEY_LUCAS,
    SAM_SEABORN,
    TOBY_ZIEGLER,
    WILL_BAILEY,
)


# ---------------------------------------------------------------------------
# Function 1: parse_schematic_events_html Tests
# ---------------------------------------------------------------------------

SAMPLE_EVENTS_HTML = """<!DOCTYPE html>
<html>
<head><title>Schematic viewer</title></head>
<body>
<p class="pagetitle">Schematic viewer</p>
<form name="form1" method="get" action="schem-view.php">
  Please select a grouping to view the schematic for: 
  <select id='groupingid' name='groupingid'><option value='6'>Varsity Lincoln-Douglas</option><option value='3'>JV Policy Debate</option><option value='4'>Novice Restricted Packet Policy Debate</option><option value='5'>Rookie Policy Debate</option><option value='2'>Varsity Policy Debate</option></select>  <input name="Submit" type="submit" value="View schematic">
</form>
<p class='sectiontitle'>Schematic VIEWER quick access</p>
<p><a href='schem-view.php?groupingid=6'>Varsity Lincoln-Douglas</a><br /><a href='schem-view.php?groupingid=3'>JV Policy Debate</a><br /></p>
<p class='sectiontitle'>Pairings EDITOR quick access</p>
<p><b>JV Policy Debate</b><br /><a href='schem-edit.php?groupingid=3&round=3'>Round 3</a><br /><a href='schem-edit.php?groupingid=3&round=2'>Round 2</a><br /><a href='schem-edit.php?groupingid=3&round=1'>Round 1</a></p>
<p><b>Novice Restricted Packet Policy Debate</b><br /><a href='schem-edit.php?groupingid=4&round=3'>Round 3</a><br /><a href='schem-edit.php?groupingid=4&round=2'>Round 2</a><br /><a href='schem-edit.php?groupingid=4&round=1'>Round 1</a></p>
<p><b>Varsity Policy Debate</b><br /><a href='schem-edit.php?groupingid=2&round=3'>Round 3</a><br /><a href='schem-edit.php?groupingid=2&round=2'>Round 2</a><br /><a href='schem-edit.php?groupingid=2&round=1'>Round 1</a></p>
</body>
</html>
"""


def test_parse_schematic_events_happy_path():
    """Use full sample HTML. Verify all 5 events extracted with correct rounds."""
    events = parse_schematic_events_html(SAMPLE_EVENTS_HTML)
    assert len(events) == 5
    
    # Check all events by grouping_id
    events_by_id = {e["grouping_id"]: e for e in events}
    
    # JV Policy Debate (id=3) has rounds [1, 2, 3]
    assert 3 in events_by_id
    assert events_by_id[3]["name"] == "JV Policy Debate"
    assert events_by_id[3]["rounds"] == [1, 2, 3]
    
    # Novice Restricted Packet Policy Debate (id=4) has rounds [1, 2, 3]
    assert 4 in events_by_id
    assert events_by_id[4]["name"] == "Novice Restricted Packet Policy Debate"
    assert events_by_id[4]["rounds"] == [1, 2, 3]
    
    # Varsity Policy Debate (id=2) has rounds [1, 2, 3]
    assert 2 in events_by_id
    assert events_by_id[2]["name"] == "Varsity Policy Debate"
    assert events_by_id[2]["rounds"] == [1, 2, 3]
    
    # Rookie Policy Debate (id=5) has empty rounds []
    assert 5 in events_by_id
    assert events_by_id[5]["name"] == "Rookie Policy Debate"
    assert events_by_id[5]["rounds"] == []
    
    # Varsity Lincoln-Douglas (id=6) has empty rounds []
    assert 6 in events_by_id
    assert events_by_id[6]["name"] == "Varsity Lincoln-Douglas"
    assert events_by_id[6]["rounds"] == []


def test_parse_schematic_events_empty_html():
    """Pass empty string → returns []"""
    events = parse_schematic_events_html("")
    assert events == []


def test_parse_schematic_events_no_select():
    """HTML with no select element → returns []"""
    html = """<!DOCTYPE html>
    <html><body>
    <p class="pagetitle">Schematic viewer</p>
    <p>No select element here</p>
    </body></html>
    """
    events = parse_schematic_events_html(html)
    assert events == []


def test_parse_schematic_events_select_no_editor_links():
    """HTML with select but NO 'Pairings EDITOR' section → all events have empty rounds"""
    html = """<!DOCTYPE html>
    <html><body>
    <p class="pagetitle">Schematic viewer</p>
    <form name="form1" method="get" action="schem-view.php">
      <select id='groupingid' name='groupingid'>
        <option value='10'>Event A</option>
        <option value='11'>Event B</option>
      </select>
    </form>
    </body></html>
    """
    events = parse_schematic_events_html(html)
    assert len(events) == 2
    assert events[0]["grouping_id"] == 10
    assert events[0]["name"] == "Event A"
    assert events[0]["rounds"] == []
    assert events[1]["grouping_id"] == 11
    assert events[1]["name"] == "Event B"
    assert events[1]["rounds"] == []


def test_parse_schematic_events_single_event():
    """HTML with just one event and one round"""
    html = """<!DOCTYPE html>
    <html><body>
    <p class="pagetitle">Schematic viewer</p>
    <form name="form1" method="get" action="schem-view.php">
      <select id='groupingid' name='groupingid'>
        <option value='99'>Solo Event</option>
      </select>
    </form>
    <p class='sectiontitle'>Pairings EDITOR quick access</p>
    <p><b>Solo Event</b><br /><a href='schem-edit.php?groupingid=99&round=1'>Round 1</a></p>
    </body></html>
    """
    events = parse_schematic_events_html(html)
    assert len(events) == 1
    assert events[0]["grouping_id"] == 99
    assert events[0]["name"] == "Solo Event"
    assert events[0]["rounds"] == [1]


# ---------------------------------------------------------------------------
# Function 2: parse_round_schematic_html Tests
# ---------------------------------------------------------------------------

SAMPLE_ROUND_HTML = f"""<!DOCTYPE html>
<html>
<head><title>Schematic editor</title></head>
<body>
<table class="dd">
<tr class="tableheader">
  <td colspan="5">Novice Restricted Packet Policy Debate Round 3 - 3:30 PM</td>
  <td><a href='schem-edit.php?firstsectionid=0&firstjudgeid=9&groupingid=4&round=3&editorsort=normal'>{DANNY_CONCANNON} [3]</a> <a href='schem-edit.php?firstsectionid=0&firstjudgeid=15&groupingid=4&round=3&editorsort=normal'>{TOBY_ZIEGLER} [2]</a></td>
</tr>
<tr class="tableheader">
  <td>Sect.</td><td>Judge</td><td>Room</td><td colspan="2">Competitors</td>
</tr>
<tr>
  <td><a href='view-debate.php?sectionid=291'>A</a></td>
  <td><a href='schem-edit.php?firstsectionid=291&firstjudgeid=3&groupingid=4&round=3&editorsort=normal'>{JOEY_LUCAS} [3]</a> <a href='judge-detail.php?judgeid=3'>detail</a></td>
  <td><a href='rooms-section.php?sectionid=291'>Room 101</a></td>
  <td><a href='schem-edit.php?firstcompid=183&groupingid=4&round=3'>{AMY_GARDNER}</a> (AFF) (2-0)</td>
  <td><a href='schem-edit.php?firstcompid=184&groupingid=4&round=3'>{CHARLIE_YOUNG}</a> (Neg) (1-1)</td>
</tr>
<tr>
  <td><a href='view-debate.php?sectionid=292'>B</a></td>
  <td>Assign judge</td>
  <td><a href='rooms-section.php?sectionid=292'>Room 102</a></td>
  <td><a href='schem-edit.php?firstcompid=185&groupingid=4&round=3'>{AINSLEY_HAYES}</a> (AFF) (1-1)</td>
  <td><a href='schem-edit.php?firstcompid=186&groupingid=4&round=3'>{WILL_BAILEY}</a> (Neg) (0-2)</td>
</tr>
</table>
</body>
</html>
"""


def test_parse_round_schematic_happy_path():
    """Use full fixture. Verify event_name, round, time, unused_judges, sections."""
    result = parse_round_schematic_html(SAMPLE_ROUND_HTML)
    
    # Verify metadata
    assert result["event_name"] == "Novice Restricted Packet Policy Debate"
    assert result["round"] == 3
    assert result["time"] == "3:30 PM"
    
    # Verify unused judges
    assert len(result["unused_judges"]) == 2
    unused_by_id = {j["judge_id"]: j for j in result["unused_judges"]}
    assert 9 in unused_by_id
    assert unused_by_id[9]["name"] == DANNY_CONCANNON
    assert unused_by_id[9]["rounds_judged"] == 3
    assert 15 in unused_by_id
    assert unused_by_id[15]["name"] == TOBY_ZIEGLER
    assert unused_by_id[15]["rounds_judged"] == 2
    
    # Verify sections
    assert len(result["sections"]) == 2
    
    # Section A
    section_a = result["sections"][0]
    assert section_a["section_id"] == 291
    assert section_a["label"] == "A"
    assert section_a["judge"] is not None
    assert section_a["judge"]["judge_id"] == 3
    assert section_a["judge"]["name"] == JOEY_LUCAS
    assert section_a["judge"]["rounds_judged"] == 3
    assert section_a["room"] == "Room 101"
    assert len(section_a["competitors"]) == 2
    assert section_a["competitors"][0]["competitor_id"] == 183
    assert section_a["competitors"][0]["name"] == AMY_GARDNER
    assert section_a["competitors"][0]["side"] == "AFF"
    assert section_a["competitors"][0]["record"] == "2-0"
    assert section_a["competitors"][1]["competitor_id"] == 184
    assert section_a["competitors"][1]["name"] == CHARLIE_YOUNG
    assert section_a["competitors"][1]["side"] == "NEG"
    assert section_a["competitors"][1]["record"] == "1-1"
    
    # Section B
    section_b = result["sections"][1]
    assert section_b["section_id"] == 292
    assert section_b["label"] == "B"
    assert section_b["judge"] is None  # "Assign judge" case
    assert section_b["room"] == "Room 102"
    assert len(section_b["competitors"]) == 2
    assert section_b["competitors"][0]["competitor_id"] == 185
    assert section_b["competitors"][0]["name"] == AINSLEY_HAYES
    assert section_b["competitors"][0]["side"] == "AFF"
    assert section_b["competitors"][0]["record"] == "1-1"
    assert section_b["competitors"][1]["competitor_id"] == 186
    assert section_b["competitors"][1]["name"] == WILL_BAILEY
    assert section_b["competitors"][1]["side"] == "NEG"
    assert section_b["competitors"][1]["record"] == "0-2"


def test_parse_round_schematic_empty_html():
    """Pass empty string → returns {}"""
    result = parse_round_schematic_html("")
    assert result == {}


def test_parse_round_schematic_no_table():
    """HTML with no table.dd → returns {}"""
    html = """<!DOCTYPE html>
    <html><body>
    <p>No table here</p>
    </body></html>
    """
    result = parse_round_schematic_html(html)
    assert result == {}


def test_parse_round_schematic_no_judge():
    """Section with 'Assign judge' text instead of judge link → judge field is None"""
    html = f"""<!DOCTYPE html>
    <html><body>
    <table class="dd">
    <tr class="tableheader">
      <td colspan="5">Test Event Round 1 - 9:00 AM</td>
      <td></td>
    </tr>
    <tr class="tableheader">
      <td>Sect.</td><td>Judge</td><td>Room</td><td colspan="2">Competitors</td>
    </tr>
    <tr>
      <td><a href='view-debate.php?sectionid=100'>A</a></td>
      <td>Assign judge</td>
      <td><a href='rooms-section.php?sectionid=100'>Room 201</a></td>
      <td><a href='schem-edit.php?firstcompid=50&groupingid=1&round=1'>{SAM_SEABORN}</a> (AFF) (0-0)</td>
      <td><a href='schem-edit.php?firstcompid=51&groupingid=1&round=1'>{DONNA_MOSS}</a> (Neg) (0-0)</td>
    </tr>
    </table>
    </body></html>
    """
    result = parse_round_schematic_html(html)
    assert result["sections"][0]["judge"] is None


def test_parse_round_schematic_no_unused_judges():
    """Header row cell 1 is empty or missing → unused_judges is empty list"""
    html = f"""<!DOCTYPE html>
    <html><body>
    <table class="dd">
    <tr class="tableheader">
      <td colspan="5">Test Event Round 1 - 9:00 AM</td>
      <td></td>
    </tr>
    <tr class="tableheader">
      <td>Sect.</td><td>Judge</td><td>Room</td><td colspan="2">Competitors</td>
    </tr>
    <tr>
      <td><a href='view-debate.php?sectionid=100'>A</a></td>
      <td><a href='schem-edit.php?firstsectionid=100&firstjudgeid=5&groupingid=1&round=1&editorsort=normal'>Test Judge [1]</a></td>
      <td><a href='rooms-section.php?sectionid=100'>Room 201</a></td>
      <td><a href='schem-edit.php?firstcompid=50&groupingid=1&round=1'>{SAM_SEABORN}</a> (AFF) (0-0)</td>
      <td><a href='schem-edit.php?firstcompid=51&groupingid=1&round=1'>{DONNA_MOSS}</a> (Neg) (0-0)</td>
    </tr>
    </table>
    </body></html>
    """
    result = parse_round_schematic_html(html)
    assert result["unused_judges"] == []


def test_parse_round_schematic_no_time():
    """Header has 'Event Round 1' without the ' - Time' part → time is None"""
    html = f"""<!DOCTYPE html>
    <html><body>
    <table class="dd">
    <tr class="tableheader">
      <td colspan="5">Test Event Round 1</td>
      <td></td>
    </tr>
    <tr class="tableheader">
      <td>Sect.</td><td>Judge</td><td>Room</td><td colspan="2">Competitors</td>
    </tr>
    <tr>
      <td><a href='view-debate.php?sectionid=100'>A</a></td>
      <td><a href='schem-edit.php?firstsectionid=100&firstjudgeid=5&groupingid=1&round=1&editorsort=normal'>Test Judge [1]</a></td>
      <td><a href='rooms-section.php?sectionid=100'>Room 201</a></td>
      <td><a href='schem-edit.php?firstcompid=50&groupingid=1&round=1'>{SAM_SEABORN}</a> (AFF) (0-0)</td>
      <td><a href='schem-edit.php?firstcompid=51&groupingid=1&round=1'>{DONNA_MOSS}</a> (Neg) (0-0)</td>
    </tr>
    </table>
    </body></html>
    """
    result = parse_round_schematic_html(html)
    assert result["event_name"] == "Test Event"
    assert result["round"] == 1
    assert result["time"] is None


def test_parse_round_schematic_single_competitor():
    """Section with only one competitor (cell 4 missing or empty)"""
    html = f"""<!DOCTYPE html>
    <html><body>
    <table class="dd">
    <tr class="tableheader">
      <td colspan="5">Test Event Round 1 - 9:00 AM</td>
      <td></td>
    </tr>
    <tr class="tableheader">
      <td>Sect.</td><td>Judge</td><td>Room</td><td colspan="2">Competitors</td>
    </tr>
    <tr>
      <td><a href='view-debate.php?sectionid=100'>A</a></td>
      <td><a href='schem-edit.php?firstsectionid=100&firstjudgeid=5&groupingid=1&round=1&editorsort=normal'>Test Judge [1]</a></td>
      <td><a href='rooms-section.php?sectionid=100'>Room 201</a></td>
      <td><a href='schem-edit.php?firstcompid=50&groupingid=1&round=1'>{SAM_SEABORN}</a> (AFF) (0-0)</td>
      <td></td>
    </tr>
    </table>
    </body></html>
    """
    result = parse_round_schematic_html(html)
    assert len(result["sections"]) == 1
    assert len(result["sections"][0]["competitors"]) == 1
    assert result["sections"][0]["competitors"][0]["name"] == SAM_SEABORN
