"""Small fail-closed multipart reader for bounded single-image uploads."""

from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.message import Message
from email.parser import BytesParser
from typing import Final

from fastapi import Request

from app.services.image_storage import MAX_IMAGE_BYTES

MAX_MULTIPART_OVERHEAD: Final = 16 * 1024
MAX_MULTIPART_BYTES: Final = MAX_IMAGE_BYTES + MAX_MULTIPART_OVERHEAD
MAX_PART_HEADERS_BYTES: Final = 8 * 1024
MAX_TEXT_FIELD_BYTES: Final = 1024
_ALLOWED_FIELDS: Final = frozenset({"version", "alt_en", "alt_de"})
_ALLOWED_IMAGE_TYPES: Final = frozenset({"image/jpeg", "image/png", "image/webp"})


class MultipartUploadError(ValueError):
    """Raised before durable work when a multipart image request is malformed or excessive."""


@dataclass(frozen=True, slots=True)
class MultipartImageUpload:
    """One image and its small allowlisted text fields."""

    file_name: str
    content_type: str
    content: bytes
    fields: dict[str, str]


def _boundary(content_type: str) -> bytes:
    message = Message()
    message["Content-Type"] = content_type
    if message.get_content_type() != "multipart/form-data":
        raise MultipartUploadError("Multipart form-data is required.")
    boundary = message.get_param("boundary", header="content-type")
    if not isinstance(boundary, str):
        raise MultipartUploadError("Multipart boundary is missing.")
    try:
        encoded = boundary.encode("ascii")
    except UnicodeEncodeError as error:
        raise MultipartUploadError("Multipart boundary is invalid.") from error
    if not 1 <= len(encoded) <= 70 or any(value <= 32 or value >= 127 for value in encoded):
        raise MultipartUploadError("Multipart boundary is invalid.")
    return encoded


async def _bounded_body(request: Request) -> bytes:
    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        try:
            parsed_length = int(declared_length)
        except ValueError as error:
            raise MultipartUploadError("Multipart content length is invalid.") from error
        if parsed_length < 1 or parsed_length > MAX_MULTIPART_BYTES:
            raise MultipartUploadError("Multipart upload exceeds the size limit.")

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_MULTIPART_BYTES:
            raise MultipartUploadError("Multipart upload exceeds the size limit.")
        chunks.append(chunk)
    if total == 0:
        raise MultipartUploadError("Multipart upload is empty.")
    return b"".join(chunks)


def _parts(body: bytes, boundary: bytes) -> tuple[tuple[Message, bytes], ...]:
    marker = b"--" + boundary
    if not body.startswith(marker + b"\r\n"):
        raise MultipartUploadError("Multipart body is malformed.")

    cursor = len(marker) + 2
    parsed: list[tuple[Message, bytes]] = []
    while True:
        header_end = body.find(b"\r\n\r\n", cursor)
        if header_end < 0 or header_end - cursor > MAX_PART_HEADERS_BYTES:
            raise MultipartUploadError("Multipart part headers are invalid.")
        header_bytes = body[cursor:header_end]
        try:
            headers = BytesParser(policy=policy.default).parsebytes(header_bytes + b"\r\n\r\n")
        except (TypeError, ValueError) as error:
            raise MultipartUploadError("Multipart part headers are invalid.") from error

        content_start = header_end + 4
        next_marker = body.find(b"\r\n" + marker, content_start)
        if next_marker < 0:
            raise MultipartUploadError("Multipart closing boundary is missing.")
        parsed.append((headers, body[content_start:next_marker]))

        cursor = next_marker + 2 + len(marker)
        if body[cursor : cursor + 2] == b"--":
            remainder = body[cursor + 2 :]
            if remainder not in {b"", b"\r\n"}:
                raise MultipartUploadError("Multipart body has trailing data.")
            break
        if body[cursor : cursor + 2] != b"\r\n":
            raise MultipartUploadError("Multipart boundary is malformed.")
        cursor += 2

    if not parsed or len(parsed) > 4:
        raise MultipartUploadError("Multipart part count is invalid.")
    return tuple(parsed)


def _parse_upload(body: bytes, boundary: bytes) -> MultipartImageUpload:
    fields: dict[str, str] = {}
    file_name: str | None = None
    file_type: str | None = None
    file_content: bytes | None = None

    for headers, content in _parts(body, boundary):
        if len(headers.get_all("Content-Disposition", [])) != 1:
            raise MultipartUploadError("Multipart disposition is invalid.")
        if headers.get_content_disposition() != "form-data":
            raise MultipartUploadError("Multipart disposition is invalid.")
        name = headers.get_param("name", header="content-disposition")
        filename = headers.get_filename()
        if not isinstance(name, str):
            raise MultipartUploadError("Multipart field name is invalid.")

        if name == "file":
            if file_content is not None or not isinstance(filename, str) or not filename:
                raise MultipartUploadError("Exactly one image file is required.")
            content_type = headers.get_content_type().casefold()
            if content_type not in _ALLOWED_IMAGE_TYPES:
                raise MultipartUploadError("Image content type is unsupported.")
            if not 1 <= len(content) <= MAX_IMAGE_BYTES:
                raise MultipartUploadError("Image file exceeds the size limit.")
            file_name = filename
            file_type = content_type
            file_content = content
            continue

        if name not in _ALLOWED_FIELDS or filename is not None or name in fields:
            raise MultipartUploadError("Multipart field is not allowed.")
        if len(content) > MAX_TEXT_FIELD_BYTES:
            raise MultipartUploadError("Multipart text field is too large.")
        try:
            fields[name] = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise MultipartUploadError("Multipart text field is invalid.") from error

    if file_name is None or file_type is None or file_content is None:
        raise MultipartUploadError("Exactly one image file is required.")
    if set(fields) != _ALLOWED_FIELDS:
        raise MultipartUploadError("Required multipart fields are missing.")
    return MultipartImageUpload(
        file_name=file_name,
        content_type=file_type,
        content=file_content,
        fields=fields,
    )


async def read_multipart_image_upload(request: Request) -> MultipartImageUpload:
    """Stream one bounded request, then parse only the approved image/field shape."""
    boundary = _boundary(request.headers.get("content-type", ""))
    return _parse_upload(await _bounded_body(request), boundary)
