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
        self.assertIn('self.input_combo = QComboBox()', self.source)
        self.assertIn('self.system_input_combo = QComboBox()', self.source)
        self.assertIn('("INPUT DEVICE",self.system_input_combo)', self.source)
        self.assertIn('def _sync_input_device', self.source)

    def test_real_ui_icons_are_referenced(self):
        for name in ('record','takes','notes','remote','system','slate','tracks','stop','play','next','circle'):
            self.assertIn(f'"{name}"', self.source)
