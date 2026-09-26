"""Auth, localization, CSRF, and transport tests for profile catalog APIs."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.profile_catalogs as catalog_api
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import Activity, Interest, Language, LanguageProficiency, User, UserRole
from app.schemas.profile_catalog import (
    CustomLanguageSelection,
    CustomPreferenceSelection,
    ProfileLanguageSelection,
    ProfileLanguageUpdate,
)
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.profile_catalogs import (
    ProfileInterestMutation,
    ProfileLanguageMutation,
    ProfilePreferenceSnapshot,
)
from app.services.profiles import ProfileValidationError, ProfileVersionConflictError
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
INTEREST_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
ACTIVITY_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _auth_settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _csrf_settings() -> CsrfSettings:
    return CsrfSettings(
        signing_key=SecretBytes(SIGNING_KEY),
        secure_cookies=False,
        trusted_origins=("http://testserver",),
    )


def _user(*, role: UserRole = UserRole.USER) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=True,
    )


def _session(actor: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=actor)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install(
    session: AsyncSession,
    *,
    token_role: UserRole = UserRole.USER,
) -> tuple[dict[str, str], dict[str, str]]:
    auth_settings = _auth_settings()
    csrf_settings = _csrf_settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: auth_settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    pair = create_token_pair(USER_ID, token_role, auth_settings)
    csrf = create_session_csrf_token(pair.session_id, csrf_settings)
    return (
        {
            DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
            csrf_cookie_name(csrf_settings): csrf.value,
        },
        {"Origin": "http://testserver", CSRF_HEADER_NAME: csrf.value},
    )


@pytest.mark.anyio
async def test_interest_catalog_localizes_active_items_for_authenticated_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_user())
    cookies, _headers = _install(session)
    interest = Interest(
        id=INTEREST_ID,
        code="music",
        label_en="Music",
        label_de="Musik",
        category="culture",
    )
    service = AsyncMock(return_value=(interest,))
    monkeypatch.setattr(catalog_api, "list_active_interests", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/interests?locale=de")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "locale": "de",
        "items": [
            {
                "id": str(INTEREST_ID),
                "code": "music",
                "label": "Musik",
                "category": "culture",
            }
        ],
    }
    service.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_language_catalog_is_available_to_authenticated_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_user(role=UserRole.ADMIN))
    cookies, _headers = _install(session, token_role=UserRole.ADMIN)
    language = Language(code="de", label_en="German", label_de="Deutsch")
    service = AsyncMock(return_value=(language,))
    monkeypatch.setattr(catalog_api, "list_active_languages", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/languages")

    assert response.status_code == 200
    assert response.json() == {
        "locale": "en",
        "items": [{"code": "de", "label": "German"}],
    }
    service.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_anonymous_catalog_read_stops_before_service(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AsyncMock()
    monkeypatch.setattr(catalog_api, "list_active_interests", service)
    app.dependency_overrides[get_auth_token_settings] = _auth_settings

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/interests")

    assert response.status_code == 401
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_interest_update_is_owner_bound_committed_and_returns_new_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user()
    mock, session = _session(actor)
    cookies, headers = _install(session)
    service = AsyncMock(
        return_value=ProfileInterestMutation(
            version=4,
            interest_ids=(INTEREST_ID,),
        )
    )
    monkeypatch.setattr(catalog_api, "replace_own_interests", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile/interests",
            headers=headers,
            json={"version": 3, "interest_ids": [str(INTEREST_ID)]},
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "version": 4,
        "interest_ids": [str(INTEREST_ID)],
    }
    service.assert_awaited_once()
    await_args = service.await_args
    assert await_args is not None
    assert await_args.args[0:2] == (session, actor)
    assert await_args.args[2].version == 3
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_language_update_returns_normalized_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user()
    mock, session = _session(actor)
    cookies, headers = _install(session)
    selection = ProfileLanguageUpdate.model_validate(
        {
            "version": 4,
            "languages": [{"language_code": "en", "proficiency": "fluent"}],
        }
    ).languages[0]
    service = AsyncMock(
        return_value=ProfileLanguageMutation(
            version=5,
            languages=(selection,),
        )
    )
    monkeypatch.setattr(catalog_api, "replace_own_languages", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile/languages",
            headers=headers,
            json={
                "version": 4,
                "languages": [{"language_code": "en", "proficiency": "fluent"}],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "version": 5,
        "languages": [{"language_code": "en", "proficiency": "fluent"}],
    }
    service.assert_awaited_once()
    await_args = service.await_args
    assert await_args is not None
    assert await_args.args[0:2] == (session, actor)
    mock.commit.assert_awaited_once_with()


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["interests", "languages"])
async def test_relation_mutations_require_session_csrf(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_user())
    cookies, _headers = _install(session)
    interest_service = AsyncMock()
    language_service = AsyncMock()
    monkeypatch.setattr(catalog_api, "replace_own_interests", interest_service)
    monkeypatch.setattr(catalog_api, "replace_own_languages", language_service)
    payload = (
        {"version": 1, "interest_ids": []}
        if path == "interests"
        else {
            "version": 1,
            "languages": [],
        }
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(f"/api/profile/{path}", json=payload)

    assert response.status_code == 403
    interest_service.assert_not_awaited()
    language_service.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_cannot_update_student_relations(monkeypatch: pytest.MonkeyPatch) -> None:
    _, session = _session(_user(role=UserRole.ADMIN))
    cookies, headers = _install(session, token_role=UserRole.ADMIN)
    service = AsyncMock()
    monkeypatch.setattr(catalog_api, "replace_own_interests", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile/interests",
            headers=headers,
            json={"version": 1, "interest_ids": []},
        )

    assert response.status_code == 403
    service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected_status", "detail"),
    [
        (ProfileVersionConflictError("private version"), 409, "Profile version is stale."),
        (ProfileValidationError("private catalog id"), 422, "Profile interests are invalid."),
    ],
)
async def test_interest_update_maps_domain_errors_and_rolls_back(
    error: Exception,
    expected_status: int,
    detail: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    cookies, headers = _install(session)
    monkeypatch.setattr(catalog_api, "replace_own_interests", AsyncMock(side_effect=error))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile/interests",
            headers=headers,
            json={"version": 1, "interest_ids": []},
        )

    assert response.status_code == expected_status
    assert response.json() == {"detail": detail}
    assert "private" not in response.text
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_relation_commit_failure_rolls_back_without_success_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    mock.commit.side_effect = RuntimeError("database unavailable")
    cookies, headers = _install(session)
    monkeypatch.setattr(
        catalog_api,
        "replace_own_interests",
        AsyncMock(
            return_value=ProfileInterestMutation(
                version=2,
                interest_ids=(),
            )
        ),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        with pytest.raises(RuntimeError, match="database unavailable"):
            await client.put(
                "/api/profile/interests",
                headers=headers,
                json={"version": 1, "interest_ids": []},
            )

    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {
            "version": 1,
            "languages": [
                {"language_code": "en", "proficiency": "native"},
                {"language_code": "en", "proficiency": "fluent"},
            ],
        },
        {
            "version": 1,
            "languages": [{"language_code": "en", "proficiency": "expert"}],
        },
        {"version": 1, "languages": [], "user_id": str(USER_ID)},
    ],
)
async def test_invalid_language_payload_fails_before_service(
    payload: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_user())
    cookies, headers = _install(session)
    service = AsyncMock()
    monkeypatch.setattr(catalog_api, "replace_own_languages", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put("/api/profile/languages", headers=headers, json=payload)

    assert response.status_code == 422
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_openapi_exposes_bounded_catalog_and_relation_contracts() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    assert set(document["paths"]["/api/interests"]) == {"get"}
    assert set(document["paths"]["/api/languages"]) == {"get"}
    assert set(document["paths"]["/api/activities"]) == {"get"}
    assert set(document["paths"]["/api/profile/interests"]) == {"put"}
    assert set(document["paths"]["/api/profile/languages"]) == {"put"}
    assert set(document["paths"]["/api/profile/activities"]) == {"put"}
    assert set(document["paths"]["/api/profile/preferences"]) == {"get", "put"}
    interest_update = document["components"]["schemas"]["ProfileInterestUpdate"]
    language_update = document["components"]["schemas"]["ProfileLanguageUpdate"]
    assert interest_update["properties"]["interest_ids"]["maxItems"] == 20
    assert language_update["properties"]["languages"]["maxItems"] == 10
    preference_update = document["components"]["schemas"]["ProfilePreferenceUpdate"]
    assert preference_update["properties"]["custom_interests"]["maxItems"] == 20
    assert preference_update["properties"]["custom_languages"]["maxItems"] == 10
    assert preference_update["properties"]["custom_activities"]["maxItems"] == 20
    profile_fields = document["components"]["schemas"]["OwnProfileResponse"]["properties"]
    assert {"interest_ids", "languages"}.issubset(profile_fields)
    assert {"user_id", "role", "password_hash"}.isdisjoint(profile_fields)


@pytest.mark.anyio
async def test_activity_catalog_uses_independent_selectable_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_user())
    cookies, _headers = _install(session)
    activity = Activity(
        id=ACTIVITY_ID,
        code="hiking",
        label_en="Hiking",
        label_de="Wandern",
    )
    service = AsyncMock(return_value=(activity,))
    monkeypatch.setattr(catalog_api, "list_active_activities", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/activities?locale=de")

    assert response.status_code == 200
    assert response.json() == {
        "locale": "de",
        "items": [
            {
                "id": str(ACTIVITY_ID),
                "code": "hiking",
                "label": "Wandern",
            }
        ],
    }
    service.assert_awaited_once_with(session)


def _preference_snapshot(*, version: int = 4) -> ProfilePreferenceSnapshot:
    return ProfilePreferenceSnapshot(
        version=version,
        interest_ids=(INTEREST_ID,),
        custom_interests=(CustomPreferenceSelection(label="Formula 1"),),
        languages=(
            ProfileLanguageSelection(
                language_code="de",
                proficiency=LanguageProficiency.FLUENT,
            ),
        ),
        custom_languages=(
            CustomLanguageSelection(
                label="Swiss German",
                proficiency=LanguageProficiency.INTERMEDIATE,
            ),
        ),
        activity_ids=(ACTIVITY_ID,),
        custom_activities=(CustomPreferenceSelection(label="Night Kayaking"),),
    )


def _preference_payload() -> dict[str, object]:
    return {
        "version": 3,
        "interest_ids": [str(INTEREST_ID)],
        "custom_interests": [{"label": "Formula 1"}],
        "languages": [{"language_code": "de", "proficiency": "fluent"}],
        "custom_languages": [
            {"label": "Swiss German", "proficiency": "intermediate"}
        ],
        "activity_ids": [str(ACTIVITY_ID)],
        "custom_activities": [{"label": "Night Kayaking"}],
    }


@pytest.mark.anyio
async def test_owner_combined_preference_update_commits_typed_safe_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user()
    mock, session = _session(actor)
    cookies, headers = _install(session)
    service = AsyncMock(return_value=_preference_snapshot())
    monkeypatch.setattr(catalog_api, "replace_own_preferences", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile/preferences",
            headers=headers,
            json=_preference_payload(),
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "version": 4,
        "interest_ids": [str(INTEREST_ID)],
        "custom_interests": [{"label": "Formula 1"}],
        "languages": [{"language_code": "de", "proficiency": "fluent"}],
        "custom_languages": [
            {"label": "Swiss German", "proficiency": "intermediate"}
        ],
        "activity_ids": [str(ACTIVITY_ID)],
        "custom_activities": [{"label": "Night Kayaking"}],
    }
    assert "normalized" not in response.text
    service.assert_awaited_once()
    await_args = service.await_args
    assert await_args is not None
    assert await_args.args[0:2] == (session, actor)
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_owner_reads_complete_preference_projection_without_csrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user()
    mock, session = _session(actor)
    cookies, _headers = _install(session)
    service = AsyncMock(return_value=_preference_snapshot())
    monkeypatch.setattr(catalog_api, "get_own_preference_snapshot", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/profile/preferences")

    assert response.status_code == 200
    assert response.json()["custom_languages"] == [
        {"label": "Swiss German", "proficiency": "intermediate"}
    ]
    assert "normalized_key" not in response.text
    service.assert_awaited_once_with(session, actor)
    mock.commit.assert_awaited_once_with()


@pytest.mark.anyio
async def test_combined_preference_mutation_requires_valid_csrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_user())
    cookies, _headers = _install(session)
    service = AsyncMock()
    monkeypatch.setattr(catalog_api, "replace_own_preferences", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile/preferences",
            json=_preference_payload(),
        )

    assert response.status_code == 403
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_duplicate_error_is_stable_and_does_not_leak_internal_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    cookies, headers = _install(session)
    service = AsyncMock(
        side_effect=ProfileValidationError(
            "normalized_key violates uq_profile_custom_preferences_profile_kind_key"
        )
    )
    monkeypatch.setattr(catalog_api, "replace_own_preferences", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile/preferences",
            headers=headers,
            json=_preference_payload(),
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Profile preferences are invalid."}
    assert "normalized_key" not in response.text
    assert "uq_profile" not in response.text
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_non_user_and_anonymous_cannot_access_owner_preference_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_user(role=UserRole.ADMIN))
    admin_cookies, admin_headers = _install(session, token_role=UserRole.ADMIN)
    service = AsyncMock()
    monkeypatch.setattr(catalog_api, "replace_own_preferences", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=admin_cookies
    ) as client:
        admin_response = await client.put(
            "/api/profile/preferences",
            headers=admin_headers,
            json=_preference_payload(),
        )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        anonymous_response = await client.put(
            "/api/profile/preferences",
            json=_preference_payload(),
        )

    assert admin_response.status_code == 403
    assert anonymous_response.status_code == 401
    service.assert_not_awaited()
