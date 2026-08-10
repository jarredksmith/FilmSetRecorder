from __future__ import annotations

import ast
import unittest
from pathlib import Path


class UIStaticTests(unittest.TestCase):
    def test_qt_symbols_used_by_main_window_are_imported_or_defined(self):
        path = Path(__file__).resolve().parents[1] / "filmrecorder" / "main_window.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        qt_loads = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and (node.id == "Qt" or (node.id.startswith("Q") and len(node.id) > 1 and node.id[1].isupper()))
        }

        imported = set()
        defined = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported.update(alias.asname or alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                imported.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(node.name)

        missing = sorted(qt_loads - imported - defined)
        self.assertEqual(missing, [], f"Qt symbols are used but not imported/defined: {missing}")


if __name__ == "__main__":
    unittest.main()

class RecorderRoutingStaticTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.source = (self.root / 'filmrecorder' / 'main_window.py').read_text(encoding='utf-8')

    def test_input_device_is_exposed_in_record_and_system_workspaces(self):
        self.assertIn('self.input_combo = DeviceComboBox()', self.source)
        self.assertIn('self.system_input_combo = DeviceComboBox()', self.source)
        self.assertIn('("INPUT DEVICE", self.system_input_combo)', self.source)
        self.assertIn('def _sync_input_device', self.source)

    def test_real_ui_icons_are_referenced(self):
        for name in ('record','takes','notes','remote','system','slate','tracks','stop','play','next','circle'):
            self.assertIn(f'"{name}"', self.source)

class UIIconAndArmStaticTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.main = (self.root / 'filmrecorder' / 'main_window.py').read_text(encoding='utf-8')
        self.widgets = (self.root / 'filmrecorder' / 'widgets.py').read_text(encoding='utf-8')
        self.icons = (self.root / 'filmrecorder' / 'ui_icons.py').read_text(encoding='utf-8')

    def test_ui_icons_are_runtime_vector_icons_not_file_dependent(self):
        self.assertIn('return make_icon(name, 64)', self.main)
        self.assertIn('def icon_pixmap', self.icons)
        self.assertIn('def brand_icon', self.icons)
        self.assertNotIn('assets") / "icons"', self.main)

    def test_input_device_selectors_have_visible_chevrons(self):
        self.assertIn('self.input_combo = DeviceComboBox()', self.main)
        self.assertIn('self.system_input_combo = DeviceComboBox()', self.main)
        self.assertIn('class DeviceComboBox', self.widgets)
        self.assertIn('Click to choose an audio device', self.widgets)

    def test_record_enable_state_is_unambiguous(self):
        self.assertIn('self.arm_button.setText("REC" if armed else "OFF")', self.widgets)
        self.assertIn('Record-enable this input', self.widgets)
        self.assertIn('QPushButton#ArmButton:checked', (self.root / 'filmrecorder' / 'theme.py').read_text(encoding='utf-8'))


class MockupParityStaticTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.main = (self.root / "filmrecorder" / "main_window.py").read_text(encoding="utf-8")
        self.widgets = (self.root / "filmrecorder" / "widgets.py").read_text(encoding="utf-8")
        self.theme = (self.root / "filmrecorder" / "theme.py").read_text(encoding="utf-8")

    def test_dynamic_add_input_control_tracks_hardware_capacity(self):
        self.assertIn('self.add_input_btn = QPushButton("ADD INPUT")', self.main)
        self.assertIn('def _add_input_track', self.main)
        self.assertIn('_selected_device_max_inputs', self.main)
        self.assertIn('self.channels_spin.setValue(current + 1)', self.main)

    def test_mockup_transport_and_production_strip_are_present(self):
        self.assertIn('TransportControl("RECORD"', self.main)
        self.assertIn('TransportControl("CIRCLE"', self.main)
        self.assertIn('production_strip.setObjectName("ProductionStrip")', self.main)
        self.assertIn('self.history_rows', self.main)
        self.assertIn('self.quick_notes = QTextEdit()', self.main)
        self.assertIn('QPushButton#TransportCircle', self.theme)

    def test_meter_supports_peak_and_rms(self):
        self.assertIn('self._rms_db', self.widgets)
        self.assertIn('RMS', self.widgets)
        self.assertIn('rms_values', self.main)
