"""Protect media when a durable commit loses its acknowledgement."""

import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.api import recaps
from app.models import User
from app.schemas.recap import RecapResponse
from app.services import recaps as service
from app.services.csrf import CsrfTokenClaims
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
)


@pytest.mark.parametrize("outcome", ["success", "uncertain_commit", "precommit_failure"])
def test_upload_compensation_respects_commit_boundary(
    monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    async def check() -> None:
        session = AsyncMock(spec=AsyncSession)
        storage = AsyncMock(spec=ImageStorageService)
        reference = StorageObjectRef(ImageBucket.EVENT_MEDIA, str(uuid4()) + ".webp")
        durable_refs: list[StorageObjectRef] = []

        async def commit() -> None:
            durable_refs.append(reference)
            if outcome == "uncertain_commit":
                raise OperationalError("COMMIT", {}, ConnectionError("acknowledgement lost"))

        async def stage(*args: object, staged: list[StorageObjectRef], **kwargs: object) -> None:
            staged.append(reference)
            if outcome == "precommit_failure":
                raise StorageOperationError("injected upload outage")

        session.commit.side_effect = commit
        monkeypatch.setattr(recaps, "RECAP_UPLOAD_GATE", asyncio.Semaphore(1))
        monkeypatch.setattr(service, "get_recap", AsyncMock(return_value=object()))
        monkeypatch.setattr(service, "upload_photo", stage)
        monkeypatch.setattr(service, "audit", AsyncMock())
        monkeypatch.setattr(
            service, "project", AsyncMock(return_value=cast(RecapResponse, object()))
        )
        monkeypatch.setattr(
            recaps,
            "read_multipart_image_upload",
            AsyncMock(
                return_value=SimpleNamespace(
                    fields={"version": "1", "alt_en": "Friends", "alt_de": "Freunde"},
                    content=b"validated elsewhere",
                    file_name="photo.jpg",
                    content_type="image/jpeg",
                )
            ),
        )
        call = recaps.upload_photo(
            uuid4(),
            cast(Request, object()),
            cast(User, object()),
            cast(CsrfTokenClaims, object()),
            cast(AsyncSession, session),
            cast(ImageStorageService, storage),
            uuid4(),
        )
        if outcome == "success":
            await call
        elif outcome == "uncertain_commit":
            with pytest.raises(OperationalError):
                await call
        else:
            with pytest.raises(HTTPException, match="Photo storage is unavailable"):
                await call
        assert len(durable_refs) == (0 if outcome == "precommit_failure" else 1)
        assert storage.delete_image.await_count == (1 if outcome == "precommit_failure" else 0)
        assert session.rollback.await_count == (0 if outcome == "success" else 1)

    asyncio.run(check())
