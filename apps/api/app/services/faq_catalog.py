"""Read-only Admin composition. Never participates in public retrieval or publication."""

from datetime import date

from app.schemas.managed_faq import Faq, FaqContent, LocaleDraft, Publication
from app.services.chatbot.models import Contract, Entry, Source


class CatalogBuiltin(Contract):
    id: str
    category: str
    status: str
    en: str
    de: str
    content: FaqContent
    verified_on: date | None


class CatalogItem(Contract):
    id: str
    content: FaqContent
    sources: tuple[Source, ...]
    status: Publication
    managed: Faq | None
    builtin: CatalogBuiltin | None


class CatalogPage(Contract):
    items: tuple[CatalogItem, ...]
    has_more: bool


def builtin_content(entry: Entry) -> FaqContent:
    # Do not turn repository provenance into Admin verification or invent a public URL.
    return FaqContent(
        category=entry.category,
        en=LocaleDraft(questions=entry.en.questions, answer=entry.en.answer),
        de=LocaleDraft(questions=entry.de.questions, answer=entry.de.answer),
    )


def catalog_page(
    rows: list[tuple[Faq, FaqContent | None]],
    builtins: tuple[Entry, ...],
    search: str,
    category: str | None,
    status: str | None,
    page: int,
) -> CatalogPage:
    linked = {faq.builtin_id: (faq, public) for faq, public in rows if faq.builtin_id}
    items = []
    for entry in builtins:
        original = builtin_content(entry)
        faq, public = linked.get(entry.id, (None, None))
        effective = public or original
        items.append(
            CatalogItem(
                id=entry.id,
                content=effective,
                sources=(Source(title=public.source_title, reference=public.source_url),)
                if public
                else entry.sources,
                status=faq.status
                if faq
                else ("published" if entry.authoritative else "unpublished"),
                managed=faq,
                builtin=CatalogBuiltin(
                    id=entry.id,
                    category=entry.category,
                    status=entry.status,
                    en=entry.en.questions[0],
                    de=entry.de.questions[0],
                    content=original,
                    verified_on=entry.verified_on,
                ),
            )
        )
    known = {entry.id for entry in builtins}
    for faq, public in rows:
        if faq.builtin_id in known:
            continue
        effective = public or faq.content
        items.append(
            CatalogItem(
                id=str(faq.id),
                content=effective,
                status=faq.status,
                managed=faq,
                builtin=None,
                sources=(
                    Source(
                        title=effective.source_title or effective.source_url,
                        reference=effective.source_url,
                    ),
                )
                if effective.source_url
                else (),
            )
        )
    needle = search.strip().casefold()
    filtered = []
    for item in items:
        # Search effective content AND the saved draft; keep a single identity through pagination.
        contents = [item.content]
        if item.managed:
            contents.append(item.managed.content)
        if item.builtin:
            contents.append(item.builtin.content)
        text = " ".join(
            value
            for content in contents
            for value in (
                *content.en.questions,
                content.en.answer,
                *content.de.questions,
                content.de.answer,
            )
        )
        if (
            (not category or item.content.category == category)
            and (not status or item.status == status)
            and (not needle or needle in text.casefold())
        ):
            filtered.append(item)
    offset = (page - 1) * 20
    return CatalogPage(
        items=tuple(filtered[offset : offset + 20]), has_more=len(filtered) > offset + 20
    )
