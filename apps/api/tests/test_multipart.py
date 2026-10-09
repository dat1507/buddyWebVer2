"""Fail-closed parser tests for the bounded Event cover multipart contract."""

from __future__ import annotations

import pytest

from app.api.multipart import (
    MultipartUploadError,
    _boundary,
    _parse_upload,
)
from app.services.image_storage import MAX_IMAGE_BYTES

BOUNDARY = b"event-cover-boundary"


def _part(name: str, content: bytes, *, filename: str | None = None) -> bytes:
    disposition = f'Content-Disposition: form-data; name="{name}"'
    content_type = ""
    if filename is not None:
        disposition += f'; filename="{filename}"'
        content_type = "\r\nContent-Type: image/png"
    return (
        b"--"
        + BOUNDARY
        + b"\r\n"
        + disposition.encode()
        + content_type.encode()
        + b"\r\n\r\n"
        + content
        + b"\r\n"
    )


def _body(*parts: bytes) -> bytes:
    return b"".join(parts) + b"--" + BOUNDARY + b"--\r\n"


def _valid_body(*, file_content: bytes = b"png-bytes") -> bytes:
    return _body(
        _part("version", b"3"),
        _part("alt_en", b"Event poster"),
        _part("alt_de", b"Veranstaltungsplakat"),
        _part("file", file_content, filename="cover.png"),
    )


def test_parser_accepts_exact_allowlisted_shape() -> None:
    upload = _parse_upload(_valid_body(), BOUNDARY)

    assert upload.file_name == "cover.png"
    assert upload.content_type == "image/png"
    assert upload.content == b"png-bytes"
    assert upload.fields == {
        "version": "3",
        "alt_en": "Event poster",
        "alt_de": "Veranstaltungsplakat",
    }


@pytest.mark.parametrize(
    "body",
    [
        _body(
            _part("version", b"3"),
            _part("alt_en", b"Event poster"),
            _part("file", b"image", filename="cover.png"),
        ),
        _body(
            _part("version", b"3"),
            _part("alt_en", b"Event poster"),
            _part("alt_de", b"Poster"),
            _part("bucket", b"public"),
            _part("file", b"image", filename="cover.png"),
        ),
        _body(
            _part("version", b"3"),
            _part("version", b"4"),
            _part("alt_en", b"Event poster"),
            _part("alt_de", b"Poster"),
            _part("file", b"image", filename="cover.png"),
        ),
    ],
)
def test_parser_rejects_missing_unknown_and_duplicate_fields(body: bytes) -> None:
    with pytest.raises(MultipartUploadError):
        _parse_upload(body, BOUNDARY)


def test_parser_rejects_duplicate_or_oversized_files() -> None:
    duplicate = _body(
        _part("version", b"3"),
        _part("alt_en", b"Event poster"),
        _part("alt_de", b"Poster"),
        _part("file", b"first", filename="first.png"),
        _part("file", b"second", filename="second.png"),
    )
    with pytest.raises(MultipartUploadError):
        _parse_upload(duplicate, BOUNDARY)
    with pytest.raises(MultipartUploadError, match="size limit"):
        _parse_upload(_valid_body(file_content=b"x" * (MAX_IMAGE_BYTES + 1)), BOUNDARY)


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "multipart/form-data",
        "multipart/form-data; boundary=bad boundary",
    ],
)
def test_boundary_rejects_wrong_or_unsafe_content_type(content_type: str) -> None:
    with pytest.raises(MultipartUploadError):
        _boundary(content_type)


def test_parser_rejects_malformed_closing_boundary() -> None:
    with pytest.raises(MultipartUploadError, match="closing boundary"):
        _parse_upload(_valid_body()[: -len(BOUNDARY) - 4], BOUNDARY)
