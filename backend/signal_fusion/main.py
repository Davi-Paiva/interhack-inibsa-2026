from __future__ import annotations

import argparse
from pathlib import Path

from .adapters import ArtifactPaths, SignalFusionLoader
from .services.exporter import AlertExporter
from .services.fusion_engine import SignalFusionEngine


def run_signal_fusion(
    *,
    project_root: Path,
    mode: str = "historical",
    output_dir: Path | None = None,
    selection: str = "ranked",
    seed: int | None = None,
    top_n: int | None = None,
) -> dict[str, Path | int]:
    paths = ArtifactPaths(project_root=project_root, mode=mode)
    tables = SignalFusionLoader(paths).load()
    alerts = SignalFusionEngine().generate_alerts(
        tables,
        selection=selection,
        seed=seed,
        top_n=top_n,
    )

    output_base = output_dir or project_root / "backend" / "signal_fusion" / "output" / mode
    exporter = AlertExporter()
    json_path = exporter.write_json(alerts, output_base / "alerts.json")
    csv_path = exporter.write_csv(alerts, output_base / "alerts.csv")
    return {
        "alert_count": len(alerts),
        "json_output": json_path,
        "csv_output": csv_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Signal Fusion alert generation")
    parser.add_argument("--mode", default="historical", choices=("historical", "daily"))
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--selection",
        default="ranked",
        choices=("ranked", "random", "balanced"),
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--top-n", type=int, default=None)
    args = parser.parse_args()

    default_root = Path(__file__).resolve().parents[2]
    result = run_signal_fusion(
        project_root=Path(args.project_root).resolve() if args.project_root else default_root,
        mode=args.mode,
        output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
        selection=args.selection,
        seed=args.seed,
        top_n=args.top_n,
    )
    print(f"Generated {result['alert_count']} alerts")
    print(f"JSON: {result['json_output']}")
    print(f"CSV: {result['csv_output']}")


if __name__ == "__main__":
    main()
