"""ADMIN-only draft, preview and publication workflow for chatbot FAQs."""

import asyncio
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role, require_session_csrf
from app.core.database import get_database_session
from app.models import User, UserRole
from app.schemas.chatbot import ChatbotResponse
from app.schemas.managed_faq import (
    Category,
    Confirm,
    CreateFaq,
    Faq,
    FaqContent,
    FaqPage,
    History,
    Preview,
    Publication,
    Restore,
    SaveFaq,
    Version,
)
from app.services import managed_faq as repo
from app.services.audit_logs import record_audit_log
from app.services.chatbot.knowledge import KnowledgeUnavailable
from app.services.chatbot.managed import (
    KnowledgeIssue,
    ManagedFaq,
    answer_with_managed,
    baseline_service,
    builtin_entries,
    validate_draft,
    validate_selection,
    validate_snapshot,
    validated_faq,
)
from app.services.chatbot.models import Contract, Question
from app.services.csrf import CsrfTokenClaims
from app.services.faq_catalog import CatalogPage, catalog_page

_PRIVATE = {"Cache-Control": "private, no-store", "Pragma": "no-cache"}
router = APIRouter(prefix="/api/admin/knowledge-base", tags=["admin-knowledge-base"])
Admin = Annotated[User, Depends(require_role(UserRole.ADMIN))]
Session = Annotated[AsyncSession, Depends(get_database_session)]
Csrf = Annotated[CsrfTokenClaims, Depends(require_session_csrf)]
_PREVIEW_SLOTS = asyncio.Semaphore(2)


class ReferenceEntry(Contract):
    id: str
    category: Category
    status: Literal["verified_code", "verified_official"]
    en: str
    de: str


class References(Contract):
    builtin: tuple[ReferenceEntry, ...]
    owner_guide: Literal["systemPrompt.txt"] = "systemPrompt.txt"


class PreviewResult(Contract):
    question: str
    answer: ChatbotResponse
    selected: Literal["draft", "existing", "fallback"]
    issue: str | None


def fail(status: int, code: str) -> HTTPException:
    return HTTPException(status, code, headers=_PRIVATE)


async def _required(session: AsyncSession, faq_id: UUID) -> Faq:
    faq = await repo.get_faq(session, faq_id)
    if faq is None:
        raise fail(404, "faq_not_found")
    return faq


def _builtin_id(value: str | None) -> None:
    if value is not None and not any(
        entry.id == value and entry.authoritative for entry in builtin_entries()
    ):
        raise fail(422, "invalid_builtin")


async def _locked(session: AsyncSession, faq_id: UUID, payload: Version) -> Faq:
    if await repo.lock_faq(session, faq_id) is None:
        raise fail(404, "faq_not_found")
    faq = await _required(session, faq_id)
    if faq.version != payload.version:
        raise fail(409, "stale_version")
    return faq


async def _finish(
    session: AsyncSession,
    actor: User,
    faq_id: UUID,
    action: str,
    version: int,
    revision: int,
) -> Faq:
    await record_audit_log(
        session,
        actor,
        action=f"knowledge.{action}",
        resource_type="managed_faq",
        resource_id=faq_id,
        new_value={"version": version, "revision": revision},
    )
    result = await _required(session, faq_id)
    await session.commit()
    return result


@router.get("")
async def list_faqs(
    response: Response,
    _admin: Admin,
    session: Session,
    search: Annotated[str, Query(max_length=100)] = "",
    category: Category | None = None,
    status: Publication | None = None,
    page: Annotated[int, Query(ge=1, le=5000)] = 1,
) -> FaqPage:
    response.headers.update(_PRIVATE)
    return await repo.list_faqs(session, search.strip(), category or "", status or "", page)


@router.get("/catalog")
async def catalog(
    response: Response,
    _admin: Admin,
    session: Session,
    search: Annotated[str, Query(max_length=500)] = "",
    category: Category | None = None,
    status: Publication | None = None,
    page: Annotated[int, Query(ge=1, le=5000)] = 1,
) -> CatalogPage:
    response.headers.update(_PRIVATE)
    try:
        return catalog_page(
            await repo.catalog_rows(session), builtin_entries(), search, category, status, page
        )
    except KnowledgeUnavailable:
        raise fail(503, "sources_unavailable") from None


@router.get("/references")
async def references(response: Response, _admin: Admin) -> References:
    response.headers.update(_PRIVATE)
    try:
        return References(
            builtin=tuple(
                ReferenceEntry(
                    id=e.id,
                    category=e.category,
                    status=e.status,
                    en=e.en.questions[0],
                    de=e.de.questions[0],
                )
                for e in builtin_entries()
                if e.status in ("verified_code", "verified_official")
            )
        )
    except KnowledgeUnavailable:
        raise fail(503, "sources_unavailable") from None


@router.post("", status_code=201)
async def create(
    payload: CreateFaq, response: Response, actor: Admin, _csrf: Csrf, session: Session
) -> Faq:
    response.headers.update(_PRIVATE)
    try:
        _builtin_id(payload.builtin_id)
        validate_draft(payload.content)
    except KnowledgeIssue as error:
        raise fail(422, str(error)) from None
    except KnowledgeUnavailable:
        raise fail(503, "sources_unavailable") from None
    faq_id = uuid4()
    if not await repo.insert_faq(session, faq_id, payload.builtin_id):
        raise fail(409, "builtin_conflict")
    await repo.add_revision(session, faq_id, 1, actor.id, payload.content)
    return await _finish(session, actor, faq_id, "create", 1, 1)


async def _bounded_preview(request: Request) -> Preview:
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise fail(415, "invalid_preview")
    body = bytearray()
    try:
        async with asyncio.timeout(2):
            async for chunk in request.stream():
                if len(body) + len(chunk) > 128 * 1024:
                    raise fail(413, "preview_too_large")
                body.extend(chunk)
        return Preview.model_validate_json(body)
    except ValidationError:
        raise fail(422, "invalid_preview") from None
    except TimeoutError:
        raise fail(408, "invalid_preview") from None


def _preview(
    question: str,
    content: FaqContent,
    faq_id: UUID,
    revision: int,
    builtin_id: str | None,
    live: tuple[ManagedFaq, ...],
) -> PreviewResult:
    issue = None
    candidate_id = None
    try:
        draft = validated_faq(faq_id, revision, builtin_id, content)
        candidates = validate_snapshot(tuple(item for item in live if item.id != faq_id) + (draft,))
        candidate_id = draft.citation_id
    except KnowledgeIssue as error:
        candidates = live
        issue = str(error)
    answer = answer_with_managed(baseline_service(), question, candidates)
    selected: Literal["draft", "existing", "fallback"] = "fallback"
    if any(source.entry_id == candidate_id for source in answer.sources):
        selected = "draft"
    elif answer.sources:
        selected = "existing"
        issue = issue or "retrieval_conflict"
    return PreviewResult(question=question, answer=answer, selected=selected, issue=issue)


@router.post("/preview")
async def preview(
    request: Request, response: Response, _admin: Admin, session: Session
) -> PreviewResult:
    response.headers.update(_PRIVATE)
    if _PREVIEW_SLOTS.locked():
        raise fail(429, "preview_busy")
    async with _PREVIEW_SLOTS:
        payload = await _bounded_preview(request)
        try:
            question = Question(text=payload.question).text
        except ValidationError:
            raise fail(422, "invalid_preview") from None
        faq = await _required(session, payload.faq_id) if payload.faq_id is not None else None
        try:
            _, live = await repo.published_snapshot(session)
            return await asyncio.to_thread(
                _preview,
                question,
                payload.content,
                faq.id if faq else uuid4(),
                faq.version + 1 if faq else 1,
                faq.builtin_id if faq else payload.builtin_id,
                live,
            )
        except (KnowledgeIssue, KnowledgeUnavailable):
            raise fail(503, "sources_unavailable") from None


@router.get("/{faq_id}")
async def detail(faq_id: UUID, response: Response, _admin: Admin, session: Session) -> Faq:
    response.headers.update(_PRIVATE)
    return await _required(session, faq_id)


@router.get("/{faq_id}/history")
async def history(
    faq_id: UUID,
    response: Response,
    _admin: Admin,
    session: Session,
    page: Annotated[int, Query(ge=1, le=5000)] = 1,
) -> History:
    response.headers.update(_PRIVATE)
    await _required(session, faq_id)
    return await repo.history(session, faq_id, page)


@router.put("/{faq_id}")
async def save(
    faq_id: UUID,
    payload: SaveFaq,
    response: Response,
    actor: Admin,
    _csrf: Csrf,
    session: Session,
) -> Faq:
    response.headers.update(_PRIVATE)
    try:
        validate_draft(payload.content)
    except KnowledgeIssue as error:
        raise fail(422, str(error)) from None
    faq = await _locked(session, faq_id, payload)
    version = faq.version + 1
    await repo.add_revision(session, faq_id, version, actor.id, payload.content)
    await repo.update_pointer(session, faq_id, version, version, faq.published_revision)
    return await _finish(session, actor, faq_id, "update", version, version)


async def _validate_publication(
    session: AsyncSession,
    faq: Faq,
    revision: int,
    content: FaqContent,
) -> None:
    try:
        draft = validated_faq(faq.id, revision, faq.builtin_id, content)
        _, live = await repo.published_snapshot(session)
        proposed = tuple(item for item in live if item.id != faq.id) + (draft,)
        await asyncio.to_thread(validate_selection, draft, validate_snapshot(proposed))
    except KnowledgeIssue as error:
        code = str(error)
        raise fail(409 if code.endswith("_conflict") else 422, code) from None
    except KnowledgeUnavailable:
        raise fail(503, "sources_unavailable") from None


@router.post("/{faq_id}/publish")
async def publish(
    faq_id: UUID,
    payload: Confirm,
    response: Response,
    actor: Admin,
    _csrf: Csrf,
    session: Session,
) -> Faq:
    response.headers.update(_PRIVATE)
    await repo.generation(session, lock=True)
    faq = await _locked(session, faq_id, payload)
    if faq.published_revision == faq.draft_revision:
        raise fail(409, "already_published")
    await _validate_publication(session, faq, faq.draft_revision, faq.content)
    version = faq.version + 1
    await repo.update_pointer(
        session, faq_id, version, faq.draft_revision, faq.draft_revision, actor.id
    )
    await repo.bump_generation(session)
    return await _finish(session, actor, faq_id, "publish", version, faq.draft_revision)


@router.post("/{faq_id}/unpublish")
async def unpublish(
    faq_id: UUID,
    payload: Confirm,
    response: Response,
    actor: Admin,
    _csrf: Csrf,
    session: Session,
) -> Faq:
    response.headers.update(_PRIVATE)
    await repo.generation(session, lock=True)
    faq = await _locked(session, faq_id, payload)
    if faq.published_revision is None:
        raise fail(409, "not_published")
    version = faq.version + 1
    await repo.update_pointer(session, faq_id, version, faq.draft_revision, None)
    await repo.bump_generation(session)
    return await _finish(session, actor, faq_id, "unpublish", version, faq.published_revision)


@router.post("/{faq_id}/restore")
async def restore(
    faq_id: UUID,
    payload: Restore,
    response: Response,
    actor: Admin,
    _csrf: Csrf,
    session: Session,
) -> Faq:
    response.headers.update(_PRIVATE)
    if payload.publish:
        if not payload.confirm:
            raise fail(422, "confirmation_required")
        await repo.generation(session, lock=True)
    faq = await _locked(session, faq_id, payload)
    content = await repo.revision_content(session, faq_id, payload.revision)
    if content is None:
        raise fail(404, "revision_not_found")
    version = faq.version + 1
    if payload.publish:
        await _validate_publication(session, faq, version, content)
    else:
        try:
            validate_draft(content)
        except KnowledgeIssue as error:
            raise fail(422, str(error)) from None
    await repo.add_revision(session, faq_id, version, actor.id, content)
    await repo.update_pointer(
        session,
        faq_id,
        version,
        version,
        version if payload.publish else faq.published_revision,
        actor.id if payload.publish else None,
    )
    if payload.publish:
        await repo.bump_generation(session)
    return await _finish(session, actor, faq_id, "restore", version, version)
