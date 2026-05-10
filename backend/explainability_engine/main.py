"""CLI entrypoint for the explainability engine."""

from __future__ import annotations

import argparse
from pathlib import Path

from .service import (
    generate_commodity_explanations,
    generate_technical_explanations,
    sync_all_explanations,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate explainability artifacts for current engine outputs.")
    parser.add_argument("--mode", default="historical", choices=("historical", "daily"))
    parser.add_argument("--source", default="all", choices=("commodity", "technical", "all"))
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()

    if args.source in {"commodity", "all"}:
        generate_commodity_explanations(args.mode, project_root=args.project_root)
    if args.source in {"technical", "all"}:
        generate_technical_explanations(args.mode, project_root=args.project_root)
    sync_all_explanations(args.mode, project_root=args.project_root)


if __name__ == "__main__":
    main()
