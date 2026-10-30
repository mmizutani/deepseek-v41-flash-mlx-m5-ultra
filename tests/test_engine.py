import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac import config, engine


class EngineTest(unittest.TestCase):
    @patch("mac.engine.verify_worktree")
    def test_default_zig_uses_path(self, _verify):
        s = config.load(Path("/nonexistent"), env={})
        self.assertEqual(s.zig, "zig")
        with tempfile.TemporaryDirectory() as root:
            s.tf_cache = root
            s.developer_dir = "/Applications/Xcode.app/Contents/Developer"
            s.worktree.mkdir(parents=True)
            with patch("mac.engine.shutil.which", return_value="/opt/bin/zig") as which, \
                 patch("mac.engine._run") as run:
                engine.build_engine(s)
            which.assert_called_once_with("zig")
            self.assertEqual(run.call_args.args[0][0], "/opt/bin/zig")
            self.assertEqual(run.call_args.kwargs["env"]["DEVELOPER_DIR"], s.developer_dir)

    @patch("mac.engine.verify_worktree")
    def test_missing_zig_has_actionable_error(self, _verify):
        with tempfile.TemporaryDirectory() as root:
            s = config.Settings(tf_cache=root, tensorfold_sha="abc", zig="/missing/zig")
            s.worktree.mkdir(parents=True)
            with patch("mac.engine.shutil.which", return_value=None), \
                 self.assertRaisesRegex(SystemExit, "Zig executable not found.*local.toml"):
                engine.build_engine(s)

    def test_explicit_zig_path_expands_home(self):
        s = config.Settings(zig="~/tools/zig")
        with patch("mac.engine.shutil.which", return_value="/custom/zig") as which:
            self.assertEqual(engine.zig_executable(s), "/custom/zig")
        which.assert_called_once_with(str(Path.home() / "tools/zig"))

    def test_prebuilt_binary_does_not_need_zig(self):
        s = config.Settings(binary="/custom/tensorfold-native")
        with patch("mac.engine.shutil.which") as which:
            self.assertEqual(engine.build_engine(s), Path(s.binary))
        which.assert_not_called()

    def test_build_env_preserves_developer_dir_from_environment(self):
        with patch.dict("os.environ", {"DEVELOPER_DIR": "/custom/Xcode"}):
            self.assertEqual(config.Settings().build_env()["DEVELOPER_DIR"], "/custom/Xcode")
