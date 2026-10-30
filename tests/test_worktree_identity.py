import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from mac import engine
from mac.config import Settings


class WorktreeIdentityTest(unittest.TestCase):
    def test_mismatched_or_dirty_tree_is_rejected_even_with_cached_binary(self):
        for head, dirty in (('wrong', ''), ('pinned', ' M zig/src/main.zig')):
            with self.subTest(head=head, dirty=dirty), tempfile.TemporaryDirectory() as root:
                s = Settings(tf_cache=root, tensorfold_sha='pinned')
                s.built_binary.parent.mkdir(parents=True)
                s.built_binary.touch()
                with patch('mac.engine.subprocess.run', side_effect=[Mock(stdout=head), Mock(stdout=dirty)]), \
                     patch('mac.engine._run') as build, self.assertRaises(SystemExit):
                    engine.build_engine(s)
                build.assert_not_called()

    def test_clean_cached_tree_does_not_need_zig(self):
        with tempfile.TemporaryDirectory() as root:
            s = Settings(tf_cache=root, tensorfold_sha='pinned')
            s.built_binary.parent.mkdir(parents=True)
            s.built_binary.touch()
            with patch('mac.engine.subprocess.run', side_effect=[Mock(stdout='pinned'), Mock(stdout='')]), \
                 patch('mac.engine.zig_executable') as zig:
                self.assertEqual(engine.build_engine(s), s.built_binary)
                zig.assert_not_called()
