import tempfile
import unittest
from pathlib import Path

from mac import config


class ConfigErrorsTest(unittest.TestCase):
    def test_typos_and_unknown_sections_are_actionable(self):
        for source, message in (('[serve]\ncontexts=123', 'unknown settings: contexts'),
                                ('[serrve]\ncontext=123', 'invalid section')):
            with tempfile.TemporaryDirectory() as root:
                path = Path(root) / 'local.toml'
                path.write_text(source)
                with self.assertRaisesRegex(SystemExit, message):
                    config.load(path, env={})

    def test_invalid_boolean_is_not_silently_false(self):
        with self.assertRaisesRegex(SystemExit, 'invalid setting thinking'):
            config.load(Path('/nonexistent'), env={'THINKING': 'treu'})
        self.assertFalse(config.load(Path('/nonexistent'), env={'THINKING': 'off', 'UNRELATED': 'ok'}).thinking)
