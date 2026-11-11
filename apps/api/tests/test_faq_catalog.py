"""Unified Admin catalog: effective content, search, pagination and ADMIN boundary."""

from collections.abc import AsyncIterator, Iterable
from datetime import UTC, datetime
from typing import NoReturn
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.schemas.managed_faq import Category, Faq, FaqContent, LocaleDraft, Publication
from app.services import managed_faq as repo
from app.services.chatbot.knowledge import KnowledgeUnavailable
from app.services.chatbot.managed import builtin_entries
from app.services.faq_catalog import CatalogPage, builtin_content, catalog_page
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair


def managed(
    number: int = 1,
    builtin_id: str | None = None,
    status: Publication = "draft",
    content: FaqContent | None = None,
) -> Faq:
    return Faq(
        id=UUID(int=number),
        builtin_id=builtin_id,
        version=3,
        draft_revision=3,
        published_revision=1 if status in ("pending", "published") else None,
        published_at=datetime(2026, 11, 11, tzinfo=UTC) if status != "draft" else None,
        updated_at=datetime(2026, 11, 11, tzinfo=UTC),
        status=status,
        content=content
        or FaqContent(
            category="student-life",
            en=LocaleDraft(questions=("Origami circle?",), answer="Fold paper."),
            de=LocaleDraft(questions=("Origami-Kreis?",), answer="Papier falten."),
        ),
    )


def catalog(
    rows: Iterable[tuple[Faq, FaqContent | None]] = (),
    search: str = "",
    category: Category | None = None,
    status: Publication | None = None,
    page: int = 1,
) -> CatalogPage:
    return catalog_page(list(rows), builtin_entries(), search, category, status, page)


def test_unified_and_prefilled_without_copying_verification() -> None:
    pages = [catalog([(managed(), None)], page=page) for page in (1, 2)]
    items = tuple(item for result in pages for item in result.items)
    assert len(items) == len(builtin_entries()) + 1
    for entry in builtin_entries():
        item = next(item for item in items if item.id == entry.id)
        assert item.builtin is not None
        assert item.builtin.content.en.questions == entry.en.questions
        assert item.content.en.answer == entry.en.answer
        assert item.content.de.answer == entry.de.answer
        assert item.sources == entry.sources
        assert item.status == ("published" if entry.authoritative else "unpublished")
        assert item.builtin.content.evidence == "unsupported"
        assert item.builtin.content.source_url == ""


@pytest.mark.parametrize("state", ["draft", "pending", "published", "unpublished"])
def test_replacement_is_one_identity_and_unpublish_exposes_original(state: Publication) -> None:
    entry = builtin_entries()[0]
    faq = managed(builtin_id=entry.id, status=state)
    public = FaqContent(
        source_title="VGU",
        source_url="https://vgu.edu.vn/",
        en=LocaleDraft(questions=("Published question?",), answer="Live answer"),
    )
    result = catalog([(faq, public if faq.published_revision else None)])
    assert len(result.items) + len(
        catalog([(faq, public if faq.published_revision else None)], page=2).items
    ) == len(builtin_entries())
    item = next(item for item in result.items if item.id == entry.id)
    assert item.managed == faq
    assert item.content == (public if faq.published_revision else builtin_content(entry))
    assert item.status == state


@pytest.mark.parametrize(
    "search", ["How do I register?", "HOW DO I", "Buddy Matching", "Wie registriere ich mich?"]
)
def test_builtin_questions_search(search: str) -> None:
    assert catalog(search=search).items


@pytest.mark.parametrize("search", ["origami", "Fold paper", "PAPIER FALTEN", "Origami-Kreis"])
def test_managed_questions_answers_and_bilingual_casefold(search: str) -> None:
    assert any(item.managed for item in catalog([(managed(), None)], search=search).items)


def test_published_and_pending_draft_answers_are_both_searchable() -> None:
    entry = builtin_entries()[0]
    faq = managed(builtin_id=entry.id, status="pending")
    public = FaqContent(
        source_title="VGU",
        source_url="https://vgu.edu.vn/",
        en=LocaleDraft(questions=("Public?",), answer="Live phrase"),
    )
    assert catalog([(faq, public)], search="live phrase").items[0].content == public
    matched = catalog([(faq, public)], search="fold paper").items[0].managed
    assert matched is not None and matched.content == faq.content
    assert catalog([(faq, public)], search=entry.en.questions[0]).items[0].id == entry.id


def test_filters_apply_before_pagination_with_stable_no_duplicate_ids() -> None:
    rows: list[tuple[Faq, FaqContent | None]] = [(managed(i), None) for i in range(1, 26)]
    first = catalog(rows, category="student-life", status="draft")
    second = catalog(rows, category="student-life", status="draft", page=2)
    assert len(first.items) == 20 and first.has_more
    assert len(second.items) == 5 and not second.has_more
    assert len({item.id for item in first.items + second.items}) == 25
    assert not catalog(rows, search="not present").items
    assert not catalog(rows, category="transportation", status="draft").items


@pytest.mark.anyio
async def test_catalog_query_joins_published_revision_in_one_snapshot() -> None:
    faq = managed(status="pending")
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())
    row = {**faq.model_dump(), "public_content": faq.content.model_dump()}
    session.execute.return_value.mappings.return_value.all.return_value = [row]
    assert await repo.catalog_rows(session) == [(faq, faq.content)]
    query = str(session.execute.call_args.args[0])
    assert "p.content AS public_content" in query
    assert "p.revision=f.published_revision" in query
    assert "r.revision=f.draft_revision" in query
    session.execute.assert_awaited_once()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_admin_catalog_transport_auth_bounds_no_store_and_source_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock()

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database
    app.dependency_overrides[get_auth_token_settings] = lambda: settings
    query = AsyncMock(return_value=[(managed(), None)])
    monkeypatch.setattr(repo, "catalog_rows", query)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            path = "/api/admin/knowledge-base/catalog"
            assert (await client.get(path)).status_code == 401
            for role, expected in [(UserRole.USER, 403), (UserRole.ADMIN, 200)]:
                session.scalar.return_value = User(
                    id=UUID(int=99),
                    email="fixture@example.invalid",
                    role=role,
                    is_active=True,
                    email_verified=True,
                )
                client.cookies.set(
                    DEVELOPMENT_ACCESS_COOKIE_NAME,
                    create_token_pair(UUID(int=99), role, settings).access_token,
                )
                response = await client.get(path)
                assert response.status_code == expected
                if expected == 403:
                    query.assert_not_awaited()
                else:
                    assert response.headers["cache-control"] == "private, no-store"
                    assert response.json()["items"][0]["builtin"]["content"]["en"]["answer"]
            assert (await client.get(path, params={"page": 0})).status_code == 422
            assert (await client.get(path, params={"search": "x" * 501})).status_code == 422

            def unavailable() -> NoReturn:
                raise KnowledgeUnavailable("unavailable")

            monkeypatch.setattr("app.api.admin_knowledge.builtin_entries", unavailable)
            response = await client.get(path)
            assert response.status_code == 503
            assert response.headers["cache-control"] == "private, no-store"
    finally:
        app.dependency_overrides.clear()
