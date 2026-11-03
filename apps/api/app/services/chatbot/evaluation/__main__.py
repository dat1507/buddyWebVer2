"""Synthetic fixture CLI. No live inference option or credential discovery."""

import argparse
import asyncio
import json
from pathlib import Path

from app.services.chatbot.evaluation.runner import run_mock, run_retrieval, write_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="working-tree")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mode", choices=("retrieval", "mock"), default="retrieval")
    args = parser.parse_args()
    result = asyncio.run(run_mock(args.label)) if args.mode == "mock" else run_retrieval(args.label)
    if args.output:
        write_report(result, args.output)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
