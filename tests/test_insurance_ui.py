"""浏览器状态逻辑回归使用 Node 内置模块；应用运行本身不需要 Node。"""

from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "前端状态回归需要可选 Node.js")
class InsuranceUIStateTests(unittest.TestCase):
    def test_retry_drafts_and_report_transitions(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([shutil.which("node"), "tests/ui/insurance-state-checks.cjs"],
                                cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
