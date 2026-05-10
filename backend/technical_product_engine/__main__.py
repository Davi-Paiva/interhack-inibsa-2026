"""
Entry point for running the technical product engine as a module.

This allows the engine to be run with:
    python -m technical_product_engine
"""
from .main import _build_parser, main

if __name__ == "__main__":
    args = _build_parser().parse_args()
    main(
        mode=args.mode,
        processed_data_dir=args.processed_data_dir,
        output_dir=args.output_dir,
    )
