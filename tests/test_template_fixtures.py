import hashlib
import json
import unittest
from pathlib import Path


class TemplateFixturesTest(unittest.TestCase):
    def test_all_pinned_fixture_bytes_are_present(self):
        root = Path(__file__).resolve().parents[1] / 'template/fixtures'
        manifest = json.loads((root / 'sha256.json').read_text())
        self.assertEqual(len(manifest), 10)
        for name, digest in manifest.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest)
