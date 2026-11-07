"""Public retrieval-only transport with scoped ASGI protection before JSON parsing."""

import asyncio
import json
import time
from typing import Annotated

from fastapi import APIRouter, Body, Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.chatbot import (
    ChatbotConfigurationError,
    ChatbotFailure,
    ChatbotRuntime,
    Lease,
    get_chatbot_runtime,
    get_chatbot_settings,
)
from app.core.rate_limits import client_identifier
from app.schemas.chatbot import ChatbotQuery, ChatbotResponse, ErrorCode

PATH = "/api/chatbot/query"
NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}
router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])


def failure(code: ErrorCode, status: int, retry: int | None = None) -> JSONResponse:
    headers = dict(NO_STORE)
    if retry is not None:
        headers["Retry-After"] = str(retry)
    if status == 405:
        headers["Allow"] = "POST"
    return JSONResponse(
        status_code=status,
        headers=headers,
        content=ChatbotResponse(
            answer="The chatbot request could not be completed. Please try again. / "
            "Die Chatbot-Anfrage konnte nicht abgeschlossen werden. Bitte versuche es erneut.",
            language="und",
            supported=False,
            status=code,
        ).model_dump(mode="json"),
    )


def no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


class ChatbotProtectionMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        root = scope.get("root_path", "")
        if root and path.startswith(f"{root}/"):
            path = path[len(root) :]
        if scope["type"] != "http" or path.rstrip("/") != PATH:
            await self.app(scope, receive, send)
            return
        lease: Lease | None = None
        response_started = False
        try:
            settings = get_chatbot_settings()
            if not settings.enabled:
                raise ChatbotFailure(503, "disabled")
            if scope["method"] != "POST":
                raise ChatbotFailure(405, "method_not_allowed")
            runtime = get_chatbot_runtime(settings)
            lease = runtime.admit(client_identifier(Request(scope)))
            if scope.get("query_string"):
                raise ChatbotFailure(422, "invalid_request")
            deadline = time.monotonic() + settings.deadline_ms / 1000
            headers = Request(scope).headers
            lengths = headers.getlist("content-length")
            if len(lengths) > 1:
                raise ChatbotFailure(400, "invalid_request")
            if lengths:
                value = lengths[0]
                if len(value) > 20 or not value.isascii() or not value.isdecimal():
                    raise ChatbotFailure(400, "invalid_request")
                if int(value) > settings.max_body_bytes:
                    raise ChatbotFailure(413, "payload_too_large")
            if headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
                raise ChatbotFailure(415, "unsupported_media_type")
            if headers.get("content-encoding", "identity").lower() != "identity":
                raise ChatbotFailure(415, "unsupported_media_type")
            body = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ChatbotFailure(504, "timeout", 1)
                message = await asyncio.wait_for(receive(), timeout=remaining)
                if message["type"] != "http.request":
                    raise ChatbotFailure(400, "invalid_request")
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > settings.max_body_bytes:
                    raise ChatbotFailure(413, "payload_too_large")
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            try:
                payload = json.loads(body, object_pairs_hook=no_duplicate_keys)
            except (ValueError, UnicodeError, RecursionError):
                raise ChatbotFailure(400, "invalid_request") from None
            try:
                validated = ChatbotQuery.model_validate(payload)
                if len(validated.question) > settings.max_question_chars:
                    raise ValueError
            except ValueError:
                raise ChatbotFailure(422, "invalid_request") from None
            state = scope.setdefault("state", {})
            state.update(chatbot_runtime=runtime, chatbot_lease=lease, chatbot_deadline=deadline)
            replayed = False

            async def replay() -> Message:
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            async def secure_send(message: Message) -> None:
                nonlocal response_started
                if message["type"] == "http.response.start":
                    response_started = True
                    message["headers"] = [
                        (key, value)
                        for key, value in message.get("headers", [])
                        if key.lower() not in {b"cache-control", b"pragma"}
                    ] + [(b"cache-control", b"no-store"), (b"pragma", b"no-cache")]
                await send(message)

            await self.app(scope, replay, secure_send)
        except ChatbotConfigurationError:
            await failure("configuration_error", 503)(scope, receive, send)
        except ChatbotFailure as error:
            await failure(error.code, error.status, error.retry_after)(scope, receive, send)
        except TimeoutError:
            await failure("timeout", 504, 1)(scope, receive, send)
        except Exception:
            if response_started:
                raise
            await failure("internal_error", 500)(scope, receive, send)
        finally:
            if lease is not None and not lease.transferred:
                lease.release()


@router.post(
    "/query",
    response_model=ChatbotResponse,
    responses={
        code: {"model": ChatbotResponse} for code in (400, 405, 413, 415, 422, 429, 500, 503, 504)
    },
)
async def query_chatbot(
    request: Request,
    payload: Annotated[ChatbotQuery, Body()],
) -> ChatbotResponse | JSONResponse:
    runtime = getattr(request.state, "chatbot_runtime", None)
    lease = getattr(request.state, "chatbot_lease", None)
    deadline = getattr(request.state, "chatbot_deadline", None)
    if (
        not isinstance(runtime, ChatbotRuntime)
        or not isinstance(lease, Lease)
        or not isinstance(deadline, float)
    ):
        return failure("unavailable", 503)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return failure("timeout", 504, 1)
    try:
        entries = await runtime.managed.get(min(0.35, remaining / 4))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return failure("timeout", 504, 1)
        future = runtime.submit(payload.question, lease, entries)
        result = await asyncio.wait_for(
            asyncio.shield(asyncio.wrap_future(future)), timeout=remaining
        )
    except TimeoutError:
        return failure("timeout", 504, 1)
    except Exception:
        return failure("internal_error", 500)
    if result is None:
        return failure("internal_error", 500)
    if result.status == "unavailable":
        return JSONResponse(
            status_code=503, content=result.model_dump(mode="json"), headers=NO_STORE
        )
    return result
