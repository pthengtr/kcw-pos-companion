from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal, QThread
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
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

        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.show()

        self.resize(420, 760)
        self.setMinimumWidth(380)
        self.setMaximumWidth(520)

        self._latest_requested_barcode: str | None = None
        self._always_on_top = True

        # ===== Top row =====
        self.status_label = QLabel("พร้อมใช้งาน")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: 700;
            color: #0a7f42;
            padding: 6px 0;
            """
        )

        self.pin_button = QPushButton("ปักหมุด")
        self.pin_button.setFixedHeight(34)
        self.pin_button.setStyleSheet(
            """
            QPushButton {
                font-size: 13px;
                font-weight: 700;
                padding: 6px 10px;
                background-color: #444;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            """
        )
        self.pin_button.clicked.connect(self.toggle_always_on_top)

        self.clear_button = QPushButton("ล้างผล")
        self.clear_button.setFixedHeight(34)
        self.clear_button.setStyleSheet(
            """
            QPushButton {
                font-size: 13px;
                font-weight: 700;
                padding: 6px 10px;
                background-color: #d9534f;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            """
        )
        self.clear_button.clicked.connect(self.on_clear_clicked)

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(self.pin_button)
        status_row.addWidget(self.clear_button)

        # ===== Manual input =====
        self.manual_title = QLabel("กรอกรหัสสินค้า / BCODE")
        self.manual_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; padding-top: 4px;"
        )

        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText("กรอก BCODE 8 หลัก")
        self.manual_input.setMaxLength(8)
        self.manual_input.setValidator(QIntValidator(0, 99999999, self))
        self.manual_input.setStyleSheet(
            """
            font-size: 16px;
            padding: 8px 10px;
            min-height: 38px;
            border: 1px solid #cccccc;
            border-radius: 6px;
            """
        )
        self.manual_input.returnPressed.connect(self.on_manual_submit)

        self.search_button = QPushButton("ค้นหา")
        self.search_button.setStyleSheet(
            """
            font-size: 15px;
            font-weight: 700;
            padding: 8px 12px;
            min-height: 38px;
            background-color: #2d6cdf;
            color: white;
            border: none;
            border-radius: 6px;
            """
        )
        self.search_button.clicked.connect(self.on_manual_submit)

        manual_row = QHBoxLayout()
        manual_row.setSpacing(8)
        manual_row.addWidget(self.manual_input, stretch=1)
        manual_row.addWidget(self.search_button)

        # ===== Scanned product =====
        self.scanned_title = QLabel("สินค้าที่สแกน")
        self.scanned_title.setStyleSheet(
            "font-size: 18px; font-weight: 700; padding-top: 10px;"
        )

        self.current_divider = QLabel("")
        self.current_divider.setFixedHeight(2)
        self.current_divider.setStyleSheet("background-color: #dddddd;")

        self.current_product_label = QLabel("")
        self.current_product_label.setWordWrap(True)
        self.current_product_label.setTextFormat(Qt.TextFormat.RichText)
        self.current_product_label.setStyleSheet(
            """
            font-size: 14px;
            padding: 8px 0 10px 0;
            """
        )

        # ===== Related products =====
        self.related_title = QLabel("นิยมซื้อด้วยกัน")
        self.related_title.setStyleSheet(
            "font-size: 18px; font-weight: 700; padding-top: 8px;"
        )

        self.related_divider = QLabel("")
        self.related_divider.setFixedHeight(2)
        self.related_divider.setStyleSheet("background-color: #dddddd;")

        self.related_product_labels: list[QLabel] = []
        for _ in range(3):
            label = QLabel("-")
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setStyleSheet(
                """
                font-size: 14px;
                padding: 6px 0;
                """
            )
            label.hide()
            self.related_product_labels.append(label)

        # ===== Main layout =====
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        layout.addLayout(status_row)
        layout.addWidget(self.manual_title)
        layout.addLayout(manual_row)
        layout.addSpacing(4)
        layout.addWidget(self.scanned_title)
        layout.addWidget(self.current_divider)
        layout.addWidget(self.current_product_label)
        layout.addWidget(self.related_title)
        layout.addWidget(self.related_divider)

        for label in self.related_product_labels:
            layout.addWidget(label)

        layout.addStretch()

        self.setCentralWidget(container)

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

        # Show immediate feedback before lookup returns
        self.current_product_label.setText(
            (
                f"<div style='font-size:18px; font-weight:700; color:#222;'>กำลังค้นหา...</div>"
                f"<div style='font-size:13px; margin-top:3px; color:#666;'>{barcode}</div>"
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
            color = "#c0392b"

        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"""
            font-size: 14px;
            font-weight: 700;
            color: {color};
            padding: 4px 0;
            """
        )

    def _format_current_product(self, product: Product) -> str:
        descr = product.descr or "-"
        model = product.model or "-"
        brand = product.brand or "-"
        price = self._format_price(product.price1)

        return (
            f"<div style='font-size:18px; font-weight:700; color:#222;'>{descr}</div>"
            f"<div style='font-size:13px; margin-top:3px; color:#666;'>"
            f"{product.bcode} • {model} • {brand}"
            f"</div>"
            f"<div style='font-size:20px; font-weight:700; margin-top:8px; color:#0a7f42;'>"
            f"฿ {price}"
            f"</div>"
        )

    def _format_related_product(self, product: Product, idx: int) -> str:
        descr = product.descr or "-"
        price = self._format_price(product.price1)

        return (
            f"<div style='font-size:15px;'>"
            f"<span style='font-weight:700; color:#333;'>{idx + 1}.</span> "
            f"<span style='font-weight:700; color:#111;'>{product.bcode}</span>"
            f"</div>"
            f"<div style='font-size:14px; color:#222; margin-top:2px; margin-left:16px;'>"
            f"{descr}"
            f"</div>"
            f"<div style='font-size:15px; font-weight:700; color:#0a7f42; margin-top:3px; margin-left:16px;'>"
            f"฿ {price}"
            f"</div>"
        )

    def _render_related_products(self, products: list[Product]) -> None:
        for idx, label in enumerate(self.related_product_labels):
            if idx < len(products):
                label.setText(self._format_related_product(products[idx], idx))
                label.show()
            else:
                label.hide()

    def _clear_result_fields(self) -> None:
        self.current_product_label.setText("")

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

    def toggle_always_on_top(self) -> None:
        self._always_on_top = not self._always_on_top

        self.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint,
            self._always_on_top
        )

        # IMPORTANT: re-show window to apply change
        self.show()

        if self._always_on_top:
            self.pin_button.setText("📌 ปักหมุด")
            self.pin_button.setStyleSheet(
                """
                font-size: 14px;
                font-weight: 700;
                padding: 6px 10px;
                min-height: 32px;
                background-color: #555;
                color: white;
                border: none;
                border-radius: 6px;
                """
            )
        else:
            self.pin_button.setText("ปลดหมุด")
            self.pin_button.setStyleSheet(
                """
                font-size: 14px;
                font-weight: 700;
                padding: 6px 10px;
                min-height: 32px;
                background-color: #999;
                color: white;
                border: none;
                border-radius: 6px;
                """
            )