"""通过临时项目验证功能页面的数据更新、提交查询和只读路由。"""
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from view import FeatureHandler, read_commit, snapshot


class TestView(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        (self.project / "features").mkdir()
        self.document = self.project / "features" / "orders.md"
        self.document.write_text("# 订单\n\n## F-ORDER-001 创建订单\n\n保存有效订单。\n", encoding="utf-8")

    def test_snapshot_reads_current_documents_without_writing_files(self):
        before = self.document.read_bytes()
        self.assertEqual("创建订单", snapshot(self.project)["features"][0]["name"])
        self.assertEqual(before, self.document.read_bytes())
        self.document.write_text(before.decode().replace("创建订单", "提交订单"), encoding="utf-8")
        self.assertEqual("提交订单", snapshot(self.project)["features"][0]["name"])
        self.document.unlink()
        self.assertEqual([], snapshot(self.project)["features"])

    def test_commit_lookup_uses_explicit_hash_in_target_repository(self):
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=self.project, stderr=subprocess.DEVNULL).decode().strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Feature Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
            "commit", "-qm", "feat: 创建订单")
        commit = git("rev-parse", "HEAD")
        result = read_commit(self.project, commit[:7])
        self.assertEqual(commit, result["hash"])
        self.assertEqual("feat: 创建订单", result["message"])
        self.assertIn("error", read_commit(self.project, "HEAD"))
        self.assertIn("error", read_commit(self.project, "0" * 40))

    def test_http_routes_serve_view_and_live_snapshot_only(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(FeatureHandler, project=self.project))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        def close():
            server.shutdown()
            server.server_close()
            worker.join()
        self.addCleanup(close)
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base) as response:
            self.assertIn("功能视图", response.read().decode())
        with urlopen(base + "/api/features") as response:
            self.assertEqual("F-ORDER-001", json.load(response)["features"][0]["id"])
            self.assertEqual("no-store", response.headers["Cache-Control"])
        for route in ("/features/orders.md", "/../AGENTS.md", "/api/commit/abcdef1"):
            with self.subTest(route=route), self.assertRaises(HTTPError) as error:
                urlopen(base + route)
            self.assertEqual(404, error.exception.code)


if __name__ == "__main__":
    unittest.main()
