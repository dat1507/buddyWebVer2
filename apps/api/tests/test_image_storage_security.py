"""Bounded regressions for Pillow EXIF parsing and image normalization."""

from __future__ import annotations

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import PIL
import pytest
from PIL import Image

from app.services.image_storage import prepare_image


def test_repeated_png_exif_markers_have_bounded_processing_cost() -> None:
    # Run the real pipeline in a disposable child: a regressed dependency cannot hang pytest.
    # 1.8 MiB of metadata is below the upload cap even with a one-pixel image.
    script = r"""
import io, json, struct, sys, time, zlib
sys.path[:0] = sys.argv[1:3]
from PIL import Image
from app.services.image_storage import ImageValidationError, prepare_image
buffer = io.BytesIO()
Image.new("RGB", (1, 1), (12, 34, 56)).save(buffer, "PNG")
base = buffer.getvalue()
payload = b"Exif\x00\x00" * 300_000
chunk = struct.pack(">I", len(payload)) + b"eXIf" + payload
chunk += struct.pack(">I", zlib.crc32(b"eXIf" + payload))
content = base[:33] + chunk + base[33:]
started = time.perf_counter()
try:
    prepared = prepare_image(original_name="bounded.png", declared_content_type="image/png", content=content)
except ImageValidationError:
    # Pillow 13 rejects the malformed metadata after inspecting at most two markers.
    outcome = "rejected"
else:
    with Image.open(io.BytesIO(prepared.content)) as result:
        result.load()
        assert result.size == (1, 1)
        assert result.getpixel((0, 0)) == (12, 34, 56)
        assert not result.getexif()
        assert "exif" not in result.info
    outcome = "normalized"
elapsed = time.perf_counter() - started
print(json.dumps({"seconds": elapsed, "input_bytes": len(content), "outcome": outcome}))
"""
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(Path(PIL.__file__).resolve().parent.parent),
                str(Path(__file__).resolve().parents[1]),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("PNG EXIF processing exceeded the bounded child-process timeout")
    measured = json.loads(completed.stdout)
    assert 1_800_000 < measured["input_bytes"] < 2_000_000
    assert measured["outcome"] in {"rejected", "normalized"}
    # Generous compared with the patched millisecond path; excludes interpreter/import time.
    assert measured["seconds"] < 1.0


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_exif_rotation_preserves_dimensions_and_removes_metadata(image_format: str) -> None:
    source = Image.new("RGB", (12, 8), (20, 40, 60))
    exif = Image.Exif()
    exif[0x0112] = 6  # Rotate clockwise to portrait.
    exif[0x010E] = "private test metadata"
    buffer = BytesIO()
    source.save(buffer, image_format, exif=exif)
    extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image_format]
    mime_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[image_format]
    prepared = prepare_image(
        original_name=f"orientation.{extension}",
        declared_content_type=mime_type,
        content=buffer.getvalue(),
    )
    assert (prepared.width, prepared.height) == (8, 12)
    with Image.open(BytesIO(prepared.content)) as normalized:
        normalized.load()
        assert normalized.size == (8, 12)
        assert normalized.mode == "RGB"
        assert not normalized.getexif()
        assert "exif" not in normalized.info
