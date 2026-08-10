from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image


class BrandAssetTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_primary_icon_contains_visible_blue_waveform(self):
        image = Image.open(self.root / "assets" / "icon.png").convert("RGBA")
        self.assertEqual(image.size, (1024, 1024))
        opaque = 0
        bright_blue = 0
        for r, g, b, a in image.getdata():
            if a <= 0:
                continue
            opaque += 1
            if b >= 180 and g >= 100 and b > r * 1.2:
                bright_blue += 1
        self.assertGreater(opaque, 0)
        self.assertGreater(bright_blue / opaque, 0.03, "Icon waveform is missing or too dark")

    def test_windows_icon_contains_multiple_sizes(self):
        image = Image.open(self.root / "assets" / "icon.ico")
        sizes = set(image.info.get("sizes", []))
        self.assertIn((16, 16), sizes)
        self.assertIn((32, 32), sizes)
        self.assertIn((256, 256), sizes)

    def test_remote_icon_uses_same_waveform_identity(self):
        svg = (self.root / "web" / "remote-icon.svg").read_text(encoding="utf-8")
        self.assertIn("#61C6FF", svg)
        self.assertGreaterEqual(svg.count("<path"), 9)


if __name__ == "__main__":
    unittest.main()

class UIIconSetTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_core_desktop_icons_exist_and_have_transparency(self):
        required = {
            'record','takes','notes','remote','system','help','audio','disk','idle',
            'slate','tracks','input','stop','play','next','circle','refresh','qr',
            'browser','report','diagnostics','reveal','reset'
        }
        icon_dir = self.root / 'assets' / 'icons'
        missing = sorted(name for name in required if not (icon_dir / f'{name}.png').exists())
        self.assertEqual(missing, [])
        for name in required:
            image = Image.open(icon_dir / f'{name}.png').convert('RGBA')
            self.assertEqual(image.size, (96, 96))
            alphas = [px[3] for px in image.getdata()]
            self.assertGreater(max(alphas), 0, name)
            self.assertIn(0, alphas, f'{name} should have transparent background')
