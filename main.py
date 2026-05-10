import argparse
import sys
from pathlib import Path

from pipeline.orchestrator import GlobalPipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the global pipeline.")
    parser.add_argument("data_dir", help="Path to the raw data folder")
    parser.add_argument(
        "--mode",
        default="historical",
        choices=("historical", "daily"),
        help="Pipeline mode to execute.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists() or not data_dir.is_dir():
        print(f"Error: data directory does not exist: {data_dir}", file=sys.stderr)
        return 1

    pipeline = GlobalPipeline()

    try:
        final_results = pipeline.run(str(data_dir), mode=args.mode)
    except Exception as exc:
        print(f"Pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    print("Pipeline completed successfully.")

    if hasattr(final_results, "shape"):
        print(f"Result shape: {final_results.shape}")
    elif hasattr(final_results, "__len__"):
        try:
            print(f"Result count: {len(final_results)}")
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
