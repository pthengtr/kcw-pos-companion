# Placeholder for future Supabase lookup service
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from src.core.models import Product


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
            .select("BCODE, DESCR, MODEL, BRAND, PRICE1")
            .eq("BCODE", barcode)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        if not rows:
            return None

        row = rows[0]

        return Product(
            bcode=str(row.get("BCODE", "")),
            descr=row.get("DESCR"),
            model=row.get("MODEL"),
            brand=row.get("BRAND"),
            price1=self._to_float(row.get("PRICE1")),
        )

    @staticmethod
    def _to_float(value) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None