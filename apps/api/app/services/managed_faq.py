"""Transactional private FAQ repository. Every revision is append-only."""

from uuid import UUID

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.managed_faq import Faq, FaqContent, FaqPage, History, Revision
from app.services.chatbot.managed import MAX_PUBLISHED, KnowledgeIssue, ManagedFaq, from_row

STATE = "app_private.managed_faq_state"
FAQ = "app_private.managed_faq"
REV = "app_private.managed_faq_revision"
PAGE_SIZE = 20
STATUS = """CASE WHEN f.published_revision IS NOT NULL
    THEN CASE WHEN f.published_revision=f.draft_revision THEN 'published' ELSE 'pending' END
    WHEN f.published_at IS NOT NULL THEN 'unpublished' ELSE 'draft' END"""
PROJECTION = f"""SELECT f.id, f.builtin_id, f.version, f.draft_revision,
    f.published_revision, f.published_at, f.updated_at, {STATUS} AS status, r.content
    FROM {FAQ} f JOIN {REV} r ON r.faq_id=f.id AND r.revision=f.draft_revision"""


async def get_faq(session: AsyncSession, faq_id: UUID) -> Faq | None:
    row = (
        (await session.execute(text(PROJECTION + " WHERE f.id=:id"), {"id": faq_id}))
        .mappings()
        .first()
    )
    return Faq.model_validate(dict(row)) if row is not None else None


async def list_faqs(
    session: AsyncSession,
    search: str,
    category: str,
    status: str,
    page: int,
) -> FaqPage:
    rows = (
        (
            await session.execute(
                text(
                    PROJECTION
                    + f"""
        WHERE (:category='' OR r.content->>'category'=:category)
        AND (:status='' OR ({STATUS})=:status)
        AND (:search='' OR strpos(lower(concat_ws(' ', r.content #>> '{{en,questions}}',
            r.content #>> '{{de,questions}}', r.content->>'source_title',
            f.builtin_id)), lower(:search)) > 0)
        ORDER BY f.updated_at DESC, f.id DESC LIMIT :limit OFFSET :offset
    """
                ),
                dict(
                    search=search,
                    category=category,
                    status=status,
                    limit=PAGE_SIZE + 1,
                    offset=(page - 1) * PAGE_SIZE,
                ),
            )
        )
        .mappings()
        .all()
    )
    return FaqPage(
        items=tuple(Faq.model_validate(dict(row)) for row in rows[:PAGE_SIZE]),
        has_more=len(rows) > PAGE_SIZE,
    )


async def catalog_rows(session: AsyncSession) -> list[tuple[Faq, FaqContent | None]]:
    """One consistent snapshot of draft identities and their effective published content."""
    rows = (
        (
            await session.execute(
                text(
                    PROJECTION.replace("r.content\n", "r.content, p.content AS public_content\n")
                    + f" LEFT JOIN {REV} p ON p.faq_id=f.id AND p.revision=f.published_revision"
                    + " ORDER BY f.updated_at DESC, f.id DESC"
                )
            )
        )
        .mappings()
        .all()
    )
    return [
        (
            Faq.model_validate(
                {key: value for key, value in row.items() if key != "public_content"}
            ),
            FaqContent.model_validate(row["public_content"]) if row["public_content"] else None,
        )
        for row in rows
    ]


async def history(session: AsyncSession, faq_id: UUID, page: int) -> History:
    rows = (
        (
            await session.execute(
                text(f"""SELECT revision, author_id, created_at, content
        FROM {REV} WHERE faq_id=:id ORDER BY revision DESC LIMIT :limit OFFSET :offset"""),
                dict(id=faq_id, limit=PAGE_SIZE + 1, offset=(page - 1) * PAGE_SIZE),
            )
        )
        .mappings()
        .all()
    )
    return History(
        items=tuple(Revision.model_validate(dict(row)) for row in rows[:PAGE_SIZE]),
        has_more=len(rows) > PAGE_SIZE,
    )


async def revision_content(
    session: AsyncSession,
    faq_id: UUID,
    revision: int,
) -> FaqContent | None:
    data = await session.scalar(
        text(f"SELECT content FROM {REV} WHERE faq_id=:id AND revision=:rev"),
        dict(id=faq_id, rev=revision),
    )
    return FaqContent.model_validate(data) if data is not None else None


async def insert_faq(session: AsyncSession, faq_id: UUID, builtin_id: str | None) -> bool:
    value = await session.scalar(
        text(f"""INSERT INTO {FAQ}(id,builtin_id,version,draft_revision)
        VALUES (:id,:builtin,1,1) ON CONFLICT (builtin_id) DO NOTHING RETURNING id"""),
        dict(id=faq_id, builtin=builtin_id),
    )
    return value is not None


async def lock_faq(session: AsyncSession, faq_id: UUID) -> RowMapping | None:
    return (
        (
            await session.execute(
                text(f"""SELECT version, builtin_id, draft_revision, published_revision
        FROM {FAQ} WHERE id=:id FOR UPDATE"""),
                {"id": faq_id},
            )
        )
        .mappings()
        .first()
    )


async def add_revision(
    session: AsyncSession,
    faq_id: UUID,
    revision: int,
    author: UUID,
    content: FaqContent,
) -> None:
    await session.execute(
        text(f"""INSERT INTO {REV}(faq_id,revision,author_id,content)
        VALUES (:id,:rev,:author,CAST(:content AS JSONB))"""),
        dict(id=faq_id, rev=revision, author=author, content=content.model_dump_json()),
    )


async def update_pointer(
    session: AsyncSession,
    faq_id: UUID,
    version: int,
    draft_revision: int,
    published_revision: int | None,
    publisher: UUID | None = None,
) -> None:
    if publisher is None:
        publication = ""
    else:
        publication = ", published_by=:publisher, published_at=now()"
    await session.execute(
        text(f"""UPDATE {FAQ} SET version=:version, draft_revision=:draft,
        published_revision=:published, updated_at=now(){publication} WHERE id=:id"""),
        dict(
            id=faq_id,
            version=version,
            draft=draft_revision,
            published=published_revision,
            publisher=publisher,
        ),
    )


async def generation(session: AsyncSession, *, lock: bool = False) -> int:
    suffix = " FOR UPDATE" if lock else ""
    result = await session.scalar(text(f"SELECT generation FROM {STATE} WHERE id=1{suffix}"))
    if not isinstance(result, int):
        raise KnowledgeIssue("invalid_snapshot")
    return result


async def bump_generation(session: AsyncSession) -> None:
    await session.execute(text(f"UPDATE {STATE} SET generation=generation+1 WHERE id=1"))


async def published_snapshot(session: AsyncSession) -> tuple[int, tuple[ManagedFaq, ...]]:
    # Generation and revision pointers come from one PostgreSQL statement snapshot.
    rows = (
        (
            await session.execute(
                text(f"""SELECT s.generation, f.id, f.builtin_id,
        f.published_revision, r.content FROM {STATE} s
        LEFT JOIN {FAQ} f ON f.published_revision IS NOT NULL
        LEFT JOIN {REV} r ON r.faq_id=f.id AND r.revision=f.published_revision
        WHERE s.id=1 ORDER BY f.id LIMIT :limit"""),
                {"limit": MAX_PUBLISHED + 1},
            )
        )
        .mappings()
        .all()
    )
    if not rows or len(rows) > MAX_PUBLISHED:
        raise KnowledgeIssue("invalid_snapshot")
    return rows[0]["generation"], tuple(
        from_row(row["id"], row["published_revision"], row["builtin_id"], row["content"])
        for row in rows
        if row["id"] is not None
    )
