import json
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from mac import serve
from mac.config import Settings


class IdentityTest(unittest.TestCase):
    def test_invalid_pid_never_reaches_ps(self):
        with patch('mac.serve.subprocess.run') as run:
            for value in (0, -1, None, True, '123'):
                self.assertIsNone(serve.identity(value))
            run.assert_not_called()

    def test_reused_pid_and_legacy_file_are_not_signalled(self):
        with tempfile.TemporaryDirectory() as root:
            s = Settings(tf_cache=root, binary='/engine/tensorfold-native')
            old = {'pid': 123, 'started': 'old', 'executable': str(s.run_binary)}
            for contents in ('123', json.dumps(old)):
                s.pid_file.write_text(contents)
                with patch('mac.serve.identity', return_value={**old, 'started': 'new'}), \
                     patch('mac.serve.os.kill') as kill:
                    self.assertIsNone(serve.pid(s))
                    serve.down(s, grace=0)
                    kill.assert_not_called()

    def test_rechecks_identity_before_sigkill(self):
        with tempfile.TemporaryDirectory() as root:
            s = Settings(tf_cache=root, binary='/engine/tensorfold-native')
            old = {'pid': 123, 'started': 'old', 'executable': str(s.run_binary)}
            s.pid_file.write_text(json.dumps(old))
            with patch('mac.serve.identity', side_effect=[old, {**old, 'started': 'new'}]), \
                 patch('mac.serve.os.kill') as kill:
                serve.down(s, grace=0)
                kill.assert_called_once_with(123, signal.SIGTERM)
            self.assertFalse(s.pid_file.exists())

    def test_failed_start_clears_dead_child_but_keeps_live_timeout(self):
        for dead in (False, True):
            with self.subTest(dead=dead), tempfile.TemporaryDirectory() as root:
                s = Settings(tf_cache=root, binary='/engine/tensorfold-native')
                child = Mock(pid=123)
                child.poll.return_value = 1 if dead else None
                saved = {'pid': 123, 'started': 'now', 'executable': str(s.run_binary)}
                with patch('mac.serve.pid', return_value=None), patch('mac.serve.health', return_value=None), \
                     patch('mac.serve.memory_check'), patch('mac.serve.subprocess.Popen', return_value=child), \
                     patch('mac.serve.identity', return_value=saved), \
                     patch('mac.serve.wait_ready', side_effect=SystemExit('failed')):
                    with self.assertRaises(SystemExit):
                        serve.up(s)
                self.assertEqual(s.pid_file.exists(), not dead)
