"""Bounded upload-time derivatives using the existing hardened image validation."""

from __future__ import annotations

import asyncio
from io import BytesIO

from PIL import Image

from app.services.image_storage import PreparedImage, prepare_image

# One active decoder per process. Upload reader and processing share this gate at the API boundary.
RECAP_UPLOAD_GATE = asyncio.Semaphore(1)


def prepare_recap_images(
    *, original_name: str, declared_content_type: str, content: bytes
) -> dict[str, PreparedImage]:
    validated = prepare_image(
        original_name=original_name,
        declared_content_type=declared_content_type,
        content=content,
        maximum_output_dimension=1600,
    )
    variants: dict[str, PreparedImage] = {}
    with Image.open(BytesIO(validated.content)) as source:
        for variant, bound, quality in (("display", 1600, 82), ("thumbnail", 480, 76)):
            image = source.copy()
            image.thumbnail((bound, bound), Image.Resampling.LANCZOS)
            mode = "RGBA" if image.mode == "RGBA" else "RGB"
            clean = Image.new(mode, image.size)
            clean.paste(image.convert(mode))
            output = BytesIO()
            clean.save(output, "WEBP", quality=quality, method=4)
            data = output.getvalue()
            variants[variant] = PreparedImage(data, "image/webp", "webp", len(data), *clean.size)
            image.close()
            clean.close()
    return variants


async def prepare_recap_images_async(
    *, original_name: str, declared_content_type: str, content: bytes
) -> dict[str, PreparedImage]:
    processing = asyncio.create_task(
        asyncio.to_thread(
            prepare_recap_images,
            original_name=original_name,
            declared_content_type=declared_content_type,
            content=content,
        )
    )
    try:
        return await asyncio.shield(processing)
    except asyncio.CancelledError:
        # Keep the caller's decoder gate held until a non-cancellable Pillow thread finishes.
        await processing
        raise
