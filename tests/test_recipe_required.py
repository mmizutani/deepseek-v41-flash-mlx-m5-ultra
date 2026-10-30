import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac import config


class RecipeRequiredTest(unittest.TestCase):
    def test_missing_recipe_fails_instead_of_using_empty_paths(self):
        with tempfile.TemporaryDirectory() as root, patch('mac.config.ROOT', Path(root)):
            with self.assertRaisesRegex(SystemExit, 'required recipe missing'):
                config.load(env={})

    def test_removed_recipe_key_does_not_change_thinking_silently(self):
        original = (config.ROOT / 'recipe.toml').read_text()
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            (path / 'recipe.toml').write_text(original.replace('thinking = true', '# thinking = true'))
            with patch('mac.config.ROOT', path), self.assertRaisesRegex(SystemExit, 'missing defaults: thinking'):
                config.load(env={})
