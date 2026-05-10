from pipeline.data_loader import load_raw_data
from pipeline.feature_pipeline import run_feature_pipeline
from pipeline.commodity_pipeline import run_commodity_pipeline
from pipeline.technical_pipeline import run_technical_pipeline
from pipeline.merger import merge_engine_outputs


class GlobalPipeline:
    def run(self, data_dir: str):
        raw_data = load_raw_data(data_dir)

        features = run_feature_pipeline(raw_data)

        commodity_results = run_commodity_pipeline(features)

        technical_results = run_technical_pipeline(features)

        final_results = merge_engine_outputs(
            commodity_results,
            technical_results,
        )

        return final_results
