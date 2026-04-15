from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from src.core.models import Product
from src.services.product_service import ProductService


class LookupWorker(QObject):
    finished = Signal(str, object, list)
    error = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.product_service = ProductService()

    @Slot(str)
    def lookup(self, barcode: str) -> None:
        try:
            current_product = self.product_service.get_product_by_barcode(barcode)
            related_products = self.product_service.get_related_products(barcode)
            self.finished.emit(barcode, current_product, related_products)
        except Exception as exc:
            self.error.emit(barcode, str(exc))