from pipeline.data_loader import load_raw_data
from pipeline.feature_pipeline import run_feature_pipeline
from pipeline.commodity_pipeline import run_commodity_pipeline
from pipeline.technical_pipeline import run_technical_pipeline
from pipeline.merger import merge_engine_outputs


class GlobalPipeline:
    def run(self, data_dir: str, mode: str = "historical"):
        raw_data = load_raw_data(data_dir)

        features = run_feature_pipeline(raw_data, data_dir=data_dir, mode=mode)

        commodity_results = run_commodity_pipeline(features, mode=mode)

        technical_results = run_technical_pipeline(features, mode=mode)

        final_results = merge_engine_outputs(
            commodity_results,
            technical_results,
            mode=mode,
        )

        return final_results
