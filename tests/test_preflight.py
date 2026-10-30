import json
import tempfile
import unittest
from pathlib import Path

from mac import config


class PreflightTest(unittest.TestCase):
    def checkpoint(self, root):
        root = Path(root)
        (root / 'engram').mkdir()
        (root / 'engram/hash.safetensors').touch()
        (root / 'engram/part0').touch()
        (root / 'tokenizer.json').write_text('{}')
        (root / 'model-head.safetensors').touch()
        (root / 'model.safetensors.index.json').write_text(json.dumps({'weight_map': {'head.weight': 'model-head.safetensors'}}))
        (root / 'config.json').write_text(json.dumps({'max_position_embeddings': 1048576,
                                                     'engram_files': {'2': ['engram/part0']}}))
        s = config.load(Path('/nonexistent'), env={})
        s.model_dir = str(root)
        s.tf_cache = str(root / 'cache')
        s.tensorfold_src = str(root / 'source')
        (root / 'source/.git').mkdir(parents=True)
        return s

    def test_first_build_and_negative_cache_sentinel_are_allowed(self):
        with tempfile.TemporaryDirectory() as root:
            s = self.checkpoint(root)
            s.prompt_cache_gib = -1
            self.assertFalse(s.built_binary.exists())
            self.assertEqual(config.validate(s), [])

    def test_missing_split_part_and_model_context_limit(self):
        with tempfile.TemporaryDirectory() as root:
            s = self.checkpoint(root)
            (Path(root) / 'engram/part0').unlink()
            s.context = 1048577
            errors = config.validate(s)
            self.assertTrue(any('missing Engram table' in e for e in errors))
            self.assertTrue(any('checkpoint maximum' in e for e in errors))

    def test_invalid_explicit_binary_and_numeric_settings(self):
        with tempfile.TemporaryDirectory() as root:
            s = self.checkpoint(root)
            s.binary = '/missing/engine'
            s.port = 65536
            s.thinking_reserve = -1
            errors = config.validate(s)
            for fragment in ('binary is not executable', 'port must', 'thinking_reserve'):
                self.assertTrue(any(fragment in e for e in errors))

    def test_missing_shard_and_tokenizer_are_reported(self):
        with tempfile.TemporaryDirectory() as root:
            s = self.checkpoint(root)
            (Path(root) / 'tokenizer.json').unlink()
            (Path(root) / 'model-head.safetensors').unlink()
            errors = config.validate(s)
            self.assertTrue(any('missing weight shard' in e for e in errors))
            self.assertTrue(any('missing tokenizer' in e for e in errors))
