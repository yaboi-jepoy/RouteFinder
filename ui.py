import sys
from main import get_route
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

class RouteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Route Finder")
        self.setWindowIcon(QIcon("icon.png"))
        self.setFixedSize(420, 380)
        self.init_ui()

    def init_ui(self):
        # --- Widgets ---
        self.origin_input = QLineEdit()
        self.origin_input.setObjectName("originField")
        self.origin_input.setPlaceholderText("e.g. New York, NY")

        self.dest_input = QLineEdit()
        self.dest_input.setObjectName("destField")
        self.dest_input.setPlaceholderText("e.g. Boston, MA")

        self.submit_btn = QPushButton("Get Route")
        self.submit_btn.setObjectName("submitBtn")
        self.submit_btn.clicked.connect(self.on_submit)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")

        self.result_box = QTextEdit()
        self.result_box.setObjectName("resultBox")
        self.result_box.setReadOnly(True)

        # --- Layout ---
        form_layout = QFormLayout()
        form_layout.addRow(QLabel("From:"), self.origin_input)
        form_layout.addRow(QLabel("To:"), self.dest_input)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.submit_btn)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.result_box)

        self.setLayout(main_layout)

    def on_submit(self):
        orig = self.origin_input.text().strip()
        dest = self.dest_input.text().strip()

        if not orig or not dest:
            self.status_label.setText("Please fill in both fields.")
            self.result_box.clear()
            return

        self.submit_btn.setEnabled(False)
        self.status_label.setText("Loading...")
        self.result_box.clear()
        QApplication.processEvents()  # lets the "Loading..." text render before the blocking call

        try:
            result = get_route(orig, dest)
        except Exception as e:
            self.status_label.setText("Request failed.")
            self.result_box.setPlainText(str(e))
            self.submit_btn.setEnabled(True)
            return

        status = result.get("status")

        if status == 0:
            self.status_label.setText("Route found!")
            summary_info = result["data"].get("summary", {})
            distance = summary_info.get("distance_miles")
            time_sec = summary_info.get("time_seconds")
            summary = f"Distance: {distance} miles\n"
            if time_sec is not None:
                hours = time_sec // 3600
                minutes = (time_sec % 3600) // 60
                summary += f"Estimated time: {int(hours)}h {int(minutes)}m\n"
            self.result_box.setPlainText(summary)
        else:
            self.status_label.setText(f"Error ({status})")
            self.result_box.setPlainText(result.get("message", "Unknown error"))

        self.submit_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        with open("style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass  # runs without styling if the file is missing

    window = RouteApp()
    window.show()
    app.exec()