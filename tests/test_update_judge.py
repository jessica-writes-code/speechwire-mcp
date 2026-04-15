"""Tests for update_judge_email, update_judge_availability, and update_judge_school."""

import pytest
from unittest.mock import MagicMock, patch

from fake_data import DONNA_MOSS, email_for


def _import_update_judge_email():
    try:
        from speechwire_mcp.judges.client import update_judge_email

        return update_judge_email
    except ImportError:
        pytest.skip("update_judge_email not implemented yet")


def _import_update_judge_availability():
    try:
        from speechwire_mcp.judges.client import update_judge_availability

        return update_judge_availability
    except ImportError:
        pytest.skip("update_judge_availability not implemented yet")


def _import_update_judge_school():
    try:
        from speechwire_mcp.judges.client import update_judge_school

        return update_judge_school
    except ImportError:
        pytest.skip("update_judge_school not implemented yet")


MOCK_CURRENT_VALUES = {
    "fields": {
        "judgename": DONNA_MOSS,
        "judgeemail": email_for(DONNA_MOSS),
        "teamid": "21",
        "judgeisclean": "0",
        "judgeactive": "1",
        "judgeispriority": "0",
    },
    "available_slots": [3, 4],
}


# ---------------------------------------------------------------------------
# Email validation tests
# ---------------------------------------------------------------------------


class TestUpdateJudgeEmailValidation:
    def test_rejects_empty_email(self):
        update = _import_update_judge_email()
        client = MagicMock()
        result = update(42, "", client)
        assert result["success"] is False
        assert result["error"] is not None
        assert "email" in result["error"].lower()

    def test_rejects_whitespace_only_email(self):
        update = _import_update_judge_email()
        client = MagicMock()
        result = update(42, "   ", client)
        assert result["success"] is False
        assert result["error"] is not None

    def test_rejects_invalid_email_format(self):
        update = _import_update_judge_email()
        client = MagicMock()
        result = update(42, "not-an-email", client)
        assert result["success"] is False
        assert "email" in result["error"].lower()

    def test_rejects_email_with_newlines(self):
        update = _import_update_judge_email()
        client = MagicMock()
        result = update(42, "test@example.com\r\nBcc: evil@attacker.com", client)
        assert result["success"] is False
        assert "email" in result["error"].lower()


# ---------------------------------------------------------------------------
# Email form data tests
# ---------------------------------------------------------------------------


class TestUpdateJudgeEmailFormData:
    def test_prefetch_happens(self):
        update = _import_update_judge_email()

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=MOCK_CURRENT_VALUES.copy(),
            ) as mock_fetch,
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ),
        ):
            update(42, "new@example.com", MagicMock())

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        url = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("url")
        assert "judges-edit.php" in url
        params = call_args[1].get("params", {}) if call_args[1] else {}
        assert params.get("judgeid") == "42"

    def test_post_form_data_has_required_fields(self):
        update = _import_update_judge_email()

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=MOCK_CURRENT_VALUES.copy(),
            ),
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ) as mock_post,
        ):
            update(42, "new@example.com", MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["mode"] == "editjudge"
        assert data["judgeid"] == "42"
        assert data["Submit"] == "Save changes"

    def test_email_is_replaced(self):
        update = _import_update_judge_email()

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=MOCK_CURRENT_VALUES.copy(),
            ),
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ) as mock_post,
        ):
            update(42, "new@example.com", MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["judgeemail"] == "new@example.com"

    def test_other_fields_preserved(self):
        update = _import_update_judge_email()

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=MOCK_CURRENT_VALUES.copy(),
            ),
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ) as mock_post,
        ):
            update(42, "new@example.com", MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["judgename"] == DONNA_MOSS
        assert data["teamid"] == "21"
        assert data["judgeisclean"] == "0"
        assert data["judgeactive"] == "1"
        assert data["judgeispriority"] == "0"

    def test_available_slots_preserved(self):
        update = _import_update_judge_email()

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=MOCK_CURRENT_VALUES.copy(),
            ),
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ) as mock_post,
        ):
            update(42, "new@example.com", MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["slotunblock[3]"] == "1"
        assert data["slotunblock[4]"] == "1"
        assert "slotunblock[5]" not in data

    def test_extra_fields_preserved(self):
        update = _import_update_judge_email()
        mock_values = {
            "fields": {
                **MOCK_CURRENT_VALUES["fields"],
                "judgeiscoach": "1",
            },
            "available_slots": MOCK_CURRENT_VALUES["available_slots"],
        }

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=mock_values,
            ),
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ) as mock_post,
        ):
            update(42, "new@example.com", MagicMock())

        call_args = mock_post.call_args
        data = (
            call_args[0][2]
            if len(call_args[0]) > 2
            else call_args[1].get("data")
        )
        assert data["judgeiscoach"] == "1"


# ---------------------------------------------------------------------------
# Availability form data tests
# ---------------------------------------------------------------------------


class TestUpdateJudgeAvailabilityFormData:
    def test_slots_are_replaced(self):
        update = _import_update_judge_availability()

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=MOCK_CURRENT_VALUES.copy(),
            ),
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ) as mock_post,
        ):
            update(42, [5, 6], MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["slotunblock[5]"] == "1"
        assert data["slotunblock[6]"] == "1"
        assert "slotunblock[3]" not in data
        assert "slotunblock[4]" not in data

    def test_other_fields_preserved(self):
        update = _import_update_judge_availability()

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=MOCK_CURRENT_VALUES.copy(),
            ),
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ) as mock_post,
        ):
            update(42, [5], MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["judgename"] == DONNA_MOSS
        assert data["judgeemail"] == email_for(DONNA_MOSS)
        assert data["teamid"] == "21"
        assert data["mode"] == "editjudge"

    def test_empty_slots_clears_all(self):
        update = _import_update_judge_availability()

        with (
            patch(
                "speechwire_mcp.judges.client._fetch_and_parse",
                return_value=MOCK_CURRENT_VALUES.copy(),
            ),
            patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 42, "error": None},
            ) as mock_post,
        ):
            update(42, [], MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        slot_keys = [k for k in data if k.startswith("slotunblock")]
        assert slot_keys == []


# ---------------------------------------------------------------------------
# Prefetch failure tests
# ---------------------------------------------------------------------------


class TestPrefetchFailure:
    def test_update_email_returns_error_on_prefetch_failure(self):
        update = _import_update_judge_email()

        with patch(
            "speechwire_mcp.judges.client._fetch_and_parse",
            return_value=None,
        ):
            result = update(42, "new@example.com", MagicMock())

        assert result["success"] is False
        assert result["error"] is not None
        assert "prefetch" in result["error"].lower()

    def test_update_availability_returns_error_on_prefetch_failure(self):
        update = _import_update_judge_availability()

        with patch(
            "speechwire_mcp.judges.client._fetch_and_parse",
            return_value=None,
        ):
            result = update(42, [1, 2], MagicMock())

        assert result["success"] is False
        assert result["error"] is not None
        assert "prefetch" in result["error"].lower()


# ---------------------------------------------------------------------------
# Update school tests
# ---------------------------------------------------------------------------


class TestUpdateJudgeSchoolValidation:
    def test_rejects_zero_team_id(self):
        update = _import_update_judge_school()
        client = MagicMock()
        result = update(42, 0, client)
        assert result["success"] is False
        assert "team_id" in result["error"]


class TestUpdateJudgeSchoolFormData:
    def test_team_id_is_replaced(self):
        update = _import_update_judge_school()

        with patch(
            "speechwire_mcp.judges.client._fetch_and_parse",
            return_value=MOCK_CURRENT_VALUES,
        ), patch(
            "speechwire_mcp.judges.client._post_and_parse",
            return_value={"success": True, "judge_id": 42, "error": None},
        ) as mock_post:
            update(42, 99, MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["teamid"] == "99"

    def test_other_fields_preserved(self):
        update = _import_update_judge_school()

        with patch(
            "speechwire_mcp.judges.client._fetch_and_parse",
            return_value=MOCK_CURRENT_VALUES,
        ), patch(
            "speechwire_mcp.judges.client._post_and_parse",
            return_value={"success": True, "judge_id": 42, "error": None},
        ) as mock_post:
            update(42, 99, MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["judgename"] == DONNA_MOSS
        assert data["judgeemail"] == email_for(DONNA_MOSS)
        assert data["mode"] == "editjudge"

    def test_available_slots_preserved(self):
        update = _import_update_judge_school()

        with patch(
            "speechwire_mcp.judges.client._fetch_and_parse",
            return_value=MOCK_CURRENT_VALUES,
        ), patch(
            "speechwire_mcp.judges.client._post_and_parse",
            return_value={"success": True, "judge_id": 42, "error": None},
        ) as mock_post:
            update(42, 99, MagicMock())

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["slotunblock[3]"] == "1"
        assert data["slotunblock[4]"] == "1"

    def test_prefetch_failure(self):
        update = _import_update_judge_school()

        with patch(
            "speechwire_mcp.judges.client._fetch_and_parse",
            return_value=None,
        ):
            result = update(42, 99, MagicMock())

        assert result["success"] is False
        assert "prefetch" in result["error"].lower()
