"""启动测试治理视图的本地静态服务器并打开浏览器。

用法：python view.py [项目根目录] [端口]
目录默认为当前目录，端口默认 8765，被占用时自动改用系统分配的端口。

TEST-GOVERNANCE.html 通过 fetch 读取同目录的 BEHAVIORS.md 与
TEST-DISPOSITION.md，而浏览器的 file:// 限制禁止这类跨文件读取，
因此必须经由 HTTP 访问，本脚本只负责这件事。
"""

import http.server
import os
import sys
import webbrowser
from functools import partial


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    handler = partial(QuietHandler, directory=root)
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/TEST-GOVERNANCE.html"
    print(url, flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
