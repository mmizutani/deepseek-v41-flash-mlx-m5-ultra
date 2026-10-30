import unittest

from tools.checkpoint_config import engram_files


class CheckpointConfigTest(unittest.TestCase):
    def test_every_partial_conversion_preserves_split_tables(self):
        split = {"2": ["engram/layer2-part0.safetensors", "engram/layer2-part1.safetensors"]}
        for part in ("blocks", "head", "mtp", "vision", "hash"):
            with self.subTest(part=part):
                self.assertEqual(engram_files([2], {part}, {"engram_files": split}), split)

    def test_regenerated_tables_replace_old_references(self):
        self.assertEqual(engram_files([2], {"engram"}, {"engram_files": {"2": ["old"]}}),
                         {"2": "engram/layer2.safetensors"})

    def test_fresh_conversion_has_whole_table_references(self):
        self.assertEqual(engram_files([2], {"head"}, {}), {"2": "engram/layer2.safetensors"})
