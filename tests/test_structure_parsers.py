"""Tests for speechwire_mcp.structure.parsers — timeslot & groupings parsers.

Written alongside the implementation using a TDD-ready pattern.
Tests define the contract for parse_timeslots_from_html and
parse_groupings_from_html.
"""

from speechwire_mcp.structure.parsers import (
    parse_groupings_from_html,
    parse_timeslots_from_html,
)


# ---------------------------------------------------------------------------
# Timeslot Parser Tests
# ---------------------------------------------------------------------------

SAMPLE_TIMESLOTS_HTML = (
    "<form name='form2' method='post' action='slots-list.php'>"
    "<table class='dd'>"
    "<tr class='tablemajorheader'>"
    "<td class='dd centered' colspan='7'>Mar. 21, 2026</td>"
    "</tr>"
    "<tr class='tableheader'>"
    "<td class='dd centered'>&nbsp;</td>"
    "<td class='dd centered'>EVT-A</td>"
    "<td class='dd centered'>EVT-B</td>"
    "<td class='dd centered'>EVT-C</td>"
    "<td class='dd centered'>EVT-D</td>"
    "<td class='dd centered'>EVT-E</td>"
    "<td class='dd centered'>&nbsp;</td>"
    "</tr>"
    # --- Slot 1: 9:00 AM ---
    "<tr>"
    "<td class='dd centered' rowspan='2'>"
    "<strong><a href='slots-edit.php?slotid=1'>9:00 AM</a></strong>"
    "</td>"
    "<td class='dd centered' colspan='5'>"
    "<strong><a href='slots-edit.php?slotid=1'>Round 1 / Novice Workshops</a></strong>"
    "</td>"
    "<td class='dd centered' rowspan='2'>"
    "<strong><a href='slots-edit.php?slotid=1'>9:00 AM</a></strong>"
    "</td>"
    "</tr>"
    "<tr>"
    "<td class='dd centered'><select id='roundassign[1][6]' name='roundassign[1][6]'>"
    "<option value='0'> </option>"
    "<option selected value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "</select></td>"
    "<td class='dd centered'><select id='roundassign[1][3]' name='roundassign[1][3]'>"
    "<option value='0'> </option>"
    "<option selected value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "<option value='4-1'>Rd. 4</option>"
    "</select></td>"
    "<td class='dd centered'><select id='roundassign[1][4]' name='roundassign[1][4]'>"
    "<option value='0'> </option>"
    "<option selected value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "<option value='4-1'>Rd. 4</option>"
    "</select></td>"
    "<td class='dd centered'><select id='roundassign[1][5]' name='roundassign[1][5]'>"
    "<option value='0'> </option>"
    "<option selected value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "<option value='4-1'>Rd. 4</option>"
    "</select></td>"
    "<td class='dd centered'><select id='roundassign[1][2]' name='roundassign[1][2]'>"
    "<option value='0'> </option>"
    "<option selected value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "<option value='4-1'>Rd. 4</option>"
    "</select></td>"
    "</tr>"
    # --- Slot 4: 3:30 PM ---
    "<tr class='tar'>"
    "<td class='dd centered' rowspan='2'>"
    "<strong><a href='slots-edit.php?slotid=4'>3:30 PM</a></strong>"
    "</td>"
    "<td class='dd centered' colspan='5'>"
    "<strong><a href='slots-edit.php?slotid=4'>"
    "Round 4 (Varsity / JV), Round 3 (Novice / Rookie)"
    "</a></strong>"
    "</td>"
    "<td class='dd centered' rowspan='2'>"
    "<strong><a href='slots-edit.php?slotid=4'>3:30 PM</a></strong>"
    "</td>"
    "</tr>"
    "<tr class='tar'>"
    "<td class='dd centered'><select id='roundassign[4][6]' name='roundassign[4][6]'>"
    "<option selected value='0'> </option>"
    "<option value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "</select></td>"
    "<td class='dd centered'><select id='roundassign[4][3]' name='roundassign[4][3]'>"
    "<option value='0'> </option>"
    "<option value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "<option selected value='4-1'>Rd. 4</option>"
    "</select></td>"
    "<td class='dd centered'><select id='roundassign[4][4]' name='roundassign[4][4]'>"
    "<option value='0'> </option>"
    "<option value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "<option selected value='4-1'>Rd. 4</option>"
    "</select></td>"
    "<td class='dd centered'><select id='roundassign[4][5]' name='roundassign[4][5]'>"
    "<option value='0'> </option>"
    "<option value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "<option selected value='4-1'>Rd. 4</option>"
    "</select></td>"
    "<td class='dd centered'><select id='roundassign[4][2]' name='roundassign[4][2]'>"
    "<option value='0'> </option>"
    "<option value='1-1'>Rd. 1</option>"
    "<option value='2-1'>Rd. 2</option>"
    "<option value='3-1'>Rd. 3</option>"
    "<option selected value='4-1'>Rd. 4</option>"
    "</select></td>"
    "</tr>"
    "</table>"
    "<input name='mode' id='mode' type='hidden' value='updateassigns' />"
    "</form>"
)


def test_parse_timeslots_happy_path():
    """Full sample HTML produces two timeslot records with correct fields."""
    slots = parse_timeslots_from_html(SAMPLE_TIMESLOTS_HTML)

    assert len(slots) == 2, f"Expected 2 slots, got {len(slots)}"

    # --- Slot 1: 9:00 AM ---
    s1 = slots[0]
    assert s1["slot_id"] == 1
    assert s1["time"] == "9:00 AM"
    assert s1["description"] == "Round 1 / Novice Workshops"
    assert s1["date"] == "Mar. 21, 2026"

    ra1 = s1["round_assignments"]
    assert len(ra1) == 5
    by_event_1 = {a["event_name"]: a for a in ra1}
    assert set(by_event_1.keys()) == {"EVT-A", "EVT-B", "EVT-C", "EVT-D", "EVT-E"}
    # All five events have Rd. 1 selected for slot 1
    for event_name, assignment in by_event_1.items():
        assert assignment["round_label"] == "Rd. 1", (
            f"Event '{event_name}' expected 'Rd. 1', got '{assignment['round_label']}'"
        )

    # --- Slot 4: 3:30 PM ---
    s4 = slots[1]
    assert s4["slot_id"] == 4
    assert s4["time"] == "3:30 PM"
    assert s4["description"] == "Round 4 (Varsity / JV), Round 3 (Novice / Rookie)"
    assert s4["date"] == "Mar. 21, 2026"

    ra4 = s4["round_assignments"]
    assert len(ra4) == 5
    by_event_4 = {a["event_name"]: a for a in ra4}
    # EVT-A has no round assigned (value='0' selected)
    assert by_event_4["EVT-A"]["round_label"] is None
    # Other four events have Rd. 4 selected
    for ev in ["EVT-B", "EVT-C", "EVT-D", "EVT-E"]:
        assert by_event_4[ev]["round_label"] == "Rd. 4", (
            f"Event '{ev}' expected 'Rd. 4', got '{by_event_4[ev]['round_label']}'"
        )


def test_parse_timeslots_empty_schedule():
    """Table inside form2 with only headers and no timeslot rows returns []."""
    html = (
        "<form name='form2' method='post' action='slots-list.php'>"
        "<table class='dd'>"
        "<tr class='tablemajorheader'>"
        "<td colspan='4'>Mar. 21, 2026</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td>&nbsp;</td><td>EVT-A</td><td>EVT-B</td><td>&nbsp;</td>"
        "</tr>"
        "</table></form>"
    )
    slots = parse_timeslots_from_html(html)
    assert slots == [], f"Expected empty list, got {slots}"


def test_parse_timeslots_missing_description():
    """Timeslot with no description colspan cell still parses time and slot_id."""
    html = (
        "<form name='form2' method='post' action='slots-list.php'>"
        "<table class='dd'>"
        "<tr class='tablemajorheader'>"
        "<td colspan='4'>Mar. 21, 2026</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td>&nbsp;</td><td>EVT-A</td><td>&nbsp;</td>"
        "</tr>"
        "<tr>"
        "<td rowspan='2'>"
        "<strong><a href='slots-edit.php?slotid=7'>10:00 AM</a></strong>"
        "</td>"
        "</tr>"
        "<tr>"
        "<td><select name='roundassign[7][1]'>"
        "<option selected value='0'> </option>"
        "</select></td>"
        "</tr>"
        "</table></form>"
    )
    slots = parse_timeslots_from_html(html)
    assert len(slots) == 1
    s = slots[0]
    assert s["slot_id"] == 7
    assert s["time"] == "10:00 AM"
    assert s["description"] is None
    assert s["date"] == "Mar. 21, 2026"


def test_parse_timeslots_no_round_assignments():
    """All events have value='0' selected → round_label is None for each."""
    html = (
        "<form name='form2' method='post' action='slots-list.php'>"
        "<table class='dd'>"
        "<tr class='tablemajorheader'>"
        "<td colspan='5'>Mar. 22, 2026</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td>&nbsp;</td><td>LD</td><td>PF</td><td>&nbsp;</td>"
        "</tr>"
        "<tr>"
        "<td rowspan='2'>"
        "<strong><a href='slots-edit.php?slotid=10'>8:00 AM</a></strong>"
        "</td>"
        "<td colspan='2'>"
        "<strong><a href='slots-edit.php?slotid=10'>Placeholder Round</a></strong>"
        "</td>"
        "<td rowspan='2'>"
        "<strong><a href='slots-edit.php?slotid=10'>8:00 AM</a></strong>"
        "</td>"
        "</tr>"
        "<tr>"
        "<td><select name='roundassign[10][1]'>"
        "<option selected value='0'> </option>"
        "<option value='1-1'>Rd. 1</option>"
        "</select></td>"
        "<td><select name='roundassign[10][2]'>"
        "<option selected value='0'> </option>"
        "<option value='1-1'>Rd. 1</option>"
        "</select></td>"
        "</tr>"
        "</table></form>"
    )
    slots = parse_timeslots_from_html(html)
    assert len(slots) == 1
    s = slots[0]
    assert s["slot_id"] == 10
    assert s["description"] == "Placeholder Round"

    for ra in s["round_assignments"]:
        assert ra["round_label"] is None, (
            f"Event '{ra['event_name']}' should have round_label=None"
        )


def test_parse_timeslots_multiple_dates():
    """Schedule spanning two days produces slots with correct date per day."""
    html = (
        "<form name='form2' method='post' action='slots-list.php'>"
        "<table class='dd'>"
        # --- Day 1 ---
        "<tr class='tablemajorheader'>"
        "<td colspan='4'>Mar. 21, 2026</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td>&nbsp;</td><td>LD</td><td>&nbsp;</td>"
        "</tr>"
        "<tr>"
        "<td rowspan='2'>"
        "<strong><a href='slots-edit.php?slotid=1'>9:00 AM</a></strong>"
        "</td>"
        "<td colspan='1'>"
        "<strong><a href='slots-edit.php?slotid=1'>Day 1 Round 1</a></strong>"
        "</td>"
        "<td rowspan='2'>"
        "<strong><a href='slots-edit.php?slotid=1'>9:00 AM</a></strong>"
        "</td>"
        "</tr>"
        "<tr>"
        "<td><select name='roundassign[1][1]'>"
        "<option value='0'> </option>"
        "<option selected value='1-1'>Rd. 1</option>"
        "</select></td>"
        "</tr>"
        # --- Day 2 ---
        "<tr class='tablemajorheader'>"
        "<td colspan='4'>Mar. 22, 2026</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td>&nbsp;</td><td>LD</td><td>&nbsp;</td>"
        "</tr>"
        "<tr>"
        "<td rowspan='2'>"
        "<strong><a href='slots-edit.php?slotid=5'>8:30 AM</a></strong>"
        "</td>"
        "<td colspan='1'>"
        "<strong><a href='slots-edit.php?slotid=5'>Day 2 Round 1</a></strong>"
        "</td>"
        "<td rowspan='2'>"
        "<strong><a href='slots-edit.php?slotid=5'>8:30 AM</a></strong>"
        "</td>"
        "</tr>"
        "<tr>"
        "<td><select name='roundassign[5][1]'>"
        "<option value='0'> </option>"
        "<option selected value='1-1'>Rd. 1</option>"
        "</select></td>"
        "</tr>"
        "</table></form>"
    )
    slots = parse_timeslots_from_html(html)

    assert len(slots) == 2, f"Expected 2 slots across 2 days, got {len(slots)}"

    # Day 1
    assert slots[0]["slot_id"] == 1
    assert slots[0]["date"] == "Mar. 21, 2026"
    assert slots[0]["time"] == "9:00 AM"
    assert slots[0]["description"] == "Day 1 Round 1"

    # Day 2
    assert slots[1]["slot_id"] == 5
    assert slots[1]["date"] == "Mar. 22, 2026"
    assert slots[1]["time"] == "8:30 AM"
    assert slots[1]["description"] == "Day 2 Round 1"


def test_parse_timeslots_no_form2():
    """HTML without form2 returns empty list."""
    html = "<html><body><p>No schedule here.</p></body></html>"
    assert parse_timeslots_from_html(html) == []


def test_parse_timeslots_empty_html():
    """Empty string returns empty list."""
    assert parse_timeslots_from_html("") == []


# ---------------------------------------------------------------------------
# Grouping Parser Tests
# ---------------------------------------------------------------------------

SAMPLE_GROUPINGS_HTML = (
    "<table class='dd'>"
    "<tr class='tableheader'>"
    "<td class='dd'>Grouping name</td>"
    "<td class='dd'>Abbr.</td>"
    "<td class='dd'>Event</td>"
    "<td class='dd'>Divisions</td>"
    "</tr>"
    "<tr>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=6'>Varsity Lincoln-Douglas</a>"
    "</td>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=6'>EVT-A</a>"
    "</td>"
    "<td class='dd'>Policy Debate</td>"
    "<td class='dd'>Open </td>"
    "</tr>"
    "<tr class='tar'>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=3'>JV Policy Debate</a>"
    "</td>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=3'>EVT-B</a>"
    "</td>"
    "<td class='dd'>Policy Debate</td>"
    "<td class='dd'>JV </td>"
    "</tr>"
    "<tr>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=4'>Novice Restricted Packet Policy Debate</a>"
    "</td>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=4'>EVT-C</a>"
    "</td>"
    "<td class='dd'>Policy Debate</td>"
    "<td class='dd'>Novice Restricted Packet </td>"
    "</tr>"
    "<tr class='tar'>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=5'>Rookie Policy Debate</a>"
    "</td>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=5'>EVT-D</a>"
    "</td>"
    "<td class='dd'>Policy Debate</td>"
    "<td class='dd'>Rookie </td>"
    "</tr>"
    "<tr>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=2'>Varsity Policy Debate</a>"
    "</td>"
    "<td class='dd'>"
    "<a href='groupings-edit.php?groupingid=2'>EVT-E</a>"
    "</td>"
    "<td class='dd'>Policy Debate</td>"
    "<td class='dd'>Varsity </td>"
    "</tr>"
    "</table>"
)


def test_parse_groupings_happy_path():
    """Full sample HTML produces five grouping records with correct fields."""
    groupings = parse_groupings_from_html(SAMPLE_GROUPINGS_HTML)

    assert len(groupings) == 5, f"Expected 5 groupings, got {len(groupings)}"

    expected = [
        {
            "grouping_id": 6,
            "name": "Varsity Lincoln-Douglas",
            "abbreviation": "EVT-A",
            "event": "Policy Debate",
            "divisions": "Open",
        },
        {
            "grouping_id": 3,
            "name": "JV Policy Debate",
            "abbreviation": "EVT-B",
            "event": "Policy Debate",
            "divisions": "JV",
        },
        {
            "grouping_id": 4,
            "name": "Novice Restricted Packet Policy Debate",
            "abbreviation": "EVT-C",
            "event": "Policy Debate",
            "divisions": "Novice Restricted Packet",
        },
        {
            "grouping_id": 5,
            "name": "Rookie Policy Debate",
            "abbreviation": "EVT-D",
            "event": "Policy Debate",
            "divisions": "Rookie",
        },
        {
            "grouping_id": 2,
            "name": "Varsity Policy Debate",
            "abbreviation": "EVT-E",
            "event": "Policy Debate",
            "divisions": "Varsity",
        },
    ]

    for i, (actual, exp) in enumerate(zip(groupings, expected)):
        assert actual == exp, f"Grouping {i} mismatch: {actual} != {exp}"


def test_parse_groupings_empty_table():
    """Table with only a header row and no data rows returns empty list."""
    html = (
        "<table class='dd'>"
        "<tr class='tableheader'>"
        "<td class='dd'>Grouping name</td>"
        "<td class='dd'>Abbr.</td>"
        "<td class='dd'>Event</td>"
        "<td class='dd'>Divisions</td>"
        "</tr>"
        "</table>"
    )
    assert parse_groupings_from_html(html) == []


def test_parse_groupings_missing_link():
    """Row without an <a> tag in the name cell is skipped gracefully."""
    html = (
        "<table class='dd'>"
        "<tr class='tableheader'>"
        "<td class='dd'>Grouping name</td>"
        "<td class='dd'>Abbr.</td>"
        "<td class='dd'>Event</td>"
        "<td class='dd'>Divisions</td>"
        "</tr>"
        "<tr>"
        "<td class='dd'>No Link Grouping</td>"
        "<td class='dd'>NLG</td>"
        "<td class='dd'>Lincoln-Douglas</td>"
        "<td class='dd'>Open</td>"
        "</tr>"
        "</table>"
    )
    groupings = parse_groupings_from_html(html)
    assert groupings == [], "Row without <a> should be skipped"


def test_parse_groupings_single_grouping():
    """Table with a single data row returns exactly one record."""
    html = (
        "<table class='dd'>"
        "<tr class='tableheader'>"
        "<td class='dd'>Grouping name</td>"
        "<td class='dd'>Abbr.</td>"
        "<td class='dd'>Event</td>"
        "<td class='dd'>Divisions</td>"
        "</tr>"
        "<tr>"
        "<td class='dd'>"
        "<a href='groupings-edit.php?groupingid=99'>Solo LD</a>"
        "</td>"
        "<td class='dd'>"
        "<a href='groupings-edit.php?groupingid=99'>SLD</a>"
        "</td>"
        "<td class='dd'>Lincoln-Douglas</td>"
        "<td class='dd'>Varsity</td>"
        "</tr>"
        "</table>"
    )
    groupings = parse_groupings_from_html(html)

    assert len(groupings) == 1
    g = groupings[0]
    assert g["grouping_id"] == 99
    assert g["name"] == "Solo LD"
    assert g["abbreviation"] == "SLD"
    assert g["event"] == "Lincoln-Douglas"
    assert g["divisions"] == "Varsity"


def test_parse_groupings_empty_html():
    """No table at all returns empty list."""
    assert parse_groupings_from_html("") == []
    assert parse_groupings_from_html("<html><body>Nothing here</body></html>") == []
