"""Tests for add_judge input validation and form data construction."""

import pytest
from unittest.mock import MagicMock, patch

from fake_data import JED_BARTLET, LEO_MCGARRY


def _import_add_judge():
    try:
        from speechwire_mcp.judges.client import add_judge

        return add_judge
    except ImportError:
        pytest.skip("add_judge not implemented yet")


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


class TestAddJudgeValidation:
    def test_rejects_empty_name(self):
        add_judge = _import_add_judge()
        client = MagicMock()
        result = add_judge(client, "")
        assert result["success"] is False
        assert result["error"] is not None
        assert "name" in result["error"].lower()
        client.post.assert_not_called()

    def test_rejects_whitespace_only_name(self):
        add_judge = _import_add_judge()
        client = MagicMock()
        result = add_judge(client, "   ")
        assert result["success"] is False
        assert result["error"] is not None
        client.post.assert_not_called()

    def test_rejects_long_name(self):
        add_judge = _import_add_judge()
        client = MagicMock()
        result = add_judge(client, "x" * 51)
        assert result["success"] is False
        assert "50" in result["error"]
        client.post.assert_not_called()

    def test_rejects_long_email(self):
        add_judge = _import_add_judge()
        client = MagicMock()
        result = add_judge(client, "Test", judge_email="x" * 51)
        assert result["success"] is False
        assert result["error"] is not None
        client.post.assert_not_called()

    def test_rejects_invalid_type_id(self):
        add_judge = _import_add_judge()
        client = MagicMock()
        result = add_judge(client, "Test", team_id=42, judge_type_id=99)
        assert result["success"] is False
        assert result["error"] is not None
        client.post.assert_not_called()

    def test_rejects_zero_team_id(self):
        add_judge = _import_add_judge()
        client = MagicMock()
        result = add_judge(client, "Test", team_id=0)
        assert result["success"] is False
        assert "team_id" in result["error"]
        client.post.assert_not_called()

    def test_accepts_valid_type_ids(self):
        add_judge = _import_add_judge()
        valid_ids = {0, 10, 11, 12, 13, 14}
        for type_id in valid_ids:
            with patch(
                "speechwire_mcp.judges.client._post_and_parse",
                return_value={"success": True, "judge_id": 1, "error": None},
            ):
                result = add_judge(
                    MagicMock(), JED_BARTLET, team_id=42, judge_type_id=type_id,
                )
            assert result["success"] is True, f"type_id={type_id} should be valid"


# ---------------------------------------------------------------------------
# Form data construction tests
# ---------------------------------------------------------------------------


class TestAddJudgeFormData:
    def test_builds_correct_form_data(self):
        add_judge = _import_add_judge()

        with patch(
            "speechwire_mcp.judges.client._post_and_parse",
            return_value={"success": True, "judge_id": 1, "error": None},
        ) as mock_post:
            add_judge(
                MagicMock(),
                JED_BARTLET,
                judge_email="jed@example.com",
                team_id=42,
                judge_type_id=10,
                is_clean=True,
                is_coach=False,
                is_priority=True,
            )

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["judgename"] == JED_BARTLET
        assert data["judgeemail"] == "jed@example.com"
        assert data["teamid"] == "42"
        assert data["judgetypeid"] == "10"
        assert data["judgeisclean"] == "1"
        assert data["judgeiscoach"] == "0"
        assert data["judgeispriority"] == "1"
        assert data["mode"] == "addjudge"
        assert data["Submit"] == "Create judge"

    def test_builds_slot_data(self):
        add_judge = _import_add_judge()

        with patch(
            "speechwire_mcp.judges.client._post_and_parse",
            return_value={"success": True, "judge_id": 1, "error": None},
        ) as mock_post:
            add_judge(MagicMock(), LEO_MCGARRY, team_id=42, available_slots=[1, 3])

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["slotunblock[1]"] == "1"
        assert data["slotunblock[3]"] == "1"
        assert "slotunblock[2]" not in data

    def test_no_slots_when_none(self):
        add_judge = _import_add_judge()

        with patch(
            "speechwire_mcp.judges.client._post_and_parse",
            return_value={"success": True, "judge_id": 1, "error": None},
        ) as mock_post:
            add_judge(MagicMock(), LEO_MCGARRY, team_id=42, available_slots=None)

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        slot_keys = [k for k in data if k.startswith("slotunblock")]
        assert slot_keys == []

    def test_name_is_stripped(self):
        add_judge = _import_add_judge()

        with patch(
            "speechwire_mcp.judges.client._post_and_parse",
            return_value={"success": True, "judge_id": 1, "error": None},
        ) as mock_post:
            add_judge(MagicMock(), f"  {JED_BARTLET}  ", team_id=42)

        call_args = mock_post.call_args
        data = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("data")
        assert data["judgename"] == JED_BARTLET
