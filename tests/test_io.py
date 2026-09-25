from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.io import write_json


class JsonIoTests(unittest.TestCase):
    def test_write_json_atomically_replaces_complete_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            path.write_text('{"old": true}\n')

            write_json(path, {"new": True})

            self.assertEqual(json.loads(path.read_text()), {"new": True})
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

    def test_failed_write_preserves_previous_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            original = '{"old": true}\n'
            path.write_text(original)

            def fail_after_partial_write(_value, handle, **_kwargs):
                handle.write("{")
                raise RuntimeError("synthetic interrupted write")

            with patch(
                "caa_scheduler.io.json.dump",
                side_effect=fail_after_partial_write,
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    write_json(path, {"new": True})

            self.assertEqual(path.read_text(), original)
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
