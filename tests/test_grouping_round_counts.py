"""Strict grouping/round room-detail count parsing and retrieval contracts."""

from unittest.mock import MagicMock

import pytest

from speechwire_mcp import SpeechWireAuthError, SpeechWireReadError
from speechwire_mcp.rooms import GroupingRoundCounts, get_grouping_round_counts
from speechwire_mcp.rooms.parsers import parse_grouping_round_counts_from_html


SELECTION_PAGE_HTML = """
<html><body>
<p class="pagetitle">Rooms and competition groupings</p>
<form id="form1" name="form1" method="post" action="rooms-groupings.php">
  <select id='groupinground' name='groupinground'>
    <option value='7,1'>JV Policy Debate, Round 1</option>
    <option value='7,2'>JV Policy Debate, Round 2</option>
    <option value='6,1'>Novice Policy Debate, Round 1</option>
  </select>
  <input type="submit" name="Submit" value="Select round and grouping"/>
</form>
</body></html>
"""

SELECTED_ROUND_PAGE_HTML = """
<html><body>
<p class="pagetitle">Rooms and competition groupings</p>
<form id="form1" name="form1" method="post" action="rooms-groupings.php">
  <select id='groupinground' name='groupinground'>
    <option value='7,1'>JV Policy Debate, Round 1</option>
    <option selected value='7,2'>JV Policy Debate, Round 2</option>
    <option value='6,1'>Novice Policy Debate, Round 1</option>
  </select>
  <input type="submit" name="Submit" value="Select round and grouping"/>
</form>
<p><strong>There are 9 sections in JV Policy Debate, Round 2. (20 entries)</strong></p>
<p class='sectiontitle'>The following 9 rooms have been assigned to JV Policy Debate, Round 2</p>
<table class='dd'><tr><td width='120' class='dd'>
  <a href='rooms-groupings.php?groupinground=7,2&roomid=128&mode=unassign'>143</a>
</td></tr></table>
<form id="form3" name="form3" method="post" action="rooms-groupings.php">
  Copy this room setup to:
  <select id='copyto' name='copyto'>
    <option selected value='7,0'>JV Policy Debate, All prelim rounds</option>
    <option value='7,1'>JV Policy Debate, Round 1</option>
    <option value='7,2'>JV Policy Debate, Round 2</option>
  </select>
  <input name="Submit" type="submit" value="Copy rooms">
  <input name='groupinground' id="groupinground" type="hidden" value="7,2"/>
</form>
<p class='sectiontitle'>The following rooms are not assigned at 11:00 AM</p>
<table class='dd'><tr><td width='120' class='dd'>
  <a href='rooms-groupings.php?groupinground=7,2&roomid=122&mode=assign'>121 Nurse</a>
</td></tr></table>
</body></html>
"""


def _detail_html(entries: int = 20, sections: int = 8, round_number: int = 1) -> str:
    return f"""
    <html><body>
    <h2>There are <strong>{sections}</strong> sections in JV Policy Debate,
        Round {round_number}. <span>({entries} entries)</span></h2>
    <table class="dd"><tr><td>Assigned rooms</td></tr>
    <tr><td>101</td></tr><tr><td>102</td></tr></table>
    </body></html>
    """


def _client(html: str = "") -> MagicMock:
    client = MagicMock()
    client.get.return_value.text = html
    return client


def test_real_selected_round_page_counts_are_independent_of_room_controls():
    assert parse_grouping_round_counts_from_html(SELECTED_ROUND_PAGE_HTML, 7, 2) == {
        "grouping_id": 7,
        "round_number": 2,
        "entries": 20,
        "sections": 9,
    }


def test_reader_gets_real_selected_page_without_submitting_or_following_room_controls():
    client = _client(SELECTED_ROUND_PAGE_HTML)

    assert get_grouping_round_counts(7, 2, client, raise_on_error=True) == {
        "grouping_id": 7,
        "round_number": 2,
        "entries": 20,
        "sections": 9,
    }
    client.get.assert_called_once_with(
        "https://manage.speechwire.com/tabroom/rooms-groupings.php",
        params={"groupinground": "7,2"},
    )
    client.post.assert_not_called()


def test_real_selection_only_page_is_not_a_zero_count():
    with pytest.raises(ValueError, match="Expected one"):
        parse_grouping_round_counts_from_html(SELECTION_PAGE_HTML, 7, 2)


@pytest.mark.parametrize("strict", [False, True])
def test_reader_does_not_submit_selection_only_page(strict):
    client = _client(SELECTION_PAGE_HTML)

    if strict:
        with pytest.raises(SpeechWireReadError, match="Failed to parse"):
            get_grouping_round_counts(7, 2, client, raise_on_error=True)
    else:
        assert get_grouping_round_counts(7, 2, client) is None

    client.get.assert_called_once_with(
        "https://manage.speechwire.com/tabroom/rooms-groupings.php",
        params={"groupinground": "7,2"},
    )
    client.post.assert_not_called()


@pytest.mark.parametrize(
    ("entries", "sections", "round_number"),
    [(20, 8, 1), (20, 0, 2), (21, 0, 2), (0, 0, 1)],
)
def test_explicit_entry_count_independent_of_sections_and_assigned_rooms(
    entries, sections, round_number
):
    result = parse_grouping_round_counts_from_html(
        _detail_html(entries, sections, round_number), 17, round_number
    )

    assert result == {
        "grouping_id": 17,
        "round_number": round_number,
        "entries": entries,
        "sections": sections,
    }
    assert GroupingRoundCounts.__required_keys__ == set(result)


def test_singular_summary_and_parenthesized_grouping_name():
    html = "<p>There is 1 section in Policy (JV), Round 1. (1 entry)</p>"
    assert parse_grouping_round_counts_from_html(html, 17, 1)["entries"] == 1


def test_whitespace_and_html_entities():
    html = "<b>There are 0 sections in JV&nbsp;Policy Debate,<br>Round 2. (20 entries)</b>"
    assert parse_grouping_round_counts_from_html(html, 17, 2)["entries"] == 20


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<html><form>Please log in</form></html>",
        "<p>Round not applicable</p>",
        "<p>There are 8 sections in JV Policy Debate, Round 1.</p>",
        _detail_html().replace("20 entries", "unknown entries"),
        _detail_html().replace("20 entries", "-1 entries"),
        _detail_html().replace("20 entries", "2.5 entries"),
        _detail_html().replace("8</strong>", "-1</strong>"),
        _detail_html() + _detail_html(),
        "<script>There are 8 sections in JV Policy Debate, Round 1. (20 entries)</script>",
    ],
)
def test_missing_malformed_or_ambiguous_summary_is_not_zero(html):
    with pytest.raises(ValueError, match="Expected one"):
        parse_grouping_round_counts_from_html(html, 17, 1)


def test_wrong_round_rejected():
    with pytest.raises(ValueError, match="requested round"):
        parse_grouping_round_counts_from_html(_detail_html(round_number=2), 17, 1)


def test_reader_uses_exact_endpoint_and_params():
    client = _client(_detail_html(round_number=2, sections=0))
    assert get_grouping_round_counts(17, 2, client, raise_on_error=True) == {
        "grouping_id": 17,
        "round_number": 2,
        "entries": 20,
        "sections": 0,
    }
    client.get.assert_called_once_with(
        "https://manage.speechwire.com/tabroom/rooms-groupings.php",
        params={"groupinground": "17,2"},
    )
    client.get.return_value.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("html", ["", _detail_html(round_number=2)])
def test_reader_parse_failure_policy(strict, html, caplog):
    client = _client(html)
    if strict:
        with pytest.raises(SpeechWireReadError, match="Failed to parse") as error:
            get_grouping_round_counts(17, 1, client, raise_on_error=True)
        assert isinstance(error.value.__cause__, ValueError)
    else:
        assert get_grouping_round_counts(17, 1, client) is None
    assert "Failed to parse counts for grouping 17, round 1" in caplog.text


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("failure_stage", ["fetch", "http", "auth"])
def test_reader_fetch_failure_policy(strict, failure_stage, caplog):
    client = _client(_detail_html())
    cause = SpeechWireAuthError("expired") if failure_stage == "auth" else RuntimeError("down")
    if failure_stage == "http":
        client.get.return_value.raise_for_status.side_effect = cause
    else:
        client.get.side_effect = cause
    if strict:
        with pytest.raises(SpeechWireReadError, match="Failed to fetch") as error:
            get_grouping_round_counts(17, 1, client, raise_on_error=True)
        assert error.value.__cause__ is cause
    else:
        assert get_grouping_round_counts(17, 1, client) is None
    assert "Failed to fetch counts for grouping 17, round 1" in caplog.text


@pytest.mark.parametrize("strict", [False, True])
def test_reader_explicit_zero_is_success(strict):
    result = get_grouping_round_counts(
        17, 1, _client(_detail_html(0, 0)), raise_on_error=strict
    )
    assert result is not None
    assert result["entries"] == 0


@pytest.mark.parametrize("strict", [False, True])
def test_reader_missing_client(strict):
    if strict:
        with pytest.raises(SpeechWireReadError, match="No SpeechWire client"):
            get_grouping_round_counts(17, 1, None, raise_on_error=True)
    else:
        assert get_grouping_round_counts(17, 1, None) is None


@pytest.mark.parametrize(("grouping_id", "round_number"), [(0, 1), (-1, 1), (17, 0), (17, -1)])
@pytest.mark.parametrize("strict", [False, True])
def test_invalid_identifiers_do_not_fetch(grouping_id, round_number, strict, caplog):
    client = _client(_detail_html())
    if strict:
        with pytest.raises(SpeechWireReadError, match="positive integers"):
            get_grouping_round_counts(grouping_id, round_number, client, raise_on_error=True)
    else:
        assert get_grouping_round_counts(grouping_id, round_number, client) is None
    client.get.assert_not_called()
    assert "positive integers" in caplog.text
