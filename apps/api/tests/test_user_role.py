"""Tests for the authentication role contract."""

import json

import pytest

from app.models import UserRole


def test_user_role_has_only_the_supported_roles() -> None:
    assert list(UserRole) == [UserRole.USER, UserRole.ADMIN]
    assert {role.value for role in UserRole} == {"USER", "ADMIN"}


@pytest.mark.parametrize("role", UserRole)
def test_user_role_is_string_and_json_serializable(role: UserRole) -> None:
    assert isinstance(role, str)
    assert str(role) == role.value
    assert json.dumps({"role": role}) == f'{{"role": "{role.value}"}}'


@pytest.mark.parametrize("value", ["MODERATOR", "user", "", "ADMINISTRATOR"])
def test_user_role_rejects_unknown_values(value: str) -> None:
    with pytest.raises(ValueError):
        UserRole(value)
