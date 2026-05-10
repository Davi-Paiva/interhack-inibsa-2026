"""CLI entrypoint for delegate feedback tooling."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .service import (
    ACTION_TAKEN_OPTIONS,
    ALERT_VALIDITY_OPTIONS,
    BUSINESS_OUTCOME_OPTIONS,
    RESOLUTION_STATUS_OPTIONS,
    DelegateFeedbackService,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage delegate feedback artifacts.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    subparsers = parser.add_subparsers(dest="command", required=True)

    policy_parser = subparsers.add_parser("build-policy", help="Rebuild the feedback policy artifact.")
    policy_parser.add_argument("--mode", default="daily", choices=("historical", "daily"))

    submit_parser = subparsers.add_parser("submit", help="Append a single delegate feedback record.")
    submit_parser.add_argument("--mode", default="daily", choices=("historical", "daily"))
    submit_parser.add_argument("--alert-id", required=True)
    submit_parser.add_argument("--delegate-id", required=True)
    submit_parser.add_argument("--resolution-status", required=True, choices=RESOLUTION_STATUS_OPTIONS)
    submit_parser.add_argument("--alert-validity", required=True, choices=ALERT_VALIDITY_OPTIONS)
    submit_parser.add_argument("--action-taken", required=True, choices=ACTION_TAKEN_OPTIONS)
    submit_parser.add_argument("--business-outcome", required=True, choices=BUSINESS_OUTCOME_OPTIONS)
    submit_parser.add_argument("--root-cause", required=True)
    submit_parser.add_argument("--free-note", default="")
    submit_parser.add_argument("--resolved-at", default="", help="ISO datetime. Defaults to now.")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    service = DelegateFeedbackService(project_root=args.project_root)

    if args.command == "build-policy":
        path = service.build_policy(args.mode)
        print(path)
        return

    if args.command == "submit":
        alert_row = service.find_alert_row(args.mode, args.alert_id)
        if alert_row is None:
            raise SystemExit(f"Alert not found in queue: {args.alert_id}")
        resolved_at = datetime.fromisoformat(args.resolved_at) if args.resolved_at else None
        paths = service.record_feedback(
            args.mode,
            alert_row,
            delegate_id=args.delegate_id,
            resolution_status=args.resolution_status,
            alert_validity=args.alert_validity,
            action_taken=args.action_taken,
            business_outcome=args.business_outcome,
            root_cause=args.root_cause,
            free_note=args.free_note,
            resolved_at=resolved_at,
            rebuild_policy=True,
        )
        for path in paths.values():
            print(path)


if __name__ == "__main__":
    main()
