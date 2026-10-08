"""测试治理视图的本地服务器：提供静态文件服务并按 hash 读取提交信息。

用法：python <本脚本> [项目根目录] [端口] [--no-open] [--exit-busy]
目录默认为当前目录，端口默认 8765。--no-open 只启动服务器不打开浏览器；
--exit-busy 在端口被占用时直接退出（供 TEST-GOVERNANCE.bat 启动常驻实例，
避免重复启动第二个服务），缺省时被占用会自动改用系统分配的端口。

TEST-GOVERNANCE.html 通过 fetch 读取同目录的 BEHAVIORS.md 与
TEST-DISPOSITION.md，而浏览器的 file:// 限制禁止这类跨文件读取，
因此必须经由 HTTP 访问。两份文档只登记 7 位短 hash，页面另经
/__commit?h=<hash>[,<hash>...] 接口用本仓库 git 读取提交时间与提交信息
原文；git 不可用时接口返回 501，页面降级为只显示 hash。
"""

import http.server
import json
import os
import re
import subprocess
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from urllib.parse import parse_qs, urlsplit

# git show 输出格式：完整 hash、作者日期（ISO 8601）、提交信息原文，以 \x1e 结束一条记录
GIT_FORMAT = '%H%x1f%aI%x1f%B%x1e'
HASH_RE = re.compile(r'[0-9a-fA-F]{4,40}')


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/__commit':
            self.serve_commits(parse_qs(url.query).get('h', [''])[0])
        else:
            super().do_GET()

    def send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def serve_commits(self, param):
        tokens = sorted({t.strip() for t in param.split(',') if t.strip()})
        if any(not HASH_RE.fullmatch(t) for t in tokens):
            self.send_json(400, {'error': 'invalid hash'})
            return
        # 非 git 仓库或 git 缺失属于整体不可用，返回 501 让页面给出明确降级提示，
        # 与单个 hash 查不到（正常情况，返回 ok:false）区分开
        try:
            probe = subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=self.directory,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except OSError:
            self.send_json(501, {'error': 'git unavailable'})
            return
        if probe.returncode != 0:
            self.send_json(501, {'error': 'not a git repository'})
            return
        with ThreadPoolExecutor(max_workers=8) as pool:
            commits = dict(zip(tokens, pool.map(self.read_commit, tokens)))
        self.send_json(200, {'commits': commits})

    @staticmethod
    def read_commit(token):
        try:
            proc = subprocess.run(
                ['git', 'show', '-s', '--no-notes', f'--format={GIT_FORMAT}', token],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return {'ok': False}
        if proc.returncode != 0:
            return {'ok': False}
        parts = proc.stdout.decode('utf-8', 'replace').strip('\n\x1e').split('\x1f', 2)
        if len(parts) != 3:
            return {'ok': False}
        return {'ok': True, 'hash': parts[0], 'time': parts[1], 'message': parts[2]}


def main():
    argv = sys.argv[1:]
    open_browser = '--no-open' not in argv
    exit_busy = '--exit-busy' in argv
    argv = [a for a in argv if not a.startswith('--')]
    root = os.path.abspath(argv[0]) if argv else os.getcwd()
    port = int(argv[1]) if len(argv) > 1 else 8765
    handler = partial(QuietHandler, directory=root)
    try:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    except OSError:
        if exit_busy:
            print(f'port {port} in use, assume an existing TEST-GOVERNANCE server', flush=True)
            return
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    url = f'http://127.0.0.1:{server.server_address[1]}/TEST-GOVERNANCE.html'
    print(url, flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
