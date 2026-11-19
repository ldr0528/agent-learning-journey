"""课程入口的文件兼容、免费澄清和案例快照一致性。"""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from examples.insurance_compare import main as compare
from examples.insurance_consultation import main as consult


class InsuranceExampleTests(unittest.TestCase):
    def test_confirmation_does_not_rewrite_intake_snapshot(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "consultation.json"
            with patch.object(sys, "argv", ["consultation", "--output", str(output)]), redirect_stdout(io.StringIO()):
                self.assertEqual(consult(), 0)
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["intake"]["proposal"]["request"]["selections"], [])
        self.assertEqual(len(result["confirmed_request"]["selections"]), 2)
        self.assertEqual(result["report"]["request"], result["confirmed_request"])

    def test_bom_request_and_live_clarification_do_not_require_credentials(self):
        with TemporaryDirectory() as directory:
            request, output = Path(directory) / "request.json", Path(directory) / "result.json"
            request.write_text("{}", encoding="utf-8-sig")
            with patch("examples.insurance_compare.load_settings") as settings, redirect_stdout(io.StringIO()):
                code = compare(["--request", str(request), "--live", "--output", str(output)])
            self.assertEqual(code, 0)
            settings.assert_not_called()
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "needs_input")
        self.assertEqual(report["mode"], "live")
        self.assertEqual(report["model_calls"], 0)

    def test_invalid_request_reports_error_without_traceback(self):
        with TemporaryDirectory() as directory:
            request = Path(directory) / "request.json"
            request.write_text("{", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(compare(["--request", str(request)]), 1)
        self.assertIn("无法完成比较", output.getvalue())


if __name__ == "__main__":
    unittest.main()
