import sys
import serial
import time
from collections import deque

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit
)
from PyQt6.QtCore import QTimer
import pyqtgraph as pg


# ==============================
# CONFIGURE YOUR SERIAL PORT
# ==============================

SERIAL_PORT = "/dev/cu.usbmodem101"  # Mac example
BAUD_RATE = 9600


class CentrifugeGUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Centrifuge Control Panel")
        self.resize(800, 600)

        # ==============================
        # SERIAL CONNECTION
        # ==============================
        self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)  # allow Arduino reset

        # ==============================
        # DATA STORAGE
        # ==============================
        self.rpm_data = deque(maxlen=500)
        self.time_data = deque(maxlen=500)
        self.start_time = time.time()

        # ==============================
        # LAYOUT
        # ==============================
        main_layout = QVBoxLayout()

        # -------- TOP SECTION --------
        top_layout = QHBoxLayout()

        self.rpm_input = QLineEdit()
        self.rpm_input.setPlaceholderText("Target RPM")

        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("Duration (sec)")

        self.start_button = QPushButton("GO")
        self.stop_button = QPushButton("STOP")

        top_layout.addWidget(self.rpm_input)
        top_layout.addWidget(self.duration_input)
        top_layout.addWidget(self.start_button)
        top_layout.addWidget(self.stop_button)

        main_layout.addLayout(top_layout)

        # -------- BOTTOM SECTION --------
        bottom_layout = QVBoxLayout()

        self.rpm_label = QLabel("Current RPM: 0")
        self.pwm_label = QLabel("Current PWM: 0")

        bottom_layout.addWidget(self.rpm_label)
        bottom_layout.addWidget(self.pwm_label)

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("RPM vs Time")
        self.plot_widget.setLabel("left", "RPM")
        self.plot_widget.setLabel("bottom", "Time", "s")

        self.curve = self.plot_widget.plot()

        bottom_layout.addWidget(self.plot_widget)

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

        # ==============================
        # BUTTON CONNECTIONS
        # ==============================
        self.start_button.clicked.connect(self.start_motor)
        self.stop_button.clicked.connect(self.stop_motor)

        # ==============================
        # TIMER FOR UPDATES
        # ==============================
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(50)  # update every 50 ms

    # ==============================
    # SEND COMMANDS
    # ==============================

    def start_motor(self):
        target = self.rpm_input.text()
        duration = self.duration_input.text()

        if target:
            self.ser.write(f"SET:{target}\n".encode())

        self.ser.write(b"START\n")

        if duration:
            QTimer.singleShot(int(duration) * 1000, self.stop_motor)

    def stop_motor(self):
        self.ser.write(b"STOP\n")

    # ==============================
    # UPDATE LOOP
    # ==============================

    def update_data(self):

        while self.ser.in_waiting:
            line = self.ser.readline().decode().strip()

            try:
                rpm, pwm = line.split(",")
                rpm = float(rpm)
                pwm = int(pwm)

                current_time = time.time() - self.start_time

                self.time_data.append(current_time)
                self.rpm_data.append(rpm)

                self.rpm_label.setText(f"Current RPM: {rpm:.1f}")
                self.pwm_label.setText(f"Current PWM: {pwm}")

                self.curve.setData(self.time_data, self.rpm_data)

            except:
                pass


# ==============================
# RUN APPLICATION
# ==============================

app = QApplication(sys.argv)
window = CentrifugeGUI()
window.show()
sys.exit(app.exec())