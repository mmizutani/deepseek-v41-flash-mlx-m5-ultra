import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac import config, pi
from mac.__main__ import main


class PiTest(unittest.TestCase):
    def settings(self, **overrides):
        s = config.load(Path('/nonexistent'), env={})
        for name, value in overrides.items():
            setattr(s, name, value)
        return s

    def test_cli_creates_usable_default_without_server_or_pi(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / 'agent'
            with patch('mac.__main__.config.load', return_value=self.settings()), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['pi-setup', '--agent-dir', str(directory)]), 0)
            provider = json.loads((directory / 'models.json').read_text())['providers']['local-deepseek']
            self.assertEqual(provider['baseUrl'], 'http://127.0.0.1:8890/v1')
            self.assertEqual(provider['apiKey'], 'local')
            self.assertEqual(provider['api'], 'openai-completions')
            model = provider['models'][0]
            self.assertEqual(model['id'], 'DeepSeek-V4.1-Flash')
            self.assertEqual(model['contextWindow'], 524288)
            self.assertEqual(model['maxTokens'], 32768)
            self.assertIn('image', model['input'])
            settings = json.loads((directory / 'settings.json').read_text())
            self.assertEqual(settings['defaultProvider'], 'local-deepseek')
            self.assertEqual(settings['defaultModel'], model['id'])

    def test_merge_backup_and_repeat_without_changes(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            models = {'providers': {'other': {'baseUrl': 'http://example.test'},
                                   'local-deepseek': {'models': [{'id': 'another-model'}]}}}
            settings = {'defaultProvider': 'other', 'defaultModel': 'old', 'theme': 'dark'}
            (directory / 'models.json').write_text(json.dumps(models))
            (directory / 'settings.json').write_text(json.dumps(settings))
            pi.setup(self.settings(), directory)
            updated = json.loads((directory / 'models.json').read_text())
            self.assertEqual(updated['providers']['other'], models['providers']['other'])
            self.assertIn({'id': 'another-model'}, updated['providers']['local-deepseek']['models'])
            self.assertEqual(json.loads((directory / 'settings.json').read_text())['theme'], 'dark')
            backups = list(directory.glob('backup-local-deepseek-*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(json.loads((backups[0] / 'models.json').read_text()), models)
            self.assertEqual(json.loads((backups[0] / 'settings.json').read_text()), settings)
            before = {p.name: p.stat().st_mtime_ns for p in directory.glob('*.json')}
            pi.setup(self.settings(), directory)
            self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in directory.glob('*.json')})
            self.assertEqual(list(directory.glob('backup-local-deepseek-*')), backups)
            pi.setup(self.settings(port=9100, vision=False, context=1048576), directory)
            provider = json.loads((directory / 'models.json').read_text())['providers']['local-deepseek']
            self.assertEqual(provider['baseUrl'], 'http://127.0.0.1:9100/v1')
            model = next(m for m in provider['models'] if m['id'] == 'DeepSeek-V4.1-Flash')
            self.assertEqual(model['input'], ['text'])
            self.assertNotIn('inputLimits', model)
            self.assertEqual(model['contextWindow'], 1048576)

    def test_no_default_preserves_settings_and_honors_agent_dir_env(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            original = '{"defaultModel": "keep-me"}\n'
            (directory / 'settings.json').write_text(original)
            with patch.dict(os.environ, {'PI_CODING_AGENT_DIR': root}):
                pi.setup(self.settings(), make_default=False)
            self.assertEqual((directory / 'settings.json').read_text(), original)
            self.assertTrue((directory / 'models.json').exists())

    def test_bad_existing_config_is_not_overwritten(self):
        for filename, content in [('models.json', '{'), ('models.json', '[]'),
                                  ('models.json', '{"providers": []}'),
                                  ('models.json', '{"providers":{"local-deepseek":{"models":{}}}}'),
                                  ('settings.json', '{')]:
            with self.subTest(filename=filename, content=content), tempfile.TemporaryDirectory() as root:
                directory = Path(root)
                path = directory / filename
                path.write_text(content)
                with self.assertRaisesRegex(ValueError, filename):
                    pi.setup(self.settings(), directory)
                self.assertEqual(path.read_text(), content)
                self.assertEqual(list(directory.iterdir()), [path])

    def test_auth_key_is_literal_and_config_is_private(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            pi.setup(self.settings(api_key='!secret-$KEY'), directory)
            path = directory / 'models.json'
            provider = json.loads(path.read_text())['providers']['local-deepseek']
            self.assertEqual(provider['apiKey'], '$!secret-$$KEY')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
