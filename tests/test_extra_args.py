import unittest

from mac.config import Settings


class ExtraArgsTest(unittest.TestCase):
    def test_quotes_escapes_and_empty_values(self):
        s = Settings(extra_args='--alias "a b" --label \'\' --path a\\ b')
        self.assertEqual(s.serve_args()[-7:-1], ['--alias', 'a b', '--label', '', '--path', 'a b'])

    def test_unmatched_quote_has_actionable_error(self):
        with self.assertRaisesRegex(SystemExit, "invalid extra_args.*EXTRA_ARGS"):
            Settings(extra_args='--alias "broken').serve_args()
