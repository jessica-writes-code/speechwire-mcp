"""Tests for speechwire_mcp.rooms.parsers — room list, room usage, and room counts parsers.

Written ahead of implementation per Decision #8 (Rooms Module Architecture).
These tests define the contract for room parser functions.
"""

from speechwire_mcp.rooms.parsers import (
    parse_room_counts_from_html,
    parse_room_list_from_html,
    parse_room_usage_from_html,
)


# ---------------------------------------------------------------------------
# Room List Parser Tests
# ---------------------------------------------------------------------------

ROOM_LIST_AVAIL_HTML = """
<html><body>
<form action="rooms-avail.php" method="post">
  <select name='roomid'>
    <option value='199'>101</option>
    <option value='259'>124B</option>
    <option value='198'>Media Center</option>
    <option value='249'>137 (has constraints)</option>
    <option value='242'>Office Conference 1</option>
  </select>
  <input type="submit" value="View"/>
</form>
</body></html>
"""

ROOM_LIST_EDIT_ONLY_HTML = """
<html><body>
<form action="rooms-edit.php" method="post">
  <select name='roomid'>
    <option value='300'>Gym</option>
    <option value='301'>Cafeteria</option>
    <option value='302'>Library</option>
  </select>
</form>
</body></html>
"""

ROOM_LIST_EMPTY_HTML = """
<html><body>
<p>No rooms configured.</p>
</body></html>
"""


def test_parse_room_list_happy_path():
    rooms = parse_room_list_from_html(ROOM_LIST_AVAIL_HTML)

    assert len(rooms) == 5, f"Expected 5 rooms, got {len(rooms)}"

    by_name = {r["name"]: r for r in rooms}

    # Numeric room
    r101 = by_name["101"]
    assert r101["room_id"] == 199
    assert r101["has_constraints"] is False

    # Room with constraint suffix stripped from name
    r137 = by_name["137"]
    assert r137["room_id"] == 249
    assert r137["has_constraints"] is True

    # Named room without constraints
    media = by_name["Media Center"]
    assert media["room_id"] == 198
    assert media["has_constraints"] is False

    # Alphanumeric room
    assert by_name["124B"]["room_id"] == 259

    # Multi-word named room
    assert by_name["Office Conference 1"]["room_id"] == 242


def test_parse_room_list_fallback_to_edit_form():
    rooms = parse_room_list_from_html(ROOM_LIST_EDIT_ONLY_HTML)

    assert len(rooms) == 3, f"Expected 3 rooms from edit form, got {len(rooms)}"

    by_name = {r["name"]: r for r in rooms}
    assert by_name["Gym"]["room_id"] == 300
    # Edit form doesn't carry constraint info
    for r in rooms:
        assert r["has_constraints"] is False, (
            f"Room '{r['name']}' should have has_constraints=False from edit form"
        )


def test_parse_room_list_empty():
    rooms = parse_room_list_from_html(ROOM_LIST_EMPTY_HTML)
    assert rooms == [], f"Expected empty list, got {rooms}"


# ---------------------------------------------------------------------------
# Room Usage Parser Tests
# ---------------------------------------------------------------------------

def _build_usage_table(
    date: str = "Mar. 7, 2026",
    time_slots: list[str] | None = None,
    room_rows: list[str] | None = None,
) -> str:
    """Build a minimal but realistic rooms-usage.php HTML fixture.

    Parameters
    ----------
    date
        The tournament date shown in the date header.
    time_slots
        Labels for the time columns (e.g. ["8:00 AM", "9:00 AM"]).
    room_rows
        Pre-built ``<tr>`` strings for each room data row.
    """
    if time_slots is None:
        time_slots = ["8:00 AM", "9:00 AM", "10:00 AM"]
    if room_rows is None:
        room_rows = []

    ncols = len(time_slots)
    date_header = (
        f"<tr class='tableheader'>"
        f"<td>Room</td>"
        f"<td colspan='{ncols}'>{date}</td>"
        f"<td>Room</td>"
        f"</tr>"
    )
    time_header = (
        "<tr class='tableheader'>"
        + "".join(f"<td>{t}</td>" for t in time_slots)
        + "</tr>"
    )
    rows = "\n".join(room_rows)
    return (
        f"<html><body>"
        f"<table class='dd'>\n{date_header}\n{time_header}\n{rows}\n</table>"
        f"</body></html>"
    )


def _room_cell_empty() -> str:
    return "<td>&nbsp;</td>"


def _room_cell_assigned(event_code: str, round_num: int) -> str:
    return f"<td><strong>{event_code}</strong><br/>Round {round_num}</td>"


def _room_cell_assigned_no_round(event_code: str) -> str:
    return f"<td><strong>{event_code}</strong></td>"


def _room_cell_timeblock() -> str:
    return "<td><strong>TIME<br/>BLOCK</strong></td>"


def _room_cell_unavailable() -> str:
    return "<td><strong>X</strong></td>"


def _room_row(room_id: int, room_name: str, cells: list[str]) -> str:
    """Build a room data row with room name bookends and a link."""
    return (
        f"<tr>"
        f"<td><a href='rooms-edit.php?roomid={room_id}'>{room_name}</a></td>"
        + "".join(cells)
        + f"<td>{room_name}</td>"
        f"</tr>"
    )


ROOM_USAGE_HAPPY_HTML = _build_usage_table(
    time_slots=["8:00 AM", "9:00 AM", "10:00 AM"],
    room_rows=[
        _room_row(199, "101", [
            _room_cell_empty(),
            _room_cell_assigned("J-CX", 1),
            _room_cell_timeblock(),
        ]),
        _room_row(200, "102", [
            _room_cell_assigned("J-LD", 2),
            _room_cell_unavailable(),
            _room_cell_empty(),
        ]),
    ],
)


def test_parse_room_usage_happy_path():
    rooms = parse_room_usage_from_html(ROOM_USAGE_HAPPY_HTML)

    assert len(rooms) == 2, f"Expected 2 rooms, got {len(rooms)}"

    by_name = {r["room_name"]: r for r in rooms}

    # --- Room 101 ---
    r101 = by_name["101"]
    assert r101["room_id"] == 199
    slots101 = r101["time_slots"]
    assert len(slots101) == 3

    assert slots101[0]["status"] == "available"
    assert slots101[0]["event_code"] is None
    assert slots101[0]["round_number"] is None

    assert slots101[1]["status"] == "assigned"
    assert slots101[1]["event_code"] == "J-CX"
    assert slots101[1]["round_number"] == 1

    assert slots101[2]["status"] == "timeblock"
    assert slots101[2]["event_code"] is None
    assert slots101[2]["round_number"] is None

    # --- Room 102 ---
    r102 = by_name["102"]
    assert r102["room_id"] == 200
    slots102 = r102["time_slots"]

    assert slots102[0]["status"] == "assigned"
    assert slots102[0]["event_code"] == "J-LD"
    assert slots102[0]["round_number"] == 2

    assert slots102[1]["status"] == "unavailable"

    assert slots102[2]["status"] == "available"


def test_parse_room_usage_header_extraction():
    """Each time slot carries the correct time_label from the header row."""
    time_labels = ["8:00 AM", "10:30 AM", "1:00 PM"]
    html = _build_usage_table(
        time_slots=time_labels,
        room_rows=[
            _room_row(100, "A1", [
                _room_cell_empty(),
                _room_cell_assigned("J-PF", 1),
                _room_cell_empty(),
            ]),
        ],
    )
    rooms = parse_room_usage_from_html(html)
    assert len(rooms) == 1

    slots = rooms[0]["time_slots"]
    assert len(slots) == 3
    for i, label in enumerate(time_labels):
        assert slots[i]["time_label"] == label, (
            f"Slot {i} expected time_label='{label}', got '{slots[i].get('time_label')}'"
        )


def test_parse_room_usage_empty_table():
    html = "<html><body><p>No room usage data.</p></body></html>"
    rooms = parse_room_usage_from_html(html)
    assert rooms == [], f"Expected empty list, got {rooms}"


def test_parse_room_usage_malformed_cells():
    """Graceful degradation: assigned cell with no round info."""
    html = _build_usage_table(
        time_slots=["8:00 AM", "9:00 AM"],
        room_rows=[
            _room_row(150, "Lab", [
                _room_cell_assigned_no_round("J-CX"),
                _room_cell_empty(),
            ]),
        ],
    )
    rooms = parse_room_usage_from_html(html)
    assert len(rooms) == 1

    slots = rooms[0]["time_slots"]

    # Event code present but round number missing → graceful None
    assert slots[0]["status"] == "assigned"
    assert slots[0]["event_code"] == "J-CX"
    assert slots[0]["round_number"] is None, (
        "Missing round info should yield round_number=None"
    )

    # Empty cell
    assert slots[1]["status"] == "available"


def test_parse_room_usage_skip_headers():
    """Repeating header rows (SpeechWire pattern) should not produce data."""
    # Real SpeechWire repeats headers every ~12 rows; simulate with interleaved headers
    date_header = (
        "<tr class='tableheader'>"
        "<td>Room</td>"
        "<td colspan='2'>Mar. 7, 2026</td>"
        "<td>Room</td>"
        "</tr>"
    )
    time_header = (
        "<tr class='tableheader'>"
        "<td>8:00 AM</td><td>9:00 AM</td>"
        "</tr>"
    )
    data_row_1 = _room_row(199, "101", [
        _room_cell_assigned("J-CX", 1),
        _room_cell_empty(),
    ])
    data_row_2 = _room_row(200, "102", [
        _room_cell_empty(),
        _room_cell_assigned("J-LD", 3),
    ])

    # Interleave: header, data, header (repeat), data
    table_body = "\n".join([
        date_header,
        time_header,
        data_row_1,
        date_header,
        time_header,
        data_row_2,
    ])
    html = (
        f"<html><body><table class='dd'>\n{table_body}\n</table></body></html>"
    )

    rooms = parse_room_usage_from_html(html)

    assert len(rooms) == 2, (
        f"Expected 2 data rows (headers skipped), got {len(rooms)}"
    )

    names = {r["room_name"] for r in rooms}
    assert names == {"101", "102"}, f"Unexpected room names: {names}"


# ---------------------------------------------------------------------------
# Room Counts Parser Tests
# ---------------------------------------------------------------------------

ROOM_COUNTS_HAPPY_HTML = (
    "<table class='dd'>"
    "<tr align='center' class='tableheader'>"
    "<td class='dd' rowspan='2'>Grouping</td>"
    "<td class='dd' colspan='2'>Round 1</td>"
    "<td class='dd' colspan='2'>Round 2</td>"
    "<td class='dd' rowspan='2'>Grouping</td>"
    "</tr>"
    "<tr class='tableheader'><td class='dd'>Rooms</td><td class='dd'>Sections</td>"
    "<td class='dd'>Rooms</td><td class='dd'>Sections</td></tr>"
    "<tr>"
    "<td class='dd'>Varsity Policy Debate</td>"
    "<td align='center' class='dd'>"
    "<a href='rooms-groupings.php?groupinground=2,1'>4</a></td>"
    "<td align='center' class='dd'>3</td>"
    "<td align='center' class='dd'>"
    "<a href='rooms-groupings.php?groupinground=2,2'>4</a></td>"
    "<td align='center' class='dd'>4</td>"
    "<td class='dd'>Varsity Policy Debate</td>"
    "</tr>"
    "</table>"
)


def test_parse_room_counts_happy_path():
    """Single grouping with 2 rounds — verify all fields including sufficient."""
    records = parse_room_counts_from_html(ROOM_COUNTS_HAPPY_HTML)

    assert len(records) == 1
    rec = records[0]
    assert rec["grouping_name"] == "Varsity Policy Debate"
    assert len(rec["rounds"]) == 2

    r1 = rec["rounds"][0]
    assert r1["round_number"] == 1
    assert r1["rooms"] == 4
    assert r1["sections"] == 3
    assert r1["sufficient"] is True  # 4 >= 3

    r2 = rec["rounds"][1]
    assert r2["round_number"] == 2
    assert r2["rooms"] == 4
    assert r2["sections"] == 4
    assert r2["sufficient"] is True  # 4 >= 4


def test_parse_room_counts_insufficient_rooms():
    """When rooms < sections, sufficient must be False."""
    html = (
        "<table class='dd'>"
        "<tr align='center' class='tableheader'>"
        "<td class='dd' rowspan='2'>Grouping</td>"
        "<td class='dd' colspan='2'>Round 1</td>"
        "<td class='dd' rowspan='2'>Grouping</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td class='dd'>Rooms</td><td class='dd'>Sections</td></tr>"
        "<tr>"
        "<td class='dd'>JV Lincoln-Douglas</td>"
        "<td align='center' class='dd'>2</td>"
        "<td align='center' class='dd'>5</td>"
        "<td class='dd'>JV Lincoln-Douglas</td>"
        "</tr>"
        "</table>"
    )
    records = parse_room_counts_from_html(html)

    assert len(records) == 1
    r = records[0]["rounds"][0]
    assert r["rooms"] == 2
    assert r["sections"] == 5
    assert r["sufficient"] is False  # 2 < 5


def test_parse_room_counts_blacked_out_rounds_skipped():
    """Cells with background-color: #000099 (blacked out) should be skipped."""
    html = (
        "<table class='dd'>"
        "<tr align='center' class='tableheader'>"
        "<td class='dd' rowspan='2'>Grouping</td>"
        "<td class='dd' colspan='2'>Round 1</td>"
        "<td class='dd' colspan='2'>Round 2</td>"
        "<td class='dd' colspan='2'>Round 3</td>"
        "<td class='dd' rowspan='2'>Grouping</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td class='dd'>Rooms</td><td class='dd'>Sections</td>"
        "<td class='dd'>Rooms</td><td class='dd'>Sections</td>"
        "<td class='dd'>Rooms</td><td class='dd'>Sections</td>"
        "</tr>"
        "<tr>"
        "<td class='dd'>Novice LD</td>"
        "<td align='center' class='dd'>3</td>"
        "<td align='center' class='dd'>3</td>"
        # Round 2 is blacked out
        "<td align='center' class='dd' style='background-color: #000099'>&nbsp;</td>"
        "<td align='center' class='dd' style='background-color: #000099'>&nbsp;</td>"
        "<td align='center' class='dd'>5</td>"
        "<td align='center' class='dd'>4</td>"
        "<td class='dd'>Novice LD</td>"
        "</tr>"
        "</table>"
    )
    records = parse_room_counts_from_html(html)

    assert len(records) == 1
    rounds = records[0]["rounds"]
    # Round 2 should be skipped — only rounds 1 and 3 remain
    assert len(rounds) == 2, f"Expected 2 rounds (round 2 skipped), got {len(rounds)}"
    assert rounds[0]["round_number"] == 1
    assert rounds[0]["rooms"] == 3
    assert rounds[0]["sections"] == 3
    assert rounds[0]["sufficient"] is True

    assert rounds[1]["round_number"] == 3
    assert rounds[1]["rooms"] == 5
    assert rounds[1]["sections"] == 4
    assert rounds[1]["sufficient"] is True


def test_parse_room_counts_empty_table():
    """Table with only header rows and no data returns empty list."""
    html = (
        "<table class='dd'>"
        "<tr align='center' class='tableheader'>"
        "<td class='dd' rowspan='2'>Grouping</td>"
        "<td class='dd' colspan='2'>Round 1</td>"
        "<td class='dd' rowspan='2'>Grouping</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td class='dd'>Rooms</td><td class='dd'>Sections</td></tr>"
        "</table>"
    )
    assert parse_room_counts_from_html(html) == []


def test_parse_room_counts_empty_html():
    """Empty or non-table HTML returns empty list."""
    assert parse_room_counts_from_html("") == []
    assert parse_room_counts_from_html("<html><body>Nothing</body></html>") == []


def test_parse_room_counts_multiple_groupings():
    """Multiple groupings each produce a separate record."""
    html = (
        "<table class='dd'>"
        "<tr align='center' class='tableheader'>"
        "<td class='dd' rowspan='2'>Grouping</td>"
        "<td class='dd' colspan='2'>Round 1</td>"
        "<td class='dd' rowspan='2'>Grouping</td>"
        "</tr>"
        "<tr class='tableheader'>"
        "<td class='dd'>Rooms</td><td class='dd'>Sections</td></tr>"
        "<tr>"
        "<td class='dd'>Varsity Policy Debate</td>"
        "<td align='center' class='dd'>6</td>"
        "<td align='center' class='dd'>5</td>"
        "<td class='dd'>Varsity Policy Debate</td>"
        "</tr>"
        "<tr>"
        "<td class='dd'>JV Policy Debate</td>"
        "<td align='center' class='dd'>3</td>"
        "<td align='center' class='dd'>3</td>"
        "<td class='dd'>JV Policy Debate</td>"
        "</tr>"
        "<tr>"
        "<td class='dd'>Novice LD</td>"
        "<td align='center' class='dd'>2</td>"
        "<td align='center' class='dd'>4</td>"
        "<td class='dd'>Novice LD</td>"
        "</tr>"
        "</table>"
    )
    records = parse_room_counts_from_html(html)

    assert len(records) == 3
    by_name = {r["grouping_name"]: r for r in records}

    assert by_name["Varsity Policy Debate"]["rounds"][0]["sufficient"] is True
    assert by_name["JV Policy Debate"]["rounds"][0]["sufficient"] is True
    assert by_name["Novice LD"]["rounds"][0]["sufficient"] is False
