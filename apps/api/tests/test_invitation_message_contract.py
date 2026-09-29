"""Shared cross-layer invitation-message contract vectors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from app.models import MAX_INVITATION_MESSAGE_CODE_POINTS
from app.services.invitation_sending import (
    MAX_INVITATION_MESSAGE_WORDS,
    InvitationSendError,
    canonicalize_invitation_message,
)

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3] / "contracts" / "invitation_message_validation.json"
)


def _contract() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(CONTRACT_PATH.read_text(encoding="utf-8")))


def _assert_vector(case: dict[str, Any], message: str) -> None:
    expected_reason = case["reason"]
    if expected_reason is not None:
        with pytest.raises(InvitationSendError) as raised:
            canonicalize_invitation_message(message)
        assert raised.value.reason.value == expected_reason
        return

    result = canonicalize_invitation_message(message)
    assert result.value == message.strip()
    assert result.word_count == case["word_count"]
    assert result.code_point_count == case["code_point_count"]


def test_shared_limits_match_backend_authority() -> None:
    contract = _contract()

    assert contract["limits"] == {
        "max_words": MAX_INVITATION_MESSAGE_WORDS,
        "max_code_points": MAX_INVITATION_MESSAGE_CODE_POINTS,
    }


@pytest.mark.parametrize("case", _contract()["literal_cases"], ids=lambda case: case["name"])
def test_literal_message_vectors(case: dict[str, Any]) -> None:
    _assert_vector(case, case["input"])
    if case["reason"] is None:
        assert canonicalize_invitation_message(case["input"]).value == case["canonical"]


@pytest.mark.parametrize("case", _contract()["generated_cases"], ids=lambda case: case["name"])
def test_generated_boundary_vectors(case: dict[str, Any]) -> None:
    message = case["separator"].join([case["unit"]] * case["repeat"])
    _assert_vector(case, message)


def test_html_looking_message_is_preserved_as_inert_plain_text() -> None:
    message = "<script>alert(1)</script>"

    assert canonicalize_invitation_message(message).value == message
