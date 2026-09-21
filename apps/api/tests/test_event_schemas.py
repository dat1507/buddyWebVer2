"""Validation and least-data projection tests for EVT-004 Event contracts."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models import Event, EventPhase, EventStatus, EventVisibility
from app.schemas.event import (
    AdminEventResponse,
    EventDraftCreate,
    EventDraftUpdate,
    EventStatusUpdate,
)

EVENT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
ADMIN_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


def test_empty_draft_uses_private_defaults_and_permits_incomplete_content() -> None:
    draft = EventDraftCreate.model_validate({})

    assert draft.title_en is None
    assert draft.description_de is None
    assert draft.start_date is None
    assert draft.timezone == "Asia/Ho_Chi_Minh"
    assert draft.visibility is EventVisibility.MEMBERS
    assert draft.registration_enabled is False


def test_event_content_is_trimmed_and_requires_aware_ordered_https_values() -> None:
    draft = EventDraftCreate.model_validate(
        {
            "title_en": "  Welcome  ",
            "description_de": "  Beschreibung  ",
            "timezone": "  Europe/Berlin  ",
            "registration_url": "  https://events.example/register  ",
            "start_date": "2026-10-01T08:00:00+02:00",
            "end_date": "2026-10-01T10:00:00+02:00",
            "registration_deadline": "2026-10-01T07:00:00+02:00",
        }
    )

    assert draft.title_en == "Welcome"
    assert draft.description_de == "Beschreibung"
    assert draft.timezone == "Europe/Berlin"
    assert draft.registration_url == "https://events.example/register"

    with pytest.raises(ValidationError, match="timezone-aware"):
        EventDraftCreate.model_validate({"start_date": "2026-10-01T08:00:00"})
    with pytest.raises(ValidationError, match="later than start"):
        EventDraftCreate.model_validate(
            {
                "start_date": "2026-10-01T10:00:00Z",
                "end_date": "2026-10-01T08:00:00Z",
            }
        )
    with pytest.raises(ValidationError, match="absolute HTTPS"):
        EventDraftCreate.model_validate({"registration_url": "http://events.example"})


def test_partial_update_requires_version_and_one_allowlisted_change() -> None:
    update = EventDraftUpdate.model_validate(
        {"version": 2, "title_en": " Updated ", "cover_media_id": None}
    )

    assert update.title_en == "Updated"
    assert update.model_fields_set == {"version", "title_en", "cover_media_id"}
    with pytest.raises(ValidationError, match="At least one Event field"):
        EventDraftUpdate.model_validate({"version": 2})
    with pytest.raises(ValidationError, match="Extra inputs"):
        EventDraftUpdate.model_validate({"version": 2, "created_by": str(ADMIN_ID)})


def test_status_update_accepts_only_declared_editorial_values() -> None:
    update = EventStatusUpdate.model_validate({"version": 3, "status": "PUBLISHED"})

    assert update.status is EventStatus.PUBLISHED
    with pytest.raises(ValidationError):
        EventStatusUpdate.model_validate({"version": 3, "status": "COMPLETED"})


def test_admin_projection_omits_actor_and_storage_data_and_derives_phase() -> None:
    start = datetime(2026, 1, 1, 8, tzinfo=UTC)
    end = datetime(2026, 1, 1, 10, tzinfo=UTC)
    event = Event(
        id=EVENT_ID,
        title_en="Welcome",
        title_de="Willkommen",
        description_en="Description",
        description_de="Beschreibung",
        start_date=start,
        end_date=end,
        timezone="Asia/Ho_Chi_Minh",
        location_en="Campus",
        location_de="Campus",
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
        status=EventStatus.PUBLISHED,
        visibility=EventVisibility.PUBLIC,
        registration_enabled=False,
        version=4,
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        updated_at=datetime(2026, 9, 2, tzinfo=UTC),
    )

    response = AdminEventResponse.model_validate(event)
    payload = response.model_dump()

    assert response.id == EVENT_ID
    assert response.phase is EventPhase.COMPLETED
    assert "created_by" not in payload
    assert "updated_by" not in payload
    assert "object_key" not in payload
    assert "signed_url" not in payload
