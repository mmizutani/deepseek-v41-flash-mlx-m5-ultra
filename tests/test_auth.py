import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac import serve
from mac.__main__ import main
from mac.config import Settings


class AuthTest(unittest.TestCase):
    def test_key_is_in_private_file_not_arguments_or_cli_output(self):
        secret = 'test-private-key'
        s = Settings(api_key=secret, tf_cache='/tmp/cache with spaces')
        self.assertNotIn(secret, s.serve_args())
        self.assertNotIn('--api-key', s.serve_args())
        self.assertIn('--api-key-file', s.serve_args())
        for command in ('command', 'validate'):
            output = io.StringIO()
            with patch('mac.__main__.config.load', return_value=s), \
                 patch('mac.__main__.config.validate', return_value=[]), contextlib.redirect_stdout(output):
                self.assertEqual(main([command]), 0)
            self.assertNotIn(secret, output.getvalue())

    def test_chat_sends_the_configured_or_native_environment_key(self):
        for configured, native, expected in (('configured,with-comma', 'native', 'configured,with-comma'),
                                              ('', ' , native,second ', 'native'), ('', '', None)):
            s = Settings(api_key=configured)
            with patch.dict('os.environ', {'TENSORFOLD_API_KEY': native}), \
                 patch('mac.serve.urllib.request.urlopen', return_value=io.BytesIO(json.dumps(
                     {'choices': [{'message': {'content': 'ok'}}]}).encode())) as request:
                self.assertEqual(serve.chat(s, 'hello'), 'ok')
                header = request.call_args.args[0].get_header('Authorization')
                self.assertEqual(header, f'Bearer {expected}' if expected else None)

    def test_key_file_keeps_comma_and_colon_literal(self):
        with tempfile.TemporaryDirectory() as root:
            s = Settings(api_key='first,second:literal', tf_cache=root)
            serve.prepare_key(s)
            path = Path(root) / 'server-api-key'
            self.assertEqual(path.read_text(), 'wrapper:first,second:literal\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
