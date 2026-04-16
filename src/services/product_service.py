from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from src.core.models import Product


PRODUCT_SELECT = """
BCODE,
DESCR,
MODEL,
BRAND,
PRICE1,
HQ_LOCATION1,
SYP_LOCATION1
""".replace("\n", "").replace(" ", "")


class ProductService:
    def __init__(self) -> None:
        load_dotenv()

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing in environment variables.")

        self.client: Client = create_client(url, key)

    def get_product_by_barcode(self, barcode: str) -> Optional[Product]:
        response = (
            self.client.table("v_pos_products_hq")
            .select(PRODUCT_SELECT)
            .eq("BCODE", barcode)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        if not rows:
            return None

        return self._row_to_product(rows[0])

    def get_related_products(self, bcode: str) -> list[Product]:
        group_resp = (
            self.client.table("product_related_group_map")
            .select("related_group_id")
            .eq("bcode", bcode)
            .execute()
        )
        group_rows = group_resp.data or []

        if not group_rows:
            return []

        group_ids: list[str] = []
        seen_group_ids = set()

        for row in group_rows:
            group_id = row.get("related_group_id")
            if group_id and group_id not in seen_group_ids:
                seen_group_ids.add(group_id)
                group_ids.append(group_id)

        if not group_ids:
            return []

        related_resp = (
            self.client.table("product_related_group_map")
            .select("bcode, related_group_id")
            .in_("related_group_id", group_ids)
            .neq("bcode", bcode)
            .execute()
        )
        related_rows = related_resp.data or []

        if not related_rows:
            return []

        related_bcodes: list[str] = []
        seen_bcodes = set()

        for row in related_rows:
            related_code = str(row.get("bcode", "")).strip()
            if related_code and related_code != bcode and related_code not in seen_bcodes:
                seen_bcodes.add(related_code)
                related_bcodes.append(related_code)

        if not related_bcodes:
            return []

        product_resp = (
            self.client.table("v_pos_products_hq")
            .select(PRODUCT_SELECT)
            .in_("BCODE", related_bcodes)
            .execute()
        )
        product_rows = product_resp.data or []

        if not product_rows:
            return []

        product_map = {
            str(row["BCODE"]): self._row_to_product(row)
            for row in product_rows
        }

        ordered_products: list[Product] = []
        for code in related_bcodes:
            product = product_map.get(code)
            if product is not None:
                ordered_products.append(product)

        return ordered_products

    def _row_to_product(self, row: dict) -> Product:
        return Product(
            bcode=str(row.get("BCODE", "")),
            descr=row.get("DESCR"),
            model=row.get("MODEL"),
            brand=row.get("BRAND"),
            price1=self._to_float(row.get("PRICE1")),
            hq_location1=self._to_text(row.get("HQ_LOCATION1")),
            syp_location1=self._to_text(row.get("SYP_LOCATION1")),
        )

    @staticmethod
    def _to_float(value) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_text(value) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None