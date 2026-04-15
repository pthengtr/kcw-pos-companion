from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal, QThread
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.models import Product
from src.scanner.barcode_listener import BarcodeListener
from src.services.lookup_worker import LookupWorker


class BarcodeBridge(QObject):
    barcode_detected = Signal(str)


class MainWindow(QMainWindow):
    request_lookup = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("KCW POS Companion")
        self.resize(430, 760)
        self.setMinimumWidth(390)
        self.setMaximumWidth(540)

        self._always_on_top = True
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._latest_requested_barcode: str | None = None

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f7fb;
            }
            QLabel {
                color: #1f2937;
            }
            QFrame#Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 8px 10px;
                color: #111827;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            """
        )

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ===== Header =====
        header_card = self._make_card()
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(8)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        self.header_title = QLabel("KCW POS Companion")
        self.header_title.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #111827;"
        )

        self.status_label = QLabel("พร้อมใช้งาน")
        self.status_label.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #0a7f42;"
        )

        title_layout.addWidget(self.header_title)
        title_layout.addWidget(self.status_label)

        self.pin_button = QPushButton("ปักหมุด")
        self.pin_button.setFixedHeight(32)
        self.pin_button.setStyleSheet(self._pin_button_style(True))
        self.pin_button.clicked.connect(self.toggle_always_on_top)

        self.clear_button = QPushButton("ล้างผล")
        self.clear_button.setFixedHeight(32)
        self.clear_button.setStyleSheet(
            """
            QPushButton {
                font-size: 12px;
                font-weight: 700;
                padding: 0 12px;
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #fca5a5;
                color: #ffffff;
            }
            """
        )
        self.clear_button.clicked.connect(self.on_clear_clicked)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.pin_button)
        header_layout.addWidget(self.clear_button)

        # ===== Search Card =====
        search_card = self._make_card()
        search_layout = QVBoxLayout(search_card)
        search_layout.setContentsMargins(12, 12, 12, 12)
        search_layout.setSpacing(8)

        self.manual_title = QLabel("กรอกรหัสสินค้า / BCODE")
        self.manual_title.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #374151;"
        )

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText("กรอก BCODE 8 หลัก")
        self.manual_input.setMaxLength(8)
        self.manual_input.setValidator(QIntValidator(0, 99999999, self))
        self.manual_input.setMinimumHeight(38)
        self.manual_input.setStyleSheet(
            """
            QLineEdit {
                font-size: 15px;
                font-weight: 600;
            }
            """
        )
        self.manual_input.returnPressed.connect(self.on_manual_submit)

        self.search_button = QPushButton("ค้นหา")
        self.search_button.setMinimumHeight(38)
        self.search_button.setStyleSheet(
            """
            QPushButton {
                font-size: 13px;
                font-weight: 700;
                padding: 0 14px;
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #93c5fd;
                color: #ffffff;
            }
            """
        )
        self.search_button.clicked.connect(self.on_manual_submit)

        input_row.addWidget(self.manual_input, 1)
        input_row.addWidget(self.search_button)

        search_layout.addWidget(self.manual_title)
        search_layout.addLayout(input_row)

        # ===== Current Product Card =====
        current_card = self._make_card()
        current_layout = QVBoxLayout(current_card)
        current_layout.setContentsMargins(12, 12, 12, 12)
        current_layout.setSpacing(8)

        self.scanned_title = QLabel("สินค้าที่สแกน")
        self.scanned_title.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #374151;"
        )

        self.current_product_label = QLabel("")
        self.current_product_label.setWordWrap(True)
        self.current_product_label.setTextFormat(Qt.TextFormat.RichText)
        self.current_product_label.setStyleSheet("font-size: 14px; color: #111827;")

        current_layout.addWidget(self.scanned_title)
        current_layout.addWidget(self.current_product_label)

        # ===== Related Products Card =====
        related_card = self._make_card()
        related_layout = QVBoxLayout(related_card)
        related_layout.setContentsMargins(12, 12, 12, 12)
        related_layout.setSpacing(8)

        self.related_title = QLabel("นิยมซื้อด้วยกัน")
        self.related_title.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #374151;"
        )

        self.related_empty_label = QLabel("ยังไม่มีสินค้าที่เกี่ยวข้อง")
        self.related_empty_label.setStyleSheet(
            "font-size: 12px; color: #9ca3af; padding: 4px 0;"
        )

        related_layout.addWidget(self.related_title)
        related_layout.addWidget(self.related_empty_label)

        self.related_product_labels: list[QLabel] = []
        for _ in range(3):
            label = QLabel("")
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setStyleSheet(
                """
                QLabel {
                    background-color: #f9fafb;
                    border: 1px solid #e5e7eb;
                    border-radius: 10px;
                    padding: 8px;
                    color: #111827;
                }
                """
            )
            label.hide()
            self.related_product_labels.append(label)
            related_layout.addWidget(label)

        root.addWidget(header_card)
        root.addWidget(search_card)
        root.addWidget(current_card)
        root.addWidget(related_card)
        root.addStretch()

        # ===== Barcode bridge =====
        self.bridge = BarcodeBridge()
        self.bridge.barcode_detected.connect(self.process_barcode)

        # ===== Scanner listener =====
        self.listener = BarcodeListener(on_barcode=self.handle_barcode_from_listener)
        self.listener.start()

        # ===== Worker thread =====
        self.lookup_thread = QThread(self)
        self.lookup_worker = LookupWorker()
        self.lookup_worker.moveToThread(self.lookup_thread)

        self.request_lookup.connect(self.lookup_worker.lookup)
        self.lookup_worker.finished.connect(self.on_lookup_finished)
        self.lookup_worker.error.connect(self.on_lookup_error)

        self.lookup_thread.start()

        self.manual_input.setFocus()

    def _make_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _pin_button_style(self, pinned: bool) -> str:
        if pinned:
            return """
                QPushButton {
                    font-size: 12px;
                    font-weight: 700;
                    padding: 0 12px;
                    background-color: #374151;
                    color: white;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #1f2937;
                }
            """
        return """
            QPushButton {
                font-size: 12px;
                font-weight: 700;
                padding: 0 12px;
                background-color: #9ca3af;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #6b7280;
            }
        """

    def toggle_always_on_top(self) -> None:
        self._always_on_top = not self._always_on_top
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._always_on_top)
        self.show()
        self.pin_button.setText("ปักหมุด" if self._always_on_top else "ไม่ปักหมุด")
        self.pin_button.setStyleSheet(self._pin_button_style(self._always_on_top))

    def handle_barcode_from_listener(self, barcode: str) -> None:
        self.bridge.barcode_detected.emit(barcode)

    def on_manual_submit(self) -> None:
        barcode = self.manual_input.text().strip()

        if not barcode.isdigit() or len(barcode) != 8:
            self._set_status("กรุณากรอก BCODE 8 หลัก", "error")
            return

        self.process_barcode(barcode)

    def process_barcode(self, barcode: str) -> None:
        self._latest_requested_barcode = barcode
        self.manual_input.setText(barcode)

        self.current_product_label.setText(
            (
                f"<div style='font-size:13px; color:#6b7280;'>กำลังค้นหา</div>"
                f"<div style='font-size:18px; font-weight:700; color:#111827; margin-top:2px;'>{barcode}</div>"
            )
        )
        self._render_related_products([])
        self._set_busy(True)
        self._set_status("กำลังค้นหาสินค้า...", "loading")
        self.request_lookup.emit(barcode)

    def on_lookup_finished(
        self,
        barcode: str,
        current_product: Product | None,
        related_products: list[Product],
    ) -> None:
        if barcode != self._latest_requested_barcode:
            return

        self._set_busy(False)

        if current_product is None:
            self._set_status("ไม่พบสินค้า", "error")
            self._clear_result_fields()
            return

        self._set_status("พร้อมขาย", "ready")
        self.current_product_label.setText(
            self._format_current_product(current_product)
        )
        self._render_related_products(related_products[:3])

    def on_lookup_error(self, barcode: str, message: str) -> None:
        if barcode != self._latest_requested_barcode:
            return

        self._set_busy(False)
        self._set_status(f"Lookup error: {message}", "error")
        self._clear_result_fields()

    def _set_busy(self, is_busy: bool) -> None:
        self.search_button.setEnabled(not is_busy)
        self.clear_button.setEnabled(not is_busy)
        self.manual_input.setEnabled(not is_busy)

    def _set_status(self, text: str, state: str) -> None:
        color = "#0a7f42"
        if state == "loading":
            color = "#9a6700"
        elif state == "error":
            color = "#dc2626"

        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {color};"
        )

    def _format_current_product(self, product: Product) -> str:
        descr = product.descr or "-"
        model = product.model or "-"
        brand = product.brand or "-"
        price = self._format_price(product.price1)

        return (
            f"<div style='font-size:20px; font-weight:700; color:#111827;'>{descr}</div>"
            f"<div style='font-size:12px; color:#6b7280; margin-top:4px;'>"
            f"BCODE {product.bcode} • {model} • {brand}"
            f"</div>"
            f"<div style='font-size:22px; font-weight:700; color:#0a7f42; margin-top:10px;'>"
            f"฿ {price}"
            f"</div>"
        )

    def _format_related_product(self, product: Product, idx: int) -> str:
        descr = product.descr or "-"
        price = self._format_price(product.price1)

        return (
            f"<div style='font-size:12px; color:#6b7280;'>แนะนำ {idx + 1}</div>"
            f"<div style='font-size:14px; font-weight:700; color:#111827; margin-top:2px;'>"
            f"{product.bcode}"
            f"</div>"
            f"<div style='font-size:13px; color:#1f2937; margin-top:2px;'>"
            f"{descr}"
            f"</div>"
            f"<div style='font-size:15px; font-weight:700; color:#0a7f42; margin-top:6px;'>"
            f"฿ {price}"
            f"</div>"
        )

    def _render_related_products(self, products: list[Product]) -> None:
        has_products = len(products) > 0
        self.related_empty_label.setVisible(not has_products)

        for idx, label in enumerate(self.related_product_labels):
            if idx < len(products):
                label.setText(self._format_related_product(products[idx], idx))
                label.show()
            else:
                label.setText("")
                label.hide()

    def _clear_result_fields(self) -> None:
        self.current_product_label.setText("")
        self.related_empty_label.setVisible(True)

        for label in self.related_product_labels:
            label.setText("")
            label.hide()

    def on_clear_clicked(self) -> None:
        self._latest_requested_barcode = None
        self.manual_input.clear()
        self._set_status("พร้อมใช้งาน", "ready")
        self._clear_result_fields()
        self.manual_input.setEnabled(True)
        self.search_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.manual_input.setFocus()

    def _format_price(self, value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:,.2f}"

    def closeEvent(self, event) -> None:
        self.listener.stop()
        self.lookup_thread.quit()
        self.lookup_thread.wait()
        super().closeEvent(event)