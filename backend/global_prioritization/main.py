"""CLI entrypoint for the global prioritization layer."""

from __future__ import annotations

import argparse
from pathlib import Path

from .service import build_global_alert_queue


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the globally prioritized operational alert queue.")
    parser.add_argument("--mode", default="historical", choices=("historical", "daily"))
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    build_global_alert_queue(args.mode, project_root=args.project_root)


if __name__ == "__main__":
    main()
