"""在隔离目录中验证全局提示词的组合、链接与提交钩子，不触碰真实 HOME。"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "install/hooks/post-commit"
LIB = ROOT / "install/compose-prompts.sh"


def find_bash():
    """返回可用的 bash；Windows 自带的 bash.exe 是 WSL 入口，不适用 POSIX 测试。"""
    if os.name != "nt":
        return shutil.which("bash")
    candidates = []
    git = shutil.which("git")
    if git:
        candidates.append(Path(git).parent.parent / "bin/bash.exe")
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def bash_symlink_capable(shell):
    """bash 能否真建出软链接；不能时安装会降级为复制，链接目标无从断言。"""
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [shell, "-c", "MSYS=winsymlinks:nativestrict CYGWIN=winsymlinks:nativestrict ln -s t l && [ -L l ]"],
            cwd=tmp, capture_output=True)
        return result.returncode == 0


def powershell_symlink_capable(shell):
    """PowerShell 能否建出软链接；未开开发者模式且非管理员时不能。"""
    with tempfile.TemporaryDirectory() as tmp:
        command = (f'$d = "{tmp}"; try {{ New-Item -ItemType SymbolicLink -Path (Join-Path $d "l") '
                   f'-Value (Join-Path $d "t") -ErrorAction Stop | Out-Null; exit 0 }} catch {{ exit 1 }}')
        result = subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                                capture_output=True)
        return result.returncode == 0


class GlobalPromptsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="prompt-install-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo with spaces"
        self.home = self.base / "home"
        (self.repo / "install").mkdir(parents=True)
        shutil.copy2(LIB, self.repo / "install/compose-prompts.sh")
        self.write("system/AGENTS.md", "# common\n")
        self.write("system/fragments/alpha.md", "# alpha\n")
        # 刻意不带尾换行：组合必须补上，否则下一个文件会被粘在同一行
        self.write("system/fragments/beta.md", "# beta")
        self.write("system/harness/pi.md", "# pi\n")
        for name in (".pi", ".codex", ".ghost"):
            (self.home / name).mkdir(parents=True)
        self.set_list(
            "# 清单注释",
            "pi|.pi/AGENTS.md|alpha,beta",
            "codex|.codex/AGENTS.md",
            "",
            "ghost|.ghost/AGENTS.md|missing",
        )

    def write(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def set_list(self, *lines):
        # 用 CRLF 写出，验证解析会去掉回车
        self.write("install/prompts.list", "\r\n".join(lines) + "\r\n")

    def run_installer(self, shell, powershell=False, expected_code=0):
        env = dict(os.environ, TEST_REPO=str(self.repo), TEST_HOME=str(self.home),
                   AGENTS_HOME=str(self.home / ".agents"))
        if powershell:
            source = (ROOT / "install.ps1").read_text(encoding="utf-8-sig").split("# [test-cut]", 1)[0]
            source += '''
$RepoDir = $env:TEST_REPO
Set-Variable -Name HOME -Value $env:TEST_HOME -Force
$script:CanSymlink = $true
$script:CanJunction = $true
Install-GlobalPrompts
if ($script:Failed) { exit 1 }
'''
            script = self.base / "run.ps1"
            script.write_text(source, encoding="utf-8-sig")
            command = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
        else:
            source = (ROOT / "install.sh").read_text(encoding="utf-8").split("# [test-cut]", 1)[0]
            source += '''
REPO_DIR="$TEST_REPO"
HOME="$TEST_HOME"
if command -v cygpath >/dev/null 2>&1; then
  REPO_DIR="$(cygpath -u "$REPO_DIR")"
  HOME="$(cygpath -u "$HOME")"
fi
CAN_SYMLINK=1
install_prompts
exit "$FAILED"
'''
            script = self.base / "run.sh"
            script.write_text(source, encoding="utf-8", newline="\n")
            command = [shell, script.as_posix()]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
        return result

    def assert_linked(self, link, target):
        self.assertTrue(os.path.lexists(link), link)
        # samefile 会跟随链接比较实际文件，复制降级的占位项在这里同样会被抳出来
        self.assertTrue(os.path.samefile(link, target), f"{link} does not resolve to {target}")

    def assert_composed(self, key, text):
        path = self.repo / f"system/composed/{key}.md"
        self.assertTrue(path.is_file(), path)
        self.assertNotEqual(path.read_bytes()[:3], b"\xef\xbb\xbf", "composed file must be BOM-free")
        self.assertEqual(path.read_text(encoding="utf-8"), text)

    def check(self, shell, powershell=False):
        common = self.repo / "system/AGENTS.md"
        composed_pi = self.repo / "system/composed/pi.md"

        # 有定制的 harness 指向产物；无定制的指向通用文件；缺片段时告警并退回通用文件
        result = self.run_installer(shell, powershell, expected_code=1)
        self.assertIn("fragment not found", result.stderr)
        self.assert_linked(self.home / ".pi/AGENTS.md", composed_pi)
        self.assert_linked(self.home / ".codex/AGENTS.md", common)
        self.assert_linked(self.home / ".ghost/AGENTS.md", common)
        self.assert_composed("pi", "# common\n\n# alpha\n\n# beta\n\n# pi\n")
        self.assertFalse((self.repo / "system/composed/ghost.md").exists())

        # 重复执行不重写产物；清单外的遗留产物被清理
        self.write("system/composed/orphan.md", "# orphan\n")
        self.set_list("pi|.pi/AGENTS.md|alpha,beta", "codex|.codex/AGENTS.md")
        result = self.run_installer(shell, powershell)
        self.assertNotIn("recomposed", result.stdout)
        self.assertFalse((self.repo / "system/composed/orphan.md").exists())

        # 改通用部分后：产物随重新组合更新，无定制的目标立刻生效
        self.write("system/AGENTS.md", "# common v2\n")
        self.run_installer(shell, powershell)
        self.assert_composed("pi", "# common v2\n\n# alpha\n\n# beta\n\n# pi\n")
        self.assert_linked(self.home / ".pi/AGENTS.md", composed_pi)
        self.assertEqual((self.home / ".codex/AGENTS.md").read_text(encoding="utf-8"), "# common v2\n")

        # 定制被删除后：产物清理，目标回指通用文件
        (self.repo / "system/harness/pi.md").unlink()
        self.set_list("pi|.pi/AGENTS.md", "codex|.codex/AGENTS.md")
        self.run_installer(shell, powershell)
        self.assertFalse(composed_pi.exists())
        self.assert_linked(self.home / ".pi/AGENTS.md", common)

    @unittest.skipUnless(find_bash() and bash_symlink_capable(find_bash()), "Bash symlinks unavailable")
    def test_bash(self):
        self.check(find_bash())

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell") and
                         powershell_symlink_capable(shutil.which("powershell")), "Windows PowerShell symlinks unavailable")
    def test_windows_powershell(self):
        self.check(shutil.which("powershell"), powershell=True)

    @unittest.skipUnless(os.name == "nt" and shutil.which("pwsh") and
                         powershell_symlink_capable(shutil.which("pwsh")), "PowerShell 7 symlinks unavailable")
    def test_pwsh(self):
        self.check(shutil.which("pwsh"), powershell=True)


class PostCommitHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="prompt-hook-test-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        (self.repo / "install/hooks").mkdir(parents=True)
        shutil.copy2(LIB, self.repo / "install/compose-prompts.sh")
        shutil.copy2(HOOK, self.repo / "install/hooks/post-commit")
        (self.repo / "system/harness").mkdir(parents=True)
        (self.repo / "system/AGENTS.md").write_text("# common\n", encoding="utf-8")
        (self.repo / "system/harness/pi.md").write_text("# pi\n", encoding="utf-8")
        (self.repo / "install/prompts.list").write_text("pi|.pi/AGENTS.md\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# readme\n", encoding="utf-8")
        self.git = shutil.which("git")
        self.run_git("init")
        self.commit("init")

    def commit(self, message):
        self.run_git("add", "-A", "--", "README.md", "system", "install")
        self.run_git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-m", message)

    def run_git(self, *args, **kwargs):
        return subprocess.run([self.git, *args], cwd=self.repo, check=True, capture_output=True, text=True, **kwargs)

    def run_hook(self):
        result = subprocess.run(["sh", str(self.repo / "install/hooks/post-commit")],
                                cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    @unittest.skipUnless(shutil.which("git"), "git unavailable")
    @unittest.skipUnless(shutil.which("sh"), "sh unavailable")
    def test_only_prompt_changes_recompose(self):
        composed = self.repo / "system/composed/pi.md"
        # 含提示词的提交：钩子重新组合
        result = self.run_hook()
        self.assertIn("global prompts recomposed: pi", result.stdout)
        self.assertEqual(composed.read_text(encoding="utf-8"), "# common\n\n# pi\n")

        # 只改无关文件：钩子不做事
        (self.repo / "README.md").write_text("# readme v2\n", encoding="utf-8")
        self.commit("docs")
        result = self.run_hook()
        self.assertEqual(result.stdout.strip(), "")

        # 改动 harness 定制：钩子重新组合
        (self.repo / "system/harness/pi.md").write_text("# pi v2\n", encoding="utf-8")
        self.commit("feat")
        result = self.run_hook()
        self.assertIn("global prompts recomposed: pi", result.stdout)
        self.assertEqual(composed.read_text(encoding="utf-8"), "# common\n\n# pi v2\n")


if __name__ == "__main__":
    unittest.main()
