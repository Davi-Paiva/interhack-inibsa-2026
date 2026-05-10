"""CLI entrypoint for the global prioritization layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .service import GlobalPrioritizationService, build_global_alert_queue


def _print_paths(label: str, paths: dict[str, Path] | dict[str, list[str]]) -> None:
    print(label)
    for key, value in paths.items():
        if isinstance(value, list):
            serialized = json.dumps(value, ensure_ascii=True)
        else:
            serialized = str(value)
        print(f"- {key}: {serialized}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the globally prioritized operational alert queue.")
    parser.add_argument("--mode", default="historical", choices=("historical", "daily"))
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--daily-state-action",
        default="build",
        choices=("build", "mark-seen", "simulate-first-run", "reset-state"),
        help="Daily queue demo control. 'build' keeps the normal behavior.",
    )
    args = parser.parse_args()
    service = GlobalPrioritizationService(args.project_root)

    if args.daily_state_action != "build" and args.mode != "daily":
        parser.error("--daily-state-action only works with --mode daily")

    if args.daily_state_action == "mark-seen":
        outputs = service.mark_current_daily_snapshot_as_seen(args.mode)
        _print_paths("Marked current daily snapshot as seen.", outputs)
        return
    if args.daily_state_action == "simulate-first-run":
        outputs = service.simulate_daily_first_run(args.mode)
        _print_paths("Simulated first daily run. Current full snapshot is public again as new alerts.", outputs)
        return
    if args.daily_state_action == "reset-state":
        outputs = service.reset_daily_state(args.mode)
        _print_paths("Reset daily state files.", outputs)
        return

    outputs = build_global_alert_queue(args.mode, project_root=args.project_root)
    _print_paths("Built global alert queue.", outputs)


if __name__ == "__main__":
    main()
