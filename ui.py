import sys
from main import get_route, summarize_route
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon


class RouteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Route Finder")
        self.setWindowIcon(QIcon("icon.png"))
        self.setFixedSize(420, 440)
        self.last_route = None  # holds the simplified route dict once fetched
        self.showing_summary = False
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

        self.summarize_btn = QPushButton("Summarize")
        self.summarize_btn.setObjectName("summarizeBtn")
        self.summarize_btn.setEnabled(False)  # nothing to summarize yet
        self.summarize_btn.clicked.connect(self.on_summarize)

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

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.submit_btn)
        btn_row.addWidget(self.summarize_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_row)
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
        self.summarize_btn.setEnabled(False)
        self.last_route = None
        self.showing_summary = False
        self.status_label.setText("Loading...")
        self.result_box.clear()
        # lets the "Loading..." text render before the blocking call
        QApplication.processEvents()

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
            self.last_route = result["data"]
            self.render_full_route()
            self.summarize_btn.setEnabled(True)
        else:
            self.status_label.setText(f"Error ({status})")
            self.result_box.setPlainText(
                result.get("message", "Unknown error"))

        self.submit_btn.setEnabled(True)

    def render_full_route(self):
        """Show the full turn-by-turn directions in the result box."""
        route = self.last_route
        s = route["summary"]
        lines = [
            f"Distance: {s['distance_miles']} mi ({s['distance_km']} km)",
            f"Estimated time: {s['time_formatted']}",
            "",
            "Turn-by-turn directions:",
        ]
        for step in route.get("steps", []):
            lines.append(f"{step['step']}. {step['instruction']}")
        self.result_box.setPlainText("\n".join(lines))
        self.showing_summary = False
        self.summarize_btn.setText("Summarize")

    def on_summarize(self):
        """Toggle between the full turn-by-turn list and a condensed summary."""
        if not self.last_route:
            return

        if self.showing_summary:
            self.render_full_route()
        else:
            self.result_box.setPlainText(summarize_route(self.last_route))
            self.showing_summary = True
            self.summarize_btn.setText("Show Full Directions")


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
