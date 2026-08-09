from __future__ import annotations

import json
import queue
import socket
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar,
    QSpinBox, QTextEdit, QVBoxLayout, QWidget
)

from .audio_engine import AudioEngine
from .controller_server import ControllerServer


def _local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return '127.0.0.1'


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FilmSet Recorder 0.1')
        self.resize(1050, 720)
        self.meter_queue = queue.Queue(maxsize=8)
        self.remote_commands = queue.Queue()
        self.audio = AudioEngine(meter_callback=self._meter_from_audio_thread)
        self.project_dir = Path.home() / 'FilmSetRecorder'
        self.last_take_path: Path | None = None
        self.circle_take = False

        self._build_ui()
        self._load_devices()

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._tick)
        self.ui_timer.start(50)

        self.controller_server = ControllerServer(
            command_sink=self.remote_commands.put,
            state_provider=self.remote_state,
            token='filmset',
        )
        try:
            self.controller_server.start(port=8765)
            self.remote_label.setText(f'Remote: http://{_local_ip()}:8765  token: filmset')
        except OSError as exc:
            self.remote_label.setText(f'Remote server unavailable: {exc}')

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        title = QLabel('FILMSET RECORDER')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 30px; font-weight: 700;')
        main.addWidget(title)

        project_row = QHBoxLayout()
        self.project_label = QLabel(str(self.project_dir))
        choose_project = QPushButton('Project Folder')
        choose_project.clicked.connect(self.choose_project)
        project_row.addWidget(QLabel('Project:'))
        project_row.addWidget(self.project_label, 1)
        project_row.addWidget(choose_project)
        main.addLayout(project_row)

        setup = QGridLayout()
        self.input_combo = QComboBox()
        self.output_combo = QComboBox()
        self.sample_combo = QComboBox()
        self.sample_combo.addItems(['48000', '96000'])
        self.channels_spin = QSpinBox(); self.channels_spin.setRange(1, 16); self.channels_spin.setValue(4)
        refresh = QPushButton('Refresh Devices'); refresh.clicked.connect(self._load_devices)
        apply_audio = QPushButton('Start / Apply Audio'); apply_audio.clicked.connect(self.apply_audio)
        setup.addWidget(QLabel('Input device'), 0, 0); setup.addWidget(self.input_combo, 0, 1)
        setup.addWidget(QLabel('Output device'), 0, 2); setup.addWidget(self.output_combo, 0, 3)
        setup.addWidget(QLabel('Sample rate'), 1, 0); setup.addWidget(self.sample_combo, 1, 1)
        setup.addWidget(QLabel('Input channels'), 1, 2); setup.addWidget(self.channels_spin, 1, 3)
        setup.addWidget(refresh, 2, 2); setup.addWidget(apply_audio, 2, 3)
        main.addLayout(setup)

        meta = QGridLayout()
        self.roll_edit = QLineEdit('A001')
        self.scene_edit = QLineEdit('1')
        self.take_spin = QSpinBox(); self.take_spin.setRange(1, 9999); self.take_spin.setValue(1)
        self.track_edits = [QLineEdit(x) for x in ('Boom', 'Lav A', 'Lav B', 'Plant')]
        meta.addWidget(QLabel('Roll'), 0, 0); meta.addWidget(self.roll_edit, 0, 1)
        meta.addWidget(QLabel('Scene'), 0, 2); meta.addWidget(self.scene_edit, 0, 3)
        meta.addWidget(QLabel('Take'), 0, 4); meta.addWidget(self.take_spin, 0, 5)
        for i, edit in enumerate(self.track_edits):
            meta.addWidget(QLabel(f'Ch {i+1}'), 1 + i // 2, (i % 2) * 3)
            meta.addWidget(edit, 1 + i // 2, (i % 2) * 3 + 1, 1, 2)
        main.addLayout(meta)

        self.meter_layout = QGridLayout()
        self.meters = []
        self.meter_labels = []
        for i in range(4):
            name = QLabel(f'{i+1}  {self.track_edits[i].text()}')
            meter = QProgressBar(); meter.setRange(-60, 0); meter.setValue(-60); meter.setFormat('%v dBFS')
            meter.setMinimumHeight(34)
            self.meter_layout.addWidget(name, i, 0)
            self.meter_layout.addWidget(meter, i, 1)
            self.meters.append(meter); self.meter_labels.append(name)
        main.addLayout(self.meter_layout)

        self.clock = QLabel('00:00:00.000')
        self.clock.setAlignment(Qt.AlignCenter)
        self.clock.setStyleSheet('font-size: 42px; font-family: monospace; font-weight: 700;')
        main.addWidget(self.clock)

        transport = QHBoxLayout()
        self.record_btn = QPushButton('● RECORD'); self.record_btn.clicked.connect(self.toggle_record)
        self.stop_btn = QPushButton('■ STOP'); self.stop_btn.clicked.connect(self.stop_all)
        self.play_btn = QPushButton('▶ PLAY LAST'); self.play_btn.clicked.connect(self.play_last)
        self.next_btn = QPushButton('NEXT TAKE'); self.next_btn.clicked.connect(self.next_take)
        self.circle_btn = QPushButton('★ CIRCLE'); self.circle_btn.setCheckable(True); self.circle_btn.clicked.connect(self.set_circle)
        for button in (self.record_btn, self.stop_btn, self.play_btn, self.next_btn, self.circle_btn):
            button.setMinimumHeight(55); transport.addWidget(button)
        main.addLayout(transport)

        self.notes = QTextEdit(); self.notes.setPlaceholderText('Take notes...')
        self.notes.setMaximumHeight(100)
        main.addWidget(self.notes)

        self.status_label = QLabel('Audio not started')
        self.remote_label = QLabel('Remote: starting...')
        main.addWidget(self.status_label)
        main.addWidget(self.remote_label)

        self.setStyleSheet('''
            QMainWindow, QWidget { background:#151515; color:#f0f0f0; font-size:14px; }
            QLineEdit, QComboBox, QSpinBox, QTextEdit { background:#252525; border:1px solid #555; padding:6px; }
            QPushButton { background:#303030; border:1px solid #666; border-radius:5px; padding:8px; }
            QPushButton:checked { background:#8a5b00; }
            QProgressBar { background:#242424; border:1px solid #555; text-align:center; }
            QProgressBar::chunk { background:#dadada; }
        ''')

    def _load_devices(self):
        self.input_combo.clear(); self.output_combo.clear()
        try:
            hostapis = AudioEngine.hostapis()
            for d in AudioEngine.devices():
                host = hostapis[d.hostapi]['name'] if d.hostapi < len(hostapis) else 'Host'
                label = f'{d.index}: {d.name} [{host}]'
                if d.max_input_channels:
                    self.input_combo.addItem(label, d.index)
                    if 'UMC404' in d.name.upper():
                        self.input_combo.setCurrentIndex(self.input_combo.count() - 1)
                if d.max_output_channels:
                    self.output_combo.addItem(label, d.index)
                    if 'UMC404' in d.name.upper():
                        self.output_combo.setCurrentIndex(self.output_combo.count() - 1)
        except Exception as exc:
            QMessageBox.critical(self, 'Audio device error', str(exc))

    def choose_project(self):
        folder = QFileDialog.getExistingDirectory(self, 'Choose project folder', str(self.project_dir))
        if folder:
            self.project_dir = Path(folder)
            self.project_label.setText(str(self.project_dir))

    def apply_audio(self):
        try:
            self.audio.stop_monitoring()
            idx = int(self.input_combo.currentData())
            self.audio.configure(idx, channels=self.channels_spin.value(), sample_rate=int(self.sample_combo.currentText()))
            self.audio.start_monitoring()
            self._ensure_meter_count(self.audio.channels)
            self.status_label.setText(f'Monitoring {self.audio.channels}ch @ {self.audio.sample_rate} Hz')
        except Exception as exc:
            QMessageBox.critical(self, 'Could not start audio', str(exc))

    def _ensure_meter_count(self, channels: int):
        while len(self.meters) < channels:
            i = len(self.meters)
            name = QLabel(f'{i+1}  Input {i+1}')
            meter = QProgressBar(); meter.setRange(-60, 0); meter.setValue(-60); meter.setFormat('%v dBFS')
            self.meter_layout.addWidget(name, i, 0); self.meter_layout.addWidget(meter, i, 1)
            self.meter_labels.append(name); self.meters.append(meter)
        for i, meter in enumerate(self.meters):
            meter.setVisible(i < channels); self.meter_labels[i].setVisible(i < channels)

    def _filename(self):
        roll = self.roll_edit.text().strip() or 'ROLL'
        scene = self.scene_edit.text().strip() or 'SCENE'
        take = self.take_spin.value()
        safe = lambda s: ''.join(c if c.isalnum() or c in '-_' else '_' for c in s)
        return f'{safe(roll)}_{safe(scene)}_T{take:03d}.wav'

    def toggle_record(self):
        if self.audio.recording:
            self.finish_take()
            return
        try:
            if self.audio.stream is None:
                self.apply_audio()
                if self.audio.stream is None:
                    return
            self.circle_take = False; self.circle_btn.setChecked(False)
            take_dir = self.project_dir / self.roll_edit.text().strip()
            path = take_dir / self._filename()
            if path.exists():
                answer = QMessageBox.question(self, 'Overwrite?', f'{path.name} exists. Overwrite it?')
                if answer != QMessageBox.Yes:
                    return
            self.audio.start_recording(path)
            self.last_take_path = path
            self.status_label.setText(f'RECORDING  {path.name}')
            self.record_btn.setText('● RECORDING')
            self.record_btn.setStyleSheet('background:#8b0000; font-weight:700;')
        except Exception as exc:
            QMessageBox.critical(self, 'Record error', str(exc))

    def finish_take(self):
        if not self.audio.recording:
            return
        self.audio.stop_recording()
        self._write_take_metadata()
        self.record_btn.setText('● RECORD'); self.record_btn.setStyleSheet('')
        self.status_label.setText(f'Saved: {self.last_take_path.name if self.last_take_path else "take"}')

    def _write_take_metadata(self):
        if not self.last_take_path:
            return
        info = {
            'file': self.last_take_path.name,
            'roll': self.roll_edit.text(),
            'scene': self.scene_edit.text(),
            'take': self.take_spin.value(),
            'circle': self.circle_take,
            'notes': self.notes.toPlainText(),
            'sample_rate': self.audio.sample_rate,
            'channels': self.audio.channels,
            'track_names': [e.text() for e in self.track_edits[:self.audio.channels]],
            'recorded_at': datetime.now().isoformat(timespec='seconds'),
            'xruns': self.audio.xrun_count,
        }
        self.last_take_path.with_suffix('.json').write_text(json.dumps(info, indent=2), encoding='utf-8')

    def stop_all(self):
        if self.audio.recording:
            self.finish_take()
        self.audio.stop_playback()

    def play_last(self):
        if self.audio.recording:
            return
        if not self.last_take_path or not self.last_take_path.exists():
            self.status_label.setText('No recorded take to play.')
            return
        try:
            output = self.output_combo.currentData()
            self.audio.play_file(self.last_take_path, int(output) if output is not None else None)
            self.status_label.setText(f'Playing {self.last_take_path.name}')
        except Exception as exc:
            QMessageBox.critical(self, 'Playback error', str(exc))

    def next_take(self):
        if self.audio.recording:
            return
        self.take_spin.setValue(self.take_spin.value() + 1)
        self.notes.clear(); self.circle_btn.setChecked(False); self.circle_take = False

    def set_circle(self, checked):
        self.circle_take = bool(checked)
        if self.last_take_path and not self.audio.recording:
            self._write_take_metadata()

    def _meter_from_audio_thread(self, values):
        try:
            while self.meter_queue.qsize() > 2:
                self.meter_queue.get_nowait()
            self.meter_queue.put_nowait(values)
        except queue.Full:
            pass

    def _tick(self):
        try:
            values = self.meter_queue.get_nowait()
            for i, db in enumerate(values[:len(self.meters)]):
                self.meters[i].setValue(max(-60, min(0, int(round(db)))))
                if i < len(self.track_edits):
                    self.meter_labels[i].setText(f'{i+1}  {self.track_edits[i].text()}')
        except queue.Empty:
            pass

        sec = self.audio.elapsed_seconds if self.audio.recording else 0
        ms = int((sec - int(sec)) * 1000)
        s = int(sec) % 60; m = (int(sec) // 60) % 60; h = int(sec) // 3600
        self.clock.setText(f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}')

        for _ in range(10):
            try:
                cmd = self.remote_commands.get_nowait()
            except queue.Empty:
                break
            self._handle_remote(cmd)

    def _handle_remote(self, payload: dict):
        cmd = str(payload.get('command', '')).lower()
        if cmd == 'record' and not self.audio.recording:
            self.toggle_record()
        elif cmd == 'stop':
            self.stop_all()
        elif cmd == 'play':
            self.play_last()
        elif cmd == 'next_take':
            self.next_take()
        elif cmd == 'circle':
            self.circle_btn.setChecked(not self.circle_btn.isChecked())
            self.set_circle(self.circle_btn.isChecked())
        elif cmd == 'set_scene' and 'scene' in payload and not self.audio.recording:
            self.scene_edit.setText(str(payload['scene']))
        elif cmd == 'set_take' and 'take' in payload and not self.audio.recording:
            self.take_spin.setValue(int(payload['take']))

    def remote_state(self):
        return {
            'recording': self.audio.recording,
            'elapsed': round(self.audio.elapsed_seconds, 2),
            'roll': self.roll_edit.text(),
            'scene': self.scene_edit.text(),
            'take': self.take_spin.value(),
            'circle': self.circle_take,
            'last_file': self.last_take_path.name if self.last_take_path else '',
            'xruns': self.audio.xrun_count,
        }

    def closeEvent(self, event):
        try:
            self.audio.stop_monitoring()
            self.controller_server.stop()
        finally:
            event.accept()


def run():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
