import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac import engine


class JPEGDownloadTest(unittest.TestCase):
    def test_verified_download_is_cached_then_reused(self):
        payload = b'test release archive'
        with tempfile.TemporaryDirectory() as root, \
             patch('mac.engine.JPEG_SHA256', hashlib.sha256(payload).hexdigest()), \
             patch('mac.engine.urllib.request.urlopen', return_value=io.BytesIO(payload)) as fetch:
            path = engine.jpeg_archive(Path(root))
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(engine.jpeg_archive(Path(root)), path)
            fetch.assert_called_once()
            self.assertEqual(fetch.call_args.kwargs['timeout'], 60)

    def test_bad_download_never_reaches_the_cache(self):
        with tempfile.TemporaryDirectory() as root, \
             patch('mac.engine.urllib.request.urlopen', return_value=io.BytesIO(b'wrong')):
            with self.assertRaisesRegex(SystemExit, 'SHA-256 mismatch'):
                engine.jpeg_archive(Path(root))
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_interrupted_download_does_not_poison_retries(self):
        with tempfile.TemporaryDirectory() as root, \
             patch('mac.engine.urllib.request.urlopen', side_effect=TimeoutError('interrupted')):
            with self.assertRaises(TimeoutError):
                engine.jpeg_archive(Path(root))
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_corrupt_cached_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / f'libjpeg-turbo-{engine.JPEG_VERSION}.tar.gz'
            path.write_bytes(b'partial')
            with self.assertRaisesRegex(SystemExit, 'cached.*remove this archive'):
                engine.jpeg_archive(Path(root))
