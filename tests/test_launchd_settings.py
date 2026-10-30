import os
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac import launchd
from mac.config import Settings


class LaunchdSettingsTest(unittest.TestCase):
    def test_explicit_overrides_and_credentials_survive_login(self):
        s = Settings(api_key='private<&key', context=123456, zig='/custom/zig')
        with patch.dict(os.environ, {'CONTEXT': '123456', 'ZIG': '/custom/zig', 'UNRELATED_SECRET': 'ignore'}, clear=True):
            env = plistlib.loads(launchd.plist(s, 8888).encode())['EnvironmentVariables']
        self.assertEqual(env['API_KEY'], s.api_key)
        self.assertEqual(env['CONTEXT'], '123456')
        self.assertEqual(env['HOST'], '0.0.0.0')
        self.assertEqual(env['PORT'], '8888')
        self.assertIn('/opt/homebrew/bin', env['PATH'])
        self.assertNotIn('UNRELATED_SECRET', env)

    def test_fresh_install_creates_private_unit_and_log_directory(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            s = Settings(tf_cache=str(home / 'cache'))
            with patch('mac.launchd.Path.home', return_value=home), patch.dict(os.environ, {}, clear=True):
                message = launchd.write(s, 8888)
            path = home / 'Library/LaunchAgents' / f'{launchd.LABEL}.plist'
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(s.cache.is_dir())
            self.assertIn('without an API key', message)
