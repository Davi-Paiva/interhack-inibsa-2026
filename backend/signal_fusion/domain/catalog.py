from __future__ import annotations

import unicodedata
from dataclasses import dataclass

import pandas as pd

from .scoring import safe_float, safe_str
from .structures import ProductBlock


@dataclass(frozen=True)
class ProductInfo:
    product_id: str
    family: str
    category: str
    block: ProductBlock
    unit_revenue: float


@dataclass(frozen=True)
class ClientInfo:
    client_id: str
    province: str
    total_revenue: float
    avg_ticket: float
    days_since_last_order: int
    is_active: bool


class Catalog:
    def __init__(
        self,
        products: pd.DataFrame | None = None,
        clients: pd.DataFrame | None = None,
    ) -> None:
        self._products = self._build_product_map(products)
        self._clients = self._build_client_map(clients)

    def product(self, product_id: object, fallback_family: object = "") -> ProductInfo:
        key = safe_str(product_id, "unknown_product")
        if key in self._products:
            return self._products[key]
        return ProductInfo(
            product_id=key,
            family=safe_str(fallback_family, key),
            category="unknown",
            block=ProductBlock.UNKNOWN,
            unit_revenue=1.0,
        )

    def client(self, client_id: object) -> ClientInfo:
        key = safe_str(client_id, "unknown_client")
        if key in self._clients:
            return self._clients[key]
        return ClientInfo(
            client_id=key,
            province="",
            total_revenue=0.0,
            avg_ticket=0.0,
            days_since_last_order=9999,
            is_active=False,
        )

    @staticmethod
    def _build_product_map(products: pd.DataFrame | None) -> dict[str, ProductInfo]:
        if products is None or products.empty:
            return {}
        result: dict[str, ProductInfo] = {}
        for _, row in products.iterrows():
            product_id = safe_str(row.get("product_id"))
            if not product_id:
                continue
            total_revenue = safe_float(row.get("product_total_revenue"))
            total_units = max(safe_float(row.get("product_total_units")), 1.0)
            result[product_id] = ProductInfo(
                product_id=product_id,
                family=safe_str(row.get("family"), product_id),
                category=safe_str(row.get("category"), "unknown"),
                block=_block_from_text(row.get("analytic_block")),
                unit_revenue=total_revenue / total_units,
            )
        return result

    @staticmethod
    def _build_client_map(clients: pd.DataFrame | None) -> dict[str, ClientInfo]:
        if clients is None or clients.empty:
            return {}
        result: dict[str, ClientInfo] = {}
        for _, row in clients.iterrows():
            client_id = safe_str(row.get("client_id") or row.get("customer_id"))
            if not client_id:
                continue
            result[client_id] = ClientInfo(
                client_id=client_id,
                province=safe_str(row.get("province")),
                total_revenue=safe_float(row.get("customer_total_revenue")),
                avg_ticket=safe_float(row.get("customer_avg_ticket")),
                days_since_last_order=int(safe_float(row.get("days_since_last_order"), 9999)),
                is_active=str(row.get("is_active_customer")).lower() == "true",
            )
        return result


def _block_from_text(value: object) -> ProductBlock:
    text = _fold_text(safe_str(value).lower())
    if "commod" in text:
        return ProductBlock.COMMODITY
    if "tecn" in text or "techn" in text or "cnic" in text:
        return ProductBlock.TECHNICAL
    return ProductBlock.UNKNOWN


def _fold_text(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
    )
