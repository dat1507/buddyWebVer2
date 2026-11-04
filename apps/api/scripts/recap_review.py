"""Opt-in loopback review using a dedicated local DB and existing local Supabase Storage.

Run only with scripts/review-recaps.mjs. No fixture is imported by app.main or production builds.
Secrets arrive through an ignored Docker env file, never CLI arguments or evidence.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.dependencies import get_image_storage_service
from app.core.config import StorageSettings
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.models.recap import Recap
from app.schemas.recap import RecapContent
from app.services import recaps
from app.services.image_storage import ImageStorageService, SupabaseStorageTransport
from app.services.passwords import hash_password

ORIGIN = os.environ.get("RECAP_REVIEW_ORIGIN", "https://127.0.0.1:5197")
if ORIGIN not in {"https://127.0.0.1:5197", "https://127.0.0.1:5198", "https://127.0.0.1:5199"}:
    raise RuntimeError("Review origin must be loopback")
private = Path("/workspace/.local/recap-review")
url = make_url(os.environ["RECAP_TEST_DATABASE_URL"])
if url.host != "buddy-recap-db" or url.database != "buddy_recap_local":
    raise RuntimeError("Refusing a non-local Recap database")


class LocalStorageTransport(SupabaseStorageTransport):
    def _url(self, operation: str, *segments: str) -> str:
        # Local-only bridge. Signed responses still use the HTTPS origin checked by the
        # production transport; the review Vite server proxies them to local Kong.
        return (
            super()
            ._url(operation, *segments)
            .replace(ORIGIN, "http://host.docker.internal:54321", 1)
        )


storage = ImageStorageService(
    LocalStorageTransport(
        StorageSettings(url=ORIGIN, secret_key=SecretStr(os.environ["SUPABASE_SECRET_KEY"]))
    )
)
runtime_url = url.set(username="vgu_buddy_runtime", password=os.environ["RUNTIME_PASSWORD"])
engine = create_async_engine(runtime_url, hide_parameters=True)
factory = async_sessionmaker(engine, expire_on_commit=False)


async def database_session():
    async with factory() as session:
        yield session


app.dependency_overrides[get_database_session] = database_session
app.dependency_overrides[get_image_storage_service] = lambda: storage


async def seed() -> None:
    admin_engine = create_async_engine(url, hide_parameters=True)
    async with admin_engine.begin() as connection:
        # Password never reaches command arguments, logs, source control or evidence.
        await connection.exec_driver_sql(
            "ALTER ROLE vgu_buddy_runtime PASSWORD '" + os.environ["RUNTIME_PASSWORD"] + "'"
        )
    await admin_engine.dispose()
    async with factory() as session:
        user = await session.scalar(
            select(User).where(User.email == "recap-review@example.invalid")
        )
        if user is None:
            import secrets

            password = secrets.token_urlsafe(24)
            user = User(
                id=uuid4(),
                email="recap-review@example.invalid",
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            await session.commit()
            (private / "login.json").write_text(
                json.dumps({"email": user.email, "password": password})
            )
        # Never reseed nine published fixtures after the original welcome recap is evicted.
        existing = await session.scalar(select(Recap.id).limit(1))
        if existing:
            return
        names = [
            ("Welcome to the Buddy community", "Willkommen in der Buddy-Community"),
            ("A day on campus", "Ein Tag auf dem Campus"),
            ("Our green corner of VGU", "Unsere grüne Ecke der VGU"),
            ("Discovering new perspectives", "Neue Perspektiven entdecken"),
            ("An afternoon together", "Ein gemeinsamer Nachmittag"),
            ("A place to belong", "Ein Ort zum Ankommen"),
            ("The start of something good", "Der Anfang von etwas Schönem"),
            ("Little moments, lasting memories", "Kleine Momente, bleibende Erinnerungen"),
            ("Exploring VGU together", "Gemeinsam die VGU entdecken"),
        ]
        sources = list(Path("/workspace/apps/web/src/assets/landing-backgrounds").glob("*.webp"))
        for index, (en, de) in enumerate(names):
            recap = await recaps.save_content(
                session,
                user,
                RecapContent(
                    title_en=en + " · local review",
                    title_de=de + " · lokale Vorschau",
                    summary_en="Campus discoveries and shared moments. Isolated review content from existing repository images.",
                    summary_de="Entdeckungen auf dem Campus und gemeinsame Momente. Isolierte Vorschau mit vorhandenen Bildern aus dem Repository.",
                    event_date=date(2026, 10 if index < 5 else 9, 25 - index),
                ),
            )
            for photo_index in range(3 if index < 5 else 1):
                source = sources[(index + photo_index) % len(sources)]
                await recaps.upload_photo(
                    session,
                    storage,
                    user,
                    recap,
                    upload_id=uuid4(),
                    version=recap.version,
                    content=source.read_bytes(),
                    original_name=source.name,
                    content_type="image/webp",
                    alt_en="VGU campus buildings and gardens in daylight",
                    alt_de="Gebäude und Gärten des VGU-Campus bei Tageslicht",
                    staged=[],
                )
            await recaps.validate_publication(session, recap)
            recap.status = "PUBLISHED"
            recap.first_published_at = datetime.now(UTC)
            await session.commit()
        (private / "public.json").write_text(
            json.dumps(
                {
                    "gallery": ORIGIN + "/events/recap",
                    "detail": ORIGIN + "/events/recap/" + str(recap.id),
                    "admin": ORIGIN + "/admin/events/recaps",
                }
            )
        )


original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def review_lifespan(application):
    async with original_lifespan(application):
        await seed()
        yield
        await engine.dispose()


app.router.lifespan_context = review_lifespan
