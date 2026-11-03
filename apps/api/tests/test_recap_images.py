"""Recap derivatives preserve safety, geometry, privacy and bounded resource profiles."""

import asyncio
import threading
from io import BytesIO

import pytest
from PIL import Image

from app.services.image_storage import ImageValidationError
from app.services.recap_images import prepare_recap_images


def test_request_cancellation_keeps_decoder_gate_held(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.recap_images as module

    started = threading.Event()
    release = threading.Event()

    def decoder(**kwargs: object) -> dict[str, object]:
        started.set()
        release.wait(timeout=2)
        return {}

    monkeypatch.setattr(module, "prepare_recap_images", decoder)

    async def check() -> None:
        gate = asyncio.Semaphore(1)

        async def request() -> None:
            async with gate:
                await module.prepare_recap_images_async(
                    original_name="x.jpg", declared_content_type="image/jpeg", content=b"unused"
                )

        task = asyncio.create_task(request())
        await asyncio.to_thread(started.wait, 2)
        task.cancel()
        await asyncio.sleep(0.01)
        assert gate.locked()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not gate.locked()

    asyncio.run(check())


@pytest.mark.parametrize("size", [(2400, 1600), (900, 2400), (100, 60)])
def test_derivatives_are_bounded_and_metadata_free(size: tuple[int, int]) -> None:
    source = Image.new("RGB", size, "green")
    exif = Image.Exif()
    exif[270] = "private source metadata"
    output = BytesIO()
    source.save(output, "JPEG", exif=exif)
    images = prepare_recap_images(
        original_name="photo.jpg", declared_content_type="image/jpeg", content=output.getvalue()
    )
    for variant, bound in (("thumbnail", 480), ("display", 1600)):
        prepared = images[variant]
        assert max(prepared.width, prepared.height) <= min(bound, max(size))
        assert abs(prepared.width / prepared.height - size[0] / size[1]) < 0.02
        with Image.open(BytesIO(prepared.content)) as image:
            assert image.format == "WEBP"
            assert not image.getexif()
            assert "exif" not in image.info
            assert "icc_profile" not in image.info


def test_derivatives_use_orientation_and_do_not_upscale() -> None:
    source = Image.new("RGB", (80, 40), "orange")
    exif = Image.Exif()
    exif[274] = 6
    output = BytesIO()
    source.save(output, "JPEG", exif=exif)
    images = prepare_recap_images(
        original_name="photo.jpg", declared_content_type="image/jpeg", content=output.getvalue()
    )
    assert {(image.width, image.height) for image in images.values()} == {(40, 80)}


@pytest.mark.parametrize(
    "name,mime,content",
    [
        ("photo.jpg", "image/jpeg", b"<script>bad</script>"),
        ("../photo.jpg", "image/jpeg", b"bad"),
        ("photo.png", "image/png", b"x" * (5 * 1024 * 1024 + 1)),
    ],
)
def test_validation_is_not_bypassed(name: str, mime: str, content: bytes) -> None:
    with pytest.raises(ImageValidationError):
        prepare_recap_images(original_name=name, declared_content_type=mime, content=content)
