"""Start the real local API with synthetic review accounts on a disposable database."""

import asyncio
import base64
import os
from datetime import UTC, datetime

import uvicorn
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from app.models import User, UserRole
from app.services.passwords import hash_password

DATABASE = "buddy_theme_local"
BASE = f"127.0.0.1:64740/{DATABASE}"
MIGRATION_URL = f"postgresql+asyncpg://postgres:local-only@{BASE}"
PASSWORD = "ThemeReview!2026"


async def seed() -> None:
    engine = create_async_engine(MIGRATION_URL)
    factory = async_sessionmaker(engine)
    try:
        async with factory() as session:
            if await session.scalar(text("SELECT current_database()")) != DATABASE:
                raise RuntimeError("Review database mismatch")
            for email, role in (
                ("theme-admin@example.invalid", UserRole.ADMIN),
                ("theme-user@example.invalid", UserRole.USER),
            ):
                if not await session.scalar(select(User.id).where(User.email == email)):
                    session.add(
                        User(
                            email=email,
                            password_hash=hash_password(PASSWORD),
                            role=role,
                            is_active=True,
                            email_verified_at=datetime.now(UTC),
                        )
                    )
            await session.commit()
    finally:
        await engine.dispose()


def main() -> None:
    os.environ.update(
        APP_ENV="local",
        DATABASE_URL=f"postgresql+asyncpg://vgu_buddy_runtime:local-only@{BASE}",
        DATABASE_MIGRATION_URL=MIGRATION_URL,
        AUTH_COOKIE_SECURE="false",
        AUTH_JWT_SECRET=base64.urlsafe_b64encode(os.urandom(32)).decode(),
        AUTH_CSRF_SECRET=base64.urlsafe_b64encode(os.urandom(32)).decode(),
        CORS_ALLOWED_ORIGINS="http://127.0.0.1:5231,http://localhost:5231",
        RATE_LIMIT_STORAGE_URI="memory://",
        REDIS_URL="redis://127.0.0.1:64741/0",
        SUPABASE_URL="http://127.0.0.1:9",
        SUPABASE_SECRET_KEY="local-review-only",
        RESEND_API_KEY="",
        CHATBOT_API_ENABLED="true",
        CHATBOT_AI_ENABLED="false",
    )
    config = Config(toml_file="pyproject.toml")
    command.upgrade(config, "head")
    asyncio.run(seed())
    uvicorn.run("app.main:app", host="127.0.0.1", port=5232, access_log=False)


if __name__ == "__main__":
    main()
