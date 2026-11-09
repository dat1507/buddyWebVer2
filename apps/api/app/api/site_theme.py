"""Read and publish the single site appearance preset."""

from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role, require_session_csrf
from app.core.database import get_database_session
from app.models import User, UserRole
from app.services.audit_logs import record_audit_log
from app.services.csrf import CsrfTokenClaims

ThemeId = Literal["default", "halloween", "christmas", "summer", "tet"]
Session = Annotated[AsyncSession, Depends(get_database_session)]
Admin = Annotated[User, Depends(require_role(UserRole.ADMIN))]
Csrf = Annotated[CsrfTokenClaims, Depends(require_session_csrf)]
router = APIRouter(prefix="/api", tags=["site-theme"])

_READ = "SELECT theme FROM app_private.site_theme WHERE singleton"
_SEED = "INSERT INTO app_private.site_theme (theme) VALUES ('default') ON CONFLICT DO NOTHING"


class SiteTheme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: ThemeId


@router.get("/public/site-theme", response_model=SiteTheme)
async def public_site_theme(response: Response, session: Session) -> SiteTheme:
    response.headers["Cache-Control"] = "no-store"
    theme = await session.scalar(text(_READ))
    return SiteTheme(theme=cast(ThemeId, theme or "default"))


@router.get("/admin/site-theme", response_model=SiteTheme)
async def admin_site_theme(response: Response, _admin: Admin, session: Session) -> SiteTheme:
    setting = await public_site_theme(response, session)
    response.headers["Cache-Control"] = "private, no-store"
    return setting


@router.put("/admin/site-theme", response_model=SiteTheme)
async def publish_site_theme(
    payload: SiteTheme, response: Response, admin: Admin, _csrf: Csrf, session: Session
) -> SiteTheme:
    await session.execute(text(_SEED))
    previous = (await session.execute(text(_READ + " FOR UPDATE"))).scalar_one()
    if previous != payload.theme:
        await session.execute(
            text("UPDATE app_private.site_theme SET theme = :theme WHERE singleton"),
            {"theme": payload.theme},
        )
        await record_audit_log(
            session,
            admin,
            action="site_theme.publish",
            resource_type="site_theme",
            resource_id=UUID("772e8c9b-8d77-4485-acd4-b0dd8c8ea704"),
            old_value={"theme": previous},
            new_value={"theme": payload.theme},
        )
    await session.commit()
    response.headers["Cache-Control"] = "private, no-store"
    return payload
