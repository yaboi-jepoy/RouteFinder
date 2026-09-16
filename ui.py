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
        self.use_km = True
        self.current_route = None
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
        
        # km toggle button
        self.unit_toggle = QPushButton("Show km")
        self.unit_toggle.setCheckable(True)
        self.unit_toggle.toggled.connect(self.on_unit_toggled)

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
        main_layout.addWidget(self.unit_toggle)
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
            self.current_route = result["data"]
            self.display_route_summary()

        self.submit_btn.setEnabled(True)


    def on_unit_toggled(self, checked):
        self.use_km = checked
        self.unit_toggle.setText("Show km" if checked else "Show miles")
        self.display_route_summary()


    def display_route_summary(self):
        if not self.current_route:
            return

        summary_info = self.current_route.get("summary", {})
        query = self.current_route.get("query", {})
        origin = self.current_route.get("origin", {})
        destination = self.current_route.get("destination", {})
        warnings = summary_info.get("route_warnings", {})
        steps = self.current_route.get("steps", [])

        if self.use_km:
            distance = summary_info.get("distance_km")
            unit = "km"
        else:
            distance = summary_info.get("distance_miles")
            unit = "miles"

        time_sec = summary_info.get("time_seconds")
        summary = (
            f"From: {query.get('origin')}\n"
            f"To: {query.get('destination')}\n"
            f"Distance: {distance} {unit}\n"
            f"Estimated time: {int(time_sec // 3600)}h "
            f"{int((time_sec % 3600) // 60)}m\n"
            f"Navigation steps: {len(steps)}\n"
            f"Toll road: {'Yes' if warnings.get('toll_road') else 'No'}\n"
            f"Highway: {'Yes' if warnings.get('highway') else 'No'}\n"
        )

        self.result_box.setPlainText(summary)


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