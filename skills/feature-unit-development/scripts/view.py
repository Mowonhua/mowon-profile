"""文件职责：提供功能视图的本地只读服务。

定义范围：功能快照、已登记提交查询和 HTTP 入口。
页面复用 featurectl 的解析结果；服务不写文档、不运行测试、不搜索提交历史。
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
import webbrowser

from featurectl import coverage, scan, to_index


def snapshot(project: Path) -> dict:
    """函数职责：读取当前功能文档，返回页面所需的只读快照。

    输入说明：project 是目标项目的绝对路径。
    输出说明：返回功能、关联统计和解析问题；不把静态关联当作测试结果。
    实现思路：复用 scan、to_index 和 coverage，不另建 Markdown 解析器。
    """
    features, issues = scan(project)
    return {"project": project.name, **to_index(features), "coverage": coverage(features),
            "issues": [issue.as_json() for issue in issues]}


def read_commit(project: Path, commit: str) -> dict:
    """函数职责：查询功能文档已登记的一个创建提交。

    输入说明：commit 只能是 7 到 40 位十六进制 hash。
    输出说明：返回 hash、时间和提交说明；查询失败返回错误，不推断来源。
    实现思路：先验证格式，再限时调用 git show；不调用 git log。
    """
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit):
        return {"error": "创建提交格式无效"}
    try:
        result = subprocess.run(
            ["git", "show", "-s", "--no-notes", "--format=%H%x00%aI%x00%B", f"{commit}^{{commit}}", "--"],
            cwd=project, capture_output=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"error": "无法读取创建提交"}
    if result.returncode:
        return {"error": "当前仓库中未找到创建提交"}
    fields = result.stdout.decode("utf-8", "replace").strip().split("\0", 2)
    if len(fields) != 3:
        return {"error": "提交信息格式无效"}
    return dict(zip(("hash", "time", "message"), fields))


class FeatureHandler(BaseHTTPRequestHandler):
    """接口职责：向本机浏览器提供功能页面和两个只读查询接口。

    调用方：ThreadingHTTPServer。
    实现要求：仅提供固定页面和 JSON 接口，不开放项目目录浏览。
    """

    def __init__(self, *args, project: Path, **kwargs):
        self.project = project
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """函数职责：分派页面、功能快照及已登记提交的 GET 请求。

        输入说明：请求路径来自浏览器；项目目录在启动时固定。
        输出说明：返回 HTML 或 JSON；未知路径返回 404。
        实现思路：使用固定路由；提交查询先确认 hash 出现在当前功能文档中。
        """
        path = urlsplit(self.path).path
        try:
            if path == "/":
                page = Path(__file__).resolve().parent.parent / "assets" / "FEATURES.html"
                body = page.read_bytes()
                status, content_type = 200, "text/html; charset=utf-8"
            elif path == "/api/features":
                body = json.dumps(snapshot(self.project), ensure_ascii=False).encode("utf-8")
                status, content_type = 200, "application/json; charset=utf-8"
            elif path.startswith("/api/commit/"):
                commit = path.removeprefix("/api/commit/")
                features, _ = scan(self.project)
                # 仅查询文档明确登记的提交，避免把查看器变成任意 Git 查询接口。
                if not commit or commit not in {f.created_commit for f in features}:
                    self.send_error(404)
                    return
                result = read_commit(self.project, commit)
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                status = 404 if "error" in result else 200
                content_type = "application/json; charset=utf-8"
            else:
                self.send_error(404)
                return
        except (OSError, UnicodeError):
            body = json.dumps({"error": "无法读取功能文档或页面"}, ensure_ascii=False).encode("utf-8")
            status, content_type = 500, "application/json; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        # 页面定期刷新；正常请求不写访问日志，启动地址由 main 输出。
        pass


def main(argv=None) -> int:
    """函数职责：启动绑定本机回环地址的功能视图服务。

    输入说明：接收项目目录、端口和 --no-open；默认项目为当前目录。
    输出说明：打印实际访问地址；端口占用时改用系统分配端口。
    实现思路：先创建服务器，再打开浏览器；退出时关闭监听端口。
    """
    parser = argparse.ArgumentParser(description="查看当前功能、场景、关系和测试引用")
    parser.add_argument("project", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)
    project = args.project.resolve()
    if not project.is_dir():
        parser.error("项目目录不存在")
    if not 0 <= args.port <= 65535:
        parser.error("端口应为 0 到 65535；0 表示系统分配")
    handler = partial(FeatureHandler, project=project)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(url, flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
