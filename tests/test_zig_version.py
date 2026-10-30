import subprocess
import unittest
from unittest.mock import Mock, patch

from mac import engine
from mac.config import Settings


class ZigVersionTest(unittest.TestCase):
    def test_wrong_or_development_version_fails_early(self):
        for value in ('0.16.0', '0.17.0-dev.123'):
            with patch('mac.engine.shutil.which', return_value='/bin/zig'), \
                 patch('mac.engine.subprocess.run', return_value=Mock(stdout=value)), \
                 self.assertRaisesRegex(SystemExit, 'Zig 0.17.0 required'):
                engine.zig_executable(Settings(zig='zig'))

    def test_unresponsive_version_probe_has_bounded_failure(self):
        with patch('mac.engine.shutil.which', return_value='/bin/zig'), \
             patch('mac.engine.subprocess.run', side_effect=subprocess.TimeoutExpired('zig', 10)), \
             self.assertRaisesRegex(SystemExit, 'cannot check Zig version'):
            engine.zig_executable(Settings(zig='zig'))
