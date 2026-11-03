"""One local question via stdin, JSON response via stdout; no history or logging."""

import sys

from app.services.chatbot.models import MAX_QUESTION
from app.services.chatbot.service import ChatbotService, InvalidQuestion


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    if sys.argv[1:] == ["--knowledge-status"]:
        from app.services.chatbot.owner_source import main as source_status

        return source_status()
    # Bounded read; use stdin rather than putting potentially sensitive questions in argv.
    try:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        text = sys.stdin.read(MAX_QUESTION + 2).removesuffix("\n")
    except UnicodeError:
        print("Enter a UTF-8 question.", file=sys.stderr)
        return 2
    try:
        answer = ChatbotService().ask(text)
    except InvalidQuestion as error:
        print(str(error), file=sys.stderr)
        return 2
    print(answer.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
