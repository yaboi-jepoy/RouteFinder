import sys
from main import get_route, summarize_route
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont

class RouteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Route Finder")
        self.setWindowIcon(QIcon("icon.png"))
        self.setFixedSize(420, 650)
        self.use_km = True
        self.current_route = None
        self.current_step = 0
        self.current_instruction = ""
        self.current_step_index = 0
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

        # Separate button: switches the displayed distance unit (km <-> miles)
        self.metrics_btn = QPushButton("Show miles")
        self.metrics_btn.setObjectName("metricsBtn")
        self.metrics_btn.clicked.connect(self.on_change_metrics)

        # Separate button: opens the text-report summary in its own dialog
        self.summarize_btn = QPushButton("Summarize")
        self.summarize_btn.setObjectName("summarizeBtn")
        self.summarize_btn.clicked.connect(self.on_summarize)
        self.summarize_btn.setEnabled(False)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")

        self.result_box = QTextEdit()
        self.result_box.setObjectName("resultBox")
        self.result_box.setReadOnly(True)
        self.result_box.setFixedHeight(160)

        self.step_box = QTextEdit()
        self.step_box.setObjectName("stepBox")
        self.step_box.setReadOnly(True)
        self.step_box.setFixedHeight(220)

        self.previous_btn = QPushButton("Previous Step")
        self.previous_btn.setObjectName("previousBtn")
        self.previous_btn.clicked.connect(self.show_previous_step)

        self.next_btn = QPushButton("Next Step")
        self.next_btn.setObjectName("nextBtn")
        self.next_btn.clicked.connect(self.show_next_step)

        # --- Layout ---
        form_layout = QFormLayout()
        form_layout.addRow(QLabel("From:"), self.origin_input)
        form_layout.addRow(QLabel("To:"), self.dest_input)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.submit_btn)
        main_layout.addWidget(self.metrics_btn)
        main_layout.addWidget(self.summarize_btn)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.result_box)
        main_layout.addWidget(self.step_box)
        main_layout.addWidget(self.previous_btn)
        main_layout.addWidget(self.next_btn)
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
            self.current_step_index = 0
            self.summarize_btn.setEnabled(True)
            self.display_route_summary()
            self.display_current_step()
        else:
            self.status_label.setText(result.get("message", "Something went wrong."))
            self.current_route = None
            self.summarize_btn.setEnabled(False)

        self.submit_btn.setEnabled(True)

    def on_change_metrics(self):
        """Toggle between km and miles for the currently displayed route."""
        self.use_km = not self.use_km
        self.metrics_btn.setText("Show miles" if self.use_km else "Show km")
        self.display_route_summary()
        self.display_current_step()

    def on_summarize(self):
        """Build the text report via main.summarize_route() and show it in a dialog."""
        if not self.current_route:
            return

        report_text = summarize_route(self.current_route)

        dialog = QDialog(self)
        dialog.setWindowTitle("Trip Summary Report")
        dialog.setFixedSize(380, 420)

        report_box = QTextEdit(dialog)
        report_box.setReadOnly(True)
        report_box.setPlainText(report_text)
        report_box.setFont(QFont("Consolas", 10))

        layout = QVBoxLayout(dialog)
        layout.addWidget(report_box)
        dialog.setLayout(layout)
        dialog.exec()

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
            f"Origin city: {origin.get('city')}, {origin.get('state')}\n"
            f"Destination city: {destination.get('city')}, "
            f"{destination.get('state')}\n"
            f"Distance: {distance} {unit}\n"
            f"Estimated time: {int(time_sec // 3600)}h "
            f"{int((time_sec % 3600) // 60)}m\n"
            f"Navigation steps: {len(steps)}\n"
            f"Toll road: {'Yes' if warnings.get('toll_road') else 'No'}\n"
            f"Highway: {'Yes' if warnings.get('highway') else 'No'}\n"
        )

        self.result_box.setPlainText(summary)

        self.show_steps(steps)


    def show_steps(self, steps):
        self.step_box.clear()
        for step in steps:
            self.step_box.append(f"Step {step['step']}: {step['instruction']}")

        self.step_box.setPlainText(self.step_box.toPlainText())


    def show_previous_step(self):
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self.display_current_step()


    def show_next_step(self):
        if not self.current_route:
            return

        steps = self.current_route.get("steps", [])

        if self.current_step_index < len(steps) - 1:
            self.current_step_index += 1
            self.display_current_step()


    def display_current_step(self):
        if not self.current_route:
            self.step_box.clear()
            return

        steps = self.current_route.get("steps", [])

        if not steps:
            self.step_box.setPlainText("No navigation steps available.")
            self.previous_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        step = steps[self.current_step_index]

        distance = (
            step.get("distance_km")
            if self.use_km
            else step.get("distance_miles")
        )
        unit = "km" if self.use_km else "miles"

        step_text = (
            f"Step {step.get('step')} of {len(steps)}\n\n"
            f"{step.get('instruction', 'No instruction available.')}\n\n"
            f"Street: {step.get('street') or 'Unnamed road'}\n"
            f"Distance: {distance} {unit}\n"
            f"Time: {step.get('time_formatted', 'Unknown')}"
        )

        self.step_box.setPlainText(step_text)
        self.previous_btn.setEnabled(self.current_step_index > 0)
        self.next_btn.setEnabled(self.current_step_index < len(steps) - 1)


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