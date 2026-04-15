from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import (
    QLabel,
    QGridLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from src.core.models import Product
from src.scanner.barcode_listener import BarcodeListener
from src.services.product_service import ProductService
from PySide6.QtGui import QKeySequence, QShortcut


class BarcodeBridge(QObject):
    barcode_detected = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Legacy POS Barcode Companion")
        self.resize(900, 420)

        self.product_service = ProductService()

        self.status_label = QLabel("Waiting for barcode scan...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 24px; font-weight: 600; padding: 8px;")

        self.barcode_label = QLabel("-")
        self.barcode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.barcode_label.setStyleSheet("font-size: 40px; font-weight: 700; padding: 12px;")

        self.clear_button = QPushButton("Clear")
        self.clear_button.setStyleSheet(
            "font-size: 18px; padding: 10px; background-color: #444; color: white;"
        )
        self.clear_button.clicked.connect(self.on_clear_clicked)

        self.descr_value = QLabel("-")
        self.model_value = QLabel("-")
        self.brand_value = QLabel("-")
        self.price1_value = QLabel("-")

        for label in [self.descr_value, self.model_value, self.brand_value, self.price1_value]:
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 22px; padding: 6px;")

        shortcut = QShortcut(QKeySequence("Esc"), self)
        shortcut.activated.connect(self.on_clear_clicked)   

        details_widget = QWidget()
        details_layout = QGridLayout(details_widget)
        details_layout.addWidget(self._make_title_label("DESCR"), 0, 0)
        details_layout.addWidget(self.descr_value, 0, 1)
        details_layout.addWidget(self._make_title_label("MODEL"), 1, 0)
        details_layout.addWidget(self.model_value, 1, 1)
        details_layout.addWidget(self._make_title_label("BRAND"), 2, 0)
        details_layout.addWidget(self.brand_value, 2, 1)
        details_layout.addWidget(self._make_title_label("PRICE1"), 3, 0)
        details_layout.addWidget(self.price1_value, 3, 1)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.status_label)
        layout.addWidget(self.barcode_label)
        layout.addWidget(details_widget)
        layout.addWidget(self.clear_button)
        self.setCentralWidget(container)

        self.bridge = BarcodeBridge()
        self.bridge.barcode_detected.connect(self.on_barcode_detected)

        self.listener = BarcodeListener(on_barcode=self.handle_barcode_from_listener)
        self.listener.start()

    def _make_title_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 20px; font-weight: 700; padding: 6px;")
        return label

    def handle_barcode_from_listener(self, barcode: str) -> None:
        self.bridge.barcode_detected.emit(barcode)

    def on_barcode_detected(self, barcode: str) -> None:
        self.barcode_label.setText(barcode)
        self.status_label.setText("Looking up product...")

        try:
            product = self.product_service.get_product_by_barcode(barcode)
        except Exception as exc:
            self.status_label.setText(f"Lookup error: {exc}")
            self._clear_product_fields()
            return

        if product is None:
            self.status_label.setText("Product not found")
            self._clear_product_fields()
            return

        self.status_label.setText("Current product")
        self._render_product(product)

    def _render_product(self, product: Product) -> None:
        self.descr_value.setText(product.descr or "-")
        self.model_value.setText(product.model or "-")
        self.brand_value.setText(product.brand or "-")
        self.price1_value.setText(self._format_price(product.price1))

    def _clear_product_fields(self) -> None:
        self.descr_value.setText("-")
        self.model_value.setText("-")
        self.brand_value.setText("-")
        self.price1_value.setText("-")

    def _format_price(self, value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:,.2f}"

    def closeEvent(self, event) -> None:
        self.listener.stop()
        super().closeEvent(event)

    def on_clear_clicked(self) -> None:
        self.status_label.setText("Waiting for barcode scan...")
        self.barcode_label.setText("-")
        self._clear_product_fields()