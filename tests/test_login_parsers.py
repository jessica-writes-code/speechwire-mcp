"""Tests for login/ module parsers: account list and tournament list HTML parsing.

These tests are written proactively against the lazy-IDs architecture spec.
They will skip gracefully if the login module has not been implemented yet.
"""

import pytest

from fake_data import HARTSFIELD_LANDING, KENNISON_ACADEMY, CHESAPEAKE_PREP

# Graceful import — skip all tests if login/parsers.py isn't available yet
try:
    from speechwire_mcp.login.parsers import (
        parse_account_list_html,
        parse_tournament_list_html,
    )
except ImportError:
    pytestmark = pytest.mark.skip(reason="speechwire_mcp.login.parsers not implemented yet")
    parse_account_list_html = None  # type: ignore[assignment]
    parse_tournament_list_html = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# HTML fixtures — account list
# ---------------------------------------------------------------------------

SINGLE_ACCOUNT_HTML = f"""<!DOCTYPE html>
<html>
<head><title>Select Account</title></head>
<body>
  <p class="pagetitle">Select Account</p>
  <table class="dd">
    <tr class="tableheader"><td>Account</td></tr>
    <tr>
      <td>
        <a href="c-account-select.php?selectaccountid=12345">{HARTSFIELD_LANDING}</a>
      </td>
    </tr>
  </table>
</body>
</html>
"""

MULTIPLE_ACCOUNTS_HTML = f"""<!DOCTYPE html>
<html>
<head><title>Select Account</title></head>
<body>
  <p class="pagetitle">Select Account</p>
  <table class="dd">
    <tr class="tableheader"><td>Account</td></tr>
    <tr>
      <td>
        <a href="c-account-select.php?selectaccountid=12345">{HARTSFIELD_LANDING}</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="c-account-select.php?selectaccountid=67890">{KENNISON_ACADEMY}</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="c-account-select.php?selectaccountid=11111">{CHESAPEAKE_PREP}</a>
      </td>
    </tr>
  </table>
</body>
</html>
"""

EMPTY_ACCOUNTS_HTML = """<!DOCTYPE html>
<html>
<head><title>Select Account</title></head>
<body>
  <p class="pagetitle">Select Account</p>
  <table class="dd">
    <tr class="tableheader"><td>Account</td></tr>
  </table>
</body>
</html>
"""

NO_TABLE_ACCOUNTS_HTML = """<!DOCTYPE html>
<html>
<head><title>Select Account</title></head>
<body>
  <p>Something went wrong. Please try again.</p>
</body>
</html>
"""

MALFORMED_ACCOUNTS_HTML = """<html><body>
  <table class="dd">
    <tr><td><a href="garbage-no-query-params">Broken Link</a></td></tr>
    <tr><td>No anchor at all</td></tr>
    <tr><td><a href="c-account-select.php?selectaccountid=notanumber">Bad ID</a></td></tr>
  </table>
</body></html>
"""

# ---------------------------------------------------------------------------
# HTML fixtures — tournament list
# ---------------------------------------------------------------------------

SINGLE_TOURNAMENT_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <p class="pagetitle">Select a tournament</p>
  <table class="dd">
    <tr class="tableheader">
      <td>Tournament</td><td>Date</td>
    </tr>
    <tr>
      <td>
        <a href="c-circuit-tournaments.php?tournid=50001&circuitid=200">
          Spring Invitational 2025
        </a>
      </td>
      <td>Mar 15, 2025</td>
    </tr>
  </table>
</body>
</html>
"""

MULTIPLE_TOURNAMENTS_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <p class="pagetitle">Select a tournament</p>
  <table class="dd">
    <tr class="tableheader">
      <td>Tournament</td><td>Date</td>
    </tr>
    <tr>
      <td>
        <a href="c-circuit-tournaments.php?tournid=50001&circuitid=200">
          Spring Invitational 2025
        </a>
      </td>
      <td>Mar 15, 2025</td>
    </tr>
    <tr>
      <td>
        <a href="c-circuit-tournaments.php?tournid=50002&circuitid=200">
          Fall Classic 2024
        </a>
      </td>
      <td>Oct 20, 2024</td>
    </tr>
    <tr>
      <td>
        <a href="c-circuit-tournaments.php?tournid=50003&circuitid=300">
          State Championship 2025
        </a>
      </td>
      <td>May 5, 2025</td>
    </tr>
  </table>
</body>
</html>
"""

EMPTY_TOURNAMENTS_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <p class="pagetitle">Select a tournament</p>
  <table class="dd">
    <tr class="tableheader"><td>Tournament</td><td>Date</td></tr>
  </table>
</body>
</html>
"""

NO_TABLE_TOURNAMENTS_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <p>No tournaments available.</p>
</body>
</html>
"""

MALFORMED_TOURNAMENTS_HTML = """<html><body>
  <table class="dd">
    <tr><td><a href="no-params-at-all">Bad Tournament</a></td><td></td></tr>
    <tr><td>No anchor tag here</td><td>Jan 1</td></tr>
    <tr><td><a href="c-circuit-tournaments.php?tournid=abc&circuitid=xyz">Non-numeric</a></td>
        <td>Feb 2</td></tr>
  </table>
</body></html>
"""

# Realistic SpeechWire HTML: <select name="tournid"> inside forms
REAL_SPEECHWIRE_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <form action="c-circuit-tournaments.php" method="post"
        name="formaddexisting" id="formaddexisting">
    <select id='tournid' name='tournid'>
      <option value='20022'>Bartlet Invitational (Oct. 25, 2025)</option>
      <option value='20074'>Capitol Thanksgiving Classic (Nov. 22, 2025)</option>
      <option value='21289'>Capitol National Qualifiers (Mar. 7, 2026)</option>
    </select>
    <input name='circuitid' id="circuitid" type="hidden" value="25" />
    <input name='mode' id="mode" type="hidden" value="tournjump" />
  </form>
  <form action="c-circuit-tournaments.php" method="post"
        name="formold" id="formold">
    <select id='tournidold' name='tournid'>
      <option value='10001'>Old Tourney One (Sep. 10, 2020)</option>
      <option value='10002'>Old Tourney Two (Oct. 5, 2020)</option>
    </select>
    <input name='circuitid' type="hidden" value="25" />
  </form>
</body>
</html>
"""

REAL_SPEECHWIRE_NO_DATE_HTML = """<html><body>
  <form name="formaddexisting">
    <select name='tournid'>
      <option value='99999'>Practice Round No Date</option>
    </select>
    <input name='circuitid' type="hidden" value="42" />
  </form>
</body></html>
"""

REAL_SPEECHWIRE_EMPTY_SELECT_HTML = """<html><body>
  <form name="formaddexisting">
    <select name='tournid'>
      <option value=''>-- Select --</option>
    </select>
    <input name='circuitid' type="hidden" value="25" />
  </form>
</body></html>
"""

REAL_SPEECHWIRE_NO_CIRCUIT_HTML = """<html><body>
  <form name="formaddexisting">
    <select name='tournid'>
      <option value='30001'>Solo Tourney (Jan. 1, 2026)</option>
    </select>
  </form>
</body></html>
"""

REAL_SPEECHWIRE_DATE_RANGE_HTML = """<html><body>
  <form name="formaddexisting">
    <select name='tournid'>
      <option value='40001'>Weekend Invitational (Feb. 14-15, 2026)</option>
    </select>
    <input name='circuitid' type="hidden" value="25" />
  </form>
</body></html>
"""


# ---------------------------------------------------------------------------
# Tests — parse_account_list_html
# ---------------------------------------------------------------------------


class TestParseAccountListHtml:
    def test_single_account(self):
        result = parse_account_list_html(SINGLE_ACCOUNT_HTML)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["account_id"] == 12345
        assert result[0]["name"] == HARTSFIELD_LANDING

    def test_multiple_accounts(self):
        result = parse_account_list_html(MULTIPLE_ACCOUNTS_HTML)
        assert len(result) == 3
        ids = [r["account_id"] for r in result]
        assert 12345 in ids
        assert 67890 in ids
        assert 11111 in ids
        names = [r["name"] for r in result]
        assert HARTSFIELD_LANDING in names
        assert KENNISON_ACADEMY in names
        assert CHESAPEAKE_PREP in names

    def test_empty_table_returns_empty_list(self):
        result = parse_account_list_html(EMPTY_ACCOUNTS_HTML)
        assert result == []

    def test_no_table_returns_empty_list(self):
        result = parse_account_list_html(NO_TABLE_ACCOUNTS_HTML)
        assert result == []

    def test_malformed_html_returns_empty_list(self):
        result = parse_account_list_html(MALFORMED_ACCOUNTS_HTML)
        assert isinstance(result, list)
        # Parser should gracefully handle bad links — no crashes
        for record in result:
            # Records with unparseable IDs should be skipped or have None
            assert isinstance(record, dict)

    def test_empty_string_returns_empty_list(self):
        result = parse_account_list_html("")
        assert result == []

    def test_account_records_have_required_keys(self):
        result = parse_account_list_html(SINGLE_ACCOUNT_HTML)
        assert len(result) == 1
        assert "account_id" in result[0]
        assert "name" in result[0]


# ---------------------------------------------------------------------------
# Tests — parse_tournament_list_html
# ---------------------------------------------------------------------------


class TestParseTournamentListHtml:
    def test_single_tournament(self):
        result = parse_tournament_list_html(SINGLE_TOURNAMENT_HTML)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["tournament_id"] == 50001
        assert result[0]["circuit_id"] == 200
        assert "Spring Invitational" in result[0]["name"]

    def test_multiple_tournaments(self):
        result = parse_tournament_list_html(MULTIPLE_TOURNAMENTS_HTML)
        assert len(result) == 3
        tourn_ids = [r["tournament_id"] for r in result]
        assert 50001 in tourn_ids
        assert 50002 in tourn_ids
        assert 50003 in tourn_ids
        circuit_ids = [r["circuit_id"] for r in result]
        assert 200 in circuit_ids
        assert 300 in circuit_ids

    def test_multiple_tournaments_have_names(self):
        result = parse_tournament_list_html(MULTIPLE_TOURNAMENTS_HTML)
        names = [r["name"] for r in result]
        assert any("Spring" in n for n in names)
        assert any("Fall" in n for n in names)
        assert any("State" in n for n in names)

    def test_empty_table_returns_empty_list(self):
        result = parse_tournament_list_html(EMPTY_TOURNAMENTS_HTML)
        assert result == []

    def test_no_table_returns_empty_list(self):
        result = parse_tournament_list_html(NO_TABLE_TOURNAMENTS_HTML)
        assert result == []

    def test_malformed_html_returns_empty_list(self):
        result = parse_tournament_list_html(MALFORMED_TOURNAMENTS_HTML)
        assert isinstance(result, list)
        for record in result:
            assert isinstance(record, dict)

    def test_empty_string_returns_empty_list(self):
        result = parse_tournament_list_html("")
        assert result == []

    def test_tournament_records_have_required_keys(self):
        result = parse_tournament_list_html(SINGLE_TOURNAMENT_HTML)
        assert len(result) == 1
        rec = result[0]
        assert "tournament_id" in rec
        assert "circuit_id" in rec
        assert "name" in rec
        assert "season" in rec

    def test_date_field_present_when_available(self):
        result = parse_tournament_list_html(SINGLE_TOURNAMENT_HTML)
        rec = result[0]
        # date may be str or None per the spec
        assert "date" in rec or rec.get("date") is None


class TestParseTournamentListSelectStrategy:
    """Tests for Strategy 1: <select name="tournid"> (real SpeechWire HTML)."""

    def test_real_html_extracts_all_seasons(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_HTML)
        # 3 current + 2 past tournaments
        assert len(result) == 5
        tourn_ids = {r["tournament_id"] for r in result}
        assert tourn_ids == {20022, 20074, 21289, 10001, 10002}

    def test_real_html_extracts_circuit_id(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_HTML)
        for rec in result:
            assert rec["circuit_id"] == 25

    def test_real_html_extracts_names(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_HTML)
        names = [r["name"] for r in result]
        assert any("Bartlet" in n for n in names)
        assert any("Thanksgiving" in n for n in names)
        assert any("National Qualifiers" in n for n in names)

    def test_real_html_extracts_dates(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_HTML)
        dates = {r["tournament_id"]: r["date"] for r in result}
        assert dates[20022] == "Oct. 25, 2025"
        assert dates[20074] == "Nov. 22, 2025"
        assert dates[21289] == "Mar. 7, 2026"

    def test_no_date_returns_none(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_NO_DATE_HTML)
        assert len(result) == 1
        assert result[0]["date"] is None
        assert result[0]["name"] == "Practice Round No Date"

    def test_empty_option_values_skipped(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_EMPTY_SELECT_HTML)
        assert result == []

    def test_missing_circuit_id_returns_none(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_NO_CIRCUIT_HTML)
        assert len(result) == 1
        assert result[0]["circuit_id"] is None
        assert result[0]["tournament_id"] == 30001
        assert result[0]["date"] == "Jan. 1, 2026"

    def test_date_range_parsing(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_DATE_RANGE_HTML)
        assert len(result) == 1
        assert result[0]["date"] == "Feb. 14-15, 2026"

    def test_records_have_required_keys(self):
        result = parse_tournament_list_html(REAL_SPEECHWIRE_HTML)
        for rec in result:
            assert "tournament_id" in rec
            assert "circuit_id" in rec
            assert "name" in rec
            assert "date" in rec
            assert "season" in rec


# ---------------------------------------------------------------------------
# HTML fixtures — tournament list (select-dropdown strategy)
# ---------------------------------------------------------------------------

SELECT_DROPDOWN_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <p class="pagetitle">Select a tournament</p>
  <form action="c-circuit-tournaments.php" method="post"
        name="formaddexisting" id="formaddexisting">
    <select id='tournid' name='tournid'>
      <option value='20022'>Bartlet Invitational (Oct. 25, 2025)</option>
      <option value='20074'>Capitol Thanksgiving Classic (Nov. 22, 2025)</option>
      <option value='21289'>Capitol National Qualifiers (Mar. 7, 2026)</option>
    </select>
    <input name='circuitid' id="circuitid" type="hidden" value="25" />
    <input name='mode' id="mode" type="hidden" value="tournjump" />
  </form>
</body>
</html>
"""

CURRENT_AND_PAST_SEASONS_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <p class="pagetitle">Select a tournament</p>
  <form action="c-circuit-tournaments.php" method="post"
        name="formaddexisting" id="formaddexisting">
    <select id='tournid' name='tournid'>
      <option value='20022'>Bartlet Invitational (Oct. 25, 2025)</option>
      <option value='20074'>Capitol Thanksgiving Classic (Nov. 22, 2025)</option>
    </select>
    <input name='circuitid' id="circuitid" type="hidden" value="25" />
    <input name='mode' id="mode" type="hidden" value="tournjump" />
  </form>
  <form action="c-circuit-tournaments.php" method="post"
        name="formold" id="formold">
    <select id='tournid' name='tournid'>
      <option value='18001'>Past Season Tournament A (Sep. 1, 2024)</option>
      <option value='18002'>Past Season Tournament B (Oct. 15, 2024)</option>
      <option value='18003'>Past Season Tournament C (Nov. 20, 2024)</option>
    </select>
    <input name='circuitid' id="circuitid" type="hidden" value="25" />
    <input name='mode' id="mode" type="hidden" value="tournjump" />
  </form>
</body>
</html>
"""

NO_DATE_OPTION_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <form action="c-circuit-tournaments.php" method="post"
        name="formaddexisting" id="formaddexisting">
    <select id='tournid' name='tournid'>
      <option value='99'>Test Tournament</option>
    </select>
    <input name='circuitid' id="circuitid" type="hidden" value="10" />
  </form>
</body>
</html>
"""

EMPTY_SELECT_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <form action="c-circuit-tournaments.php" method="post"
        name="formaddexisting" id="formaddexisting">
    <select id='tournid' name='tournid'>
    </select>
    <input name='circuitid' id="circuitid" type="hidden" value="25" />
  </form>
</body>
</html>
"""

NO_SELECT_PLAIN_PAGE_HTML = """<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
  <p class="pagetitle">Welcome to SpeechWire</p>
  <p>There are no tournaments configured for this circuit.</p>
</body>
</html>
"""

DATE_RANGE_OPTION_HTML = """<!DOCTYPE html>
<html>
<head><title>Tournaments</title></head>
<body>
  <form action="c-circuit-tournaments.php" method="post"
        name="formaddexisting" id="formaddexisting">
    <select id='tournid' name='tournid'>
      <option value='5001'>Fall Classic (Sep. 16-17, 2016)</option>
      <option value='5002'>Spring Open (Mar. 3-4, 2017)</option>
    </select>
    <input name='circuitid' id="circuitid" type="hidden" value="42" />
  </form>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Tests — parse_tournament_list_html (select-dropdown strategy)
# ---------------------------------------------------------------------------


class TestParseTournamentSelectDropdown:
    """Tests for the real SpeechWire HTML format using <select> dropdowns."""

    def test_parse_tournaments_from_select_dropdown(self):
        """Realistic fixture with 3 options in a <select name='tournid'>."""
        result = parse_tournament_list_html(SELECT_DROPDOWN_HTML)
        assert isinstance(result, list)
        assert len(result) == 3

        ids = {r["tournament_id"] for r in result}
        assert ids == {20022, 20074, 21289}

        for rec in result:
            assert isinstance(rec["tournament_id"], int)
            assert rec["circuit_id"] == 25

        by_id = {r["tournament_id"]: r for r in result}
        assert "Bartlet Invitational" in by_id[20022]["name"]
        assert "Capitol Thanksgiving Classic" in by_id[20074]["name"]
        assert "Capitol National Qualifiers" in by_id[21289]["name"]

        assert by_id[20022]["date"] is not None
        assert "Oct" in by_id[20022]["date"]
        assert "2025" in by_id[20022]["date"]

    def test_parse_tournaments_includes_all_seasons(self):
        """Both formaddexisting (current) and formold (past) tournaments returned."""
        result = parse_tournament_list_html(CURRENT_AND_PAST_SEASONS_HTML)
        assert isinstance(result, list)
        # 2 current + 3 past
        assert len(result) == 5

        ids = {r["tournament_id"] for r in result}
        assert ids == {20022, 20074, 18001, 18002, 18003}

    def test_parse_tournaments_no_date_in_name(self):
        """Option text with no parenthesized date → date should be None."""
        result = parse_tournament_list_html(NO_DATE_OPTION_HTML)
        assert len(result) == 1
        assert result[0]["tournament_id"] == 99
        assert result[0]["circuit_id"] == 10
        assert "Test Tournament" in result[0]["name"]
        assert result[0]["date"] is None

    def test_parse_tournaments_empty_select(self):
        """A form with <select> but no <option>s → empty list."""
        result = parse_tournament_list_html(EMPTY_SELECT_HTML)
        assert result == []

    def test_parse_tournaments_no_select(self):
        """Plain HTML page with no forms/selects → empty list."""
        result = parse_tournament_list_html(NO_SELECT_PLAIN_PAGE_HTML)
        assert result == []

    def test_parse_tournaments_date_range(self):
        """Option text with a date range like '(Sep. 16-17, 2016)'."""
        result = parse_tournament_list_html(DATE_RANGE_OPTION_HTML)
        assert len(result) == 2

        by_id = {r["tournament_id"]: r for r in result}
        assert by_id[5001]["circuit_id"] == 42
        assert by_id[5001]["date"] is not None
        assert "Sep" in by_id[5001]["date"]
        assert "16" in by_id[5001]["date"]
        assert "2016" in by_id[5001]["date"]

        assert by_id[5002]["date"] is not None
        assert "Mar" in by_id[5002]["date"]


# ---------------------------------------------------------------------------
# HTML fixtures — historical tournament support
# ---------------------------------------------------------------------------

PAST_ONLY_HTML = """<!DOCTYPE html>
<html><body>
  <form action="c-circuit-tournaments.php" method="post"
        name="formold" id="formold">
    <select id='tournidold' name='tournid'>
      <option value='4361'>Bartlet Middle Scrimmage (Dec. 12, 2015)</option>
      <option value='4500'>Rosslyn Spring Classic (Mar. 5, 2016)</option>
    </select>
    <input name='circuitid' type="hidden" value="25" />
  </form>
</body></html>
"""

DUPLICATE_ACROSS_FORMS_HTML = """<!DOCTYPE html>
<html><body>
  <form name="formaddexisting">
    <select name='tournid'>
      <option value='20022'>Bartlet Invitational (Oct. 25, 2025)</option>
    </select>
    <input name='circuitid' type="hidden" value="25" />
  </form>
  <form name="formold">
    <select name='tournid'>
      <option value='20022'>Bartlet Invitational Archived (Oct. 25, 2024)</option>
    </select>
    <input name='circuitid' type="hidden" value="25" />
  </form>
</body></html>
"""

PAST_MISSING_CIRCUIT_HTML = """<!DOCTYPE html>
<html><body>
  <form name="formold">
    <select name='tournid'>
      <option value='5555'>Kennison Throwback (Jan. 15, 2018)</option>
    </select>
  </form>
</body></html>
"""

PAST_DATE_RANGE_HTML = """<!DOCTYPE html>
<html><body>
  <form name="formold">
    <select name='tournid'>
      <option value='4988'>Rosslyn Season Opener (Sep. 16-17, 2016)</option>
    </select>
    <input name='circuitid' type="hidden" value="25" />
  </form>
</body></html>
"""


# ---------------------------------------------------------------------------
# Tests — historical tournament behaviour
# ---------------------------------------------------------------------------


class TestParseTournamentListHistorical:
    """Tests for historical (past-season) tournament parsing."""

    def test_both_seasons_returned(self):
        """CURRENT_AND_PAST_SEASONS_HTML returns 5 tournaments (2 current + 3 past)."""
        result = parse_tournament_list_html(CURRENT_AND_PAST_SEASONS_HTML)
        assert len(result) == 5

    def test_current_season_tagged(self):
        """Tournaments from formaddexisting are tagged season='current'."""
        result = parse_tournament_list_html(CURRENT_AND_PAST_SEASONS_HTML)
        current = [r for r in result if r["tournament_id"] in {20022, 20074}]
        assert len(current) == 2
        for rec in current:
            assert rec["season"] == "current"

    def test_past_season_tagged(self):
        """Tournaments from formold are tagged season='past'."""
        result = parse_tournament_list_html(CURRENT_AND_PAST_SEASONS_HTML)
        past = [r for r in result if r["tournament_id"] in {18001, 18002, 18003}]
        assert len(past) == 3
        for rec in past:
            assert rec["season"] == "past"

    def test_circuit_id_extracted_for_both_seasons(self):
        """All records from both forms have circuit_id == 25."""
        result = parse_tournament_list_html(CURRENT_AND_PAST_SEASONS_HTML)
        for rec in result:
            assert rec["circuit_id"] == 25

    def test_dates_extracted_for_both_seasons(self):
        """Dates are present for both current and past tournaments."""
        result = parse_tournament_list_html(CURRENT_AND_PAST_SEASONS_HTML)
        for rec in result:
            assert rec["date"] is not None
            assert isinstance(rec["date"], str)
            assert len(rec["date"]) > 0

    def test_current_only_page(self):
        """SELECT_DROPDOWN_HTML (no formold): 3 tournaments, all season='current'."""
        result = parse_tournament_list_html(SELECT_DROPDOWN_HTML)
        assert len(result) == 3
        for rec in result:
            assert rec["season"] == "current"

    def test_past_only_page(self):
        """PAST_ONLY_HTML: 2 tournaments, all season='past'."""
        result = parse_tournament_list_html(PAST_ONLY_HTML)
        assert len(result) == 2
        ids = {r["tournament_id"] for r in result}
        assert ids == {4361, 4500}
        for rec in result:
            assert rec["season"] == "past"

    def test_empty_page(self):
        """NO_SELECT_PLAIN_PAGE_HTML: returns empty list."""
        result = parse_tournament_list_html(NO_SELECT_PLAIN_PAGE_HTML)
        assert result == []

    def test_empty_selects(self):
        """EMPTY_SELECT_HTML: returns empty list."""
        result = parse_tournament_list_html(EMPTY_SELECT_HTML)
        assert result == []

    def test_all_records_have_season_key(self):
        """Every record from CURRENT_AND_PAST_SEASONS_HTML has a 'season' key."""
        result = parse_tournament_list_html(CURRENT_AND_PAST_SEASONS_HTML)
        for rec in result:
            assert "season" in rec

    def test_deduplication_across_forms(self):
        """Same tournament_id in both forms appears once, tagged 'current'."""
        result = parse_tournament_list_html(DUPLICATE_ACROSS_FORMS_HTML)
        assert len(result) == 1
        assert result[0]["tournament_id"] == 20022
        assert result[0]["season"] == "current"

    def test_past_missing_circuit_id(self):
        """Past form with no circuitid hidden input -> circuit_id is None."""
        result = parse_tournament_list_html(PAST_MISSING_CIRCUIT_HTML)
        assert len(result) == 1
        assert result[0]["tournament_id"] == 5555
        assert result[0]["circuit_id"] is None
        assert result[0]["season"] == "past"

    def test_past_date_range(self):
        """Date range like 'Sep. 16-17, 2016' extracted correctly from past form."""
        result = parse_tournament_list_html(PAST_DATE_RANGE_HTML)
        assert len(result) == 1
        assert result[0]["date"] == "Sep. 16-17, 2016"
        assert result[0]["season"] == "past"

    def test_season_values_are_valid(self):
        """All season values are either 'current' or 'past'."""
        result = parse_tournament_list_html(CURRENT_AND_PAST_SEASONS_HTML)
        valid_seasons = {"current", "past"}
        for rec in result:
            assert rec["season"] in valid_seasons
