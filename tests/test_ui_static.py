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
