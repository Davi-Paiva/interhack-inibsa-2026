from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD


DEFAULT_EMBEDDING_DIMENSIONS = 4
CLIENT_EMBEDDING_COLUMNS = [f"client_embedding_{index}" for index in range(DEFAULT_EMBEDDING_DIMENSIONS)]
PRODUCT_EMBEDDING_COLUMNS = [f"product_embedding_{index}" for index in range(DEFAULT_EMBEDDING_DIMENSIONS)]
CLIENT_PRODUCT_EMBEDDING_COLUMNS = [
    "client_product_embedding_score",
    "client_product_embedding_cosine",
    "client_product_preference_gap",
]
EMBEDDING_FEATURE_PREFIXES = (
    "client_embedding_",
    "product_embedding_",
    "client_product_embedding_",
)
EMBEDDING_DERIVED_COLUMNS = (
    "client_product_preference_gap",
)


@dataclass(frozen=True)
class EmbeddingFeatureBundle:
    client_features: pd.DataFrame
    product_features: pd.DataFrame
    client_product_features: pd.DataFrame
    metrics: dict[str, Any]


def _zero_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _pad_embedding_frame(frame: pd.DataFrame, columns: list[str], key_columns: list[str]) -> pd.DataFrame:
    padded = frame.copy()
    for column in columns:
        if column not in padded.columns:
            padded[column] = 0.0
    ordered_columns = [*key_columns, *columns]
    return padded.loc[:, ordered_columns].copy()


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_norm = np.linalg.norm(left, axis=1)
    right_norm = np.linalg.norm(right, axis=1)
    denominator = left_norm * right_norm
    similarity = np.divide(
        np.sum(left * right, axis=1),
        denominator,
        out=np.zeros_like(left_norm, dtype=float),
        where=denominator > 0,
    )
    return np.clip(similarity, -1.0, 1.0)


def build_embedding_feature_bundle(
    sales: pd.DataFrame,
    *,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
) -> EmbeddingFeatureBundle:
    if sales.empty:
        return EmbeddingFeatureBundle(
            client_features=_zero_frame(["client_id", *CLIENT_EMBEDDING_COLUMNS]),
            product_features=_zero_frame(["product_id", *PRODUCT_EMBEDDING_COLUMNS]),
            client_product_features=_zero_frame(["client_id", "product_id", *CLIENT_PRODUCT_EMBEDDING_COLUMNS]),
            metrics={
                "dimensions_requested": int(dimensions),
                "dimensions_used": 0,
                "explained_variance_ratio": 0.0,
                "matrix_shape": {"clients": 0, "products": 0},
                "status": "empty_source",
            },
        )

    grouped_sales = (
        sales.groupby(["client_id", "product_id"], dropna=False)["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "pair_total_revenue"})
    )
    grouped_sales["pair_total_revenue"] = pd.to_numeric(
        grouped_sales["pair_total_revenue"],
        errors="coerce",
    ).fillna(0.0).clip(lower=0.0)
    matrix = (
        grouped_sales.pivot(index="client_id", columns="product_id", values="pair_total_revenue")
        .fillna(0.0)
        .sort_index(axis=0)
        .sort_index(axis=1)
    )
    if matrix.empty:
        return EmbeddingFeatureBundle(
            client_features=_zero_frame(["client_id", *CLIENT_EMBEDDING_COLUMNS]),
            product_features=_zero_frame(["product_id", *PRODUCT_EMBEDDING_COLUMNS]),
            client_product_features=_zero_frame(["client_id", "product_id", *CLIENT_PRODUCT_EMBEDDING_COLUMNS]),
            metrics={
                "dimensions_requested": int(dimensions),
                "dimensions_used": 0,
                "explained_variance_ratio": 0.0,
                "matrix_shape": {"clients": 0, "products": 0},
                "status": "empty_matrix",
            },
        )

    transformed_matrix = np.log1p(matrix.astype(float))
    max_components = min(
        int(dimensions),
        max(transformed_matrix.shape[0] - 1, 1),
        max(transformed_matrix.shape[1] - 1, 1),
    )
    max_components = max(1, max_components)

    svd = TruncatedSVD(n_components=max_components, random_state=42)
    client_latent = svd.fit_transform(transformed_matrix)
    product_latent = svd.components_.T

    client_embeddings = pd.DataFrame(client_latent, index=transformed_matrix.index)
    client_embeddings.columns = [f"client_embedding_{index}" for index in range(client_embeddings.shape[1])]
    client_embeddings = _pad_embedding_frame(
        client_embeddings.reset_index(),
        CLIENT_EMBEDDING_COLUMNS,
        ["client_id"],
    )

    product_embeddings = pd.DataFrame(product_latent, index=transformed_matrix.columns)
    product_embeddings.columns = [f"product_embedding_{index}" for index in range(product_embeddings.shape[1])]
    product_embeddings = _pad_embedding_frame(
        product_embeddings.reset_index(),
        PRODUCT_EMBEDDING_COLUMNS,
        ["product_id"],
    )

    client_lookup = client_embeddings.set_index("client_id")[CLIENT_EMBEDDING_COLUMNS]
    product_lookup = product_embeddings.set_index("product_id")[PRODUCT_EMBEDDING_COLUMNS]
    pair_embeddings = grouped_sales.merge(client_lookup, on="client_id", how="left")
    pair_embeddings = pair_embeddings.merge(product_lookup, on="product_id", how="left")

    client_values = pair_embeddings.loc[:, CLIENT_EMBEDDING_COLUMNS].to_numpy(dtype=float)
    product_values = pair_embeddings.loc[:, PRODUCT_EMBEDDING_COLUMNS].to_numpy(dtype=float)
    pair_embeddings["client_product_embedding_score"] = np.sum(client_values * product_values, axis=1)
    pair_embeddings["client_product_embedding_cosine"] = _cosine_similarity(client_values, product_values)
    pair_embeddings["client_product_preference_gap"] = (
        np.log1p(pair_embeddings["pair_total_revenue"].astype(float))
        - pair_embeddings["client_product_embedding_score"].astype(float)
    )
    pair_embeddings = pair_embeddings.loc[
        :,
        ["client_id", "product_id", *CLIENT_PRODUCT_EMBEDDING_COLUMNS],
    ].copy()

    metrics = {
        "dimensions_requested": int(dimensions),
        "dimensions_used": int(max_components),
        "explained_variance_ratio": float(np.sum(svd.explained_variance_ratio_)),
        "matrix_shape": {
            "clients": int(transformed_matrix.shape[0]),
            "products": int(transformed_matrix.shape[1]),
        },
        "non_zero_pair_count": int((matrix > 0).sum().sum()),
        "status": "ok",
    }
    return EmbeddingFeatureBundle(
        client_features=client_embeddings,
        product_features=product_embeddings,
        client_product_features=pair_embeddings,
        metrics=metrics,
    )
