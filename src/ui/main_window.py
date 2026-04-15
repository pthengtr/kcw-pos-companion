from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from src.scanner.barcode_listener import BarcodeListener


class BarcodeBridge(QObject):
    barcode_detected = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Legacy POS Barcode Companion")
        self.resize(700, 260)

        self.status_label = QLabel("Waiting for barcode scan...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 28px; font-weight: 600;")

        self.barcode_label = QLabel("-")
        self.barcode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.barcode_label.setStyleSheet("font-size: 44px; padding: 16px;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.status_label)
        layout.addWidget(self.barcode_label)
        self.setCentralWidget(container)

        self.bridge = BarcodeBridge()
        self.bridge.barcode_detected.connect(self.on_barcode_detected)

        self.listener = BarcodeListener(on_barcode=self.handle_barcode_from_listener)
        self.listener.start()

    def handle_barcode_from_listener(self, barcode: str) -> None:
        print(f"Detected barcode: {barcode}")
        self.bridge.barcode_detected.emit(barcode)

    def on_barcode_detected(self, barcode: str) -> None:
        self.status_label.setText("Scanned barcode")
        self.barcode_label.setText(barcode)

    def closeEvent(self, event) -> None:
        self.listener.stop()
        super().closeEvent(event)