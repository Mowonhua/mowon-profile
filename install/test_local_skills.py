"""在隔离目录中验证本地技能安装，不运行全局配置和云端安装。"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def find_bash():
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            candidate = Path(git).parent.parent / "bin/bash.exe"
            if candidate.is_file():
                return str(candidate)
        return None  # Windows 自带的 bash.exe 是 WSL 入口。
    return shutil.which("bash")


class LocalSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-install-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo with spaces"
        self.skills = self.repo / "skills"
        self.agents = self.base / "agents"
        self.installed = self.agents / "skills"
        self.installed.mkdir(parents=True)
        for name in ("active", "fresh", "retired", "deprecated", "deprecated/archived", "group/nested"):
            directory = self.skills / name
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "SKILL.md").write_text(name, encoding="utf-8")

    def link(self, name, target, relative=False):
        path = self.installed / name
        value = os.path.relpath(target, path.parent) if relative else str(target)
        os.symlink(value, path, target_is_directory=True)
        # 先移除链接，再让 TemporaryDirectory 清理剩余文件，避免遍历目标。
        self.addCleanup(lambda: path.unlink(missing_ok=True))

    def run_installer(self, shell, powershell=False, expected_code=0):
        env = dict(os.environ, AGENTS_HOME=str(self.agents), TEST_REPO=str(self.repo))
        if powershell:
            source = (ROOT / "install.ps1").read_text(encoding="utf-8-sig")
            source = source.split('Info "OS: windows', 1)[0]
            source += '''
$RepoDir = $env:TEST_REPO
$script:CanSymlink = $true
$script:CanJunction = $true
Install-LocalSkills
if ($script:Failed) { exit 1 }
'''
            script = self.base / "run.ps1"
            script.write_text(source, encoding="utf-8-sig")
            command = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
        else:
            source = (ROOT / "install.sh").read_text(encoding="utf-8")
            source = source.split("CAN_SYMLINK=0; can_symlink", 1)[0]
            source += '''
REPO_DIR="$TEST_REPO"
if command -v cygpath >/dev/null 2>&1; then
  REPO_DIR="$(cygpath -u "$REPO_DIR")"
  AGENTS_HOME="$(cygpath -u "$AGENTS_HOME")"
fi
CAN_SYMLINK=1
install_local_skills
exit "$FAILED"
'''
            script = self.base / "run.sh"
            script.write_text(source, encoding="utf-8", newline="\n")
            command = [shell, script.as_posix()]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)

    def check_install(self, shell, powershell=False):
        self.link("active", self.skills / "active")
        self.link("retired", self.skills / "retired")
        self.link("relative", self.skills / "relative", relative=True)
        self.link("external", self.base / "elsewhere/external")
        self.link("prefix", self.repo / "skills-other/prefix")
        self.link("alias", self.skills / "missing")
        (self.installed / "copy").mkdir()
        (self.installed / "copy/local.txt").write_text("keep", encoding="utf-8")
        (self.skills / "retired").rename(self.skills / "deprecated/retired")
        if os.name == "nt":
            # junction 是 Windows 无符号链接权限时的安装方式。
            ps = shutil.which("powershell") or shutil.which("pwsh")
            (self.skills / "junction").mkdir()
            env = dict(os.environ, TEST_LINK=str(self.installed / "junction"),
                       TEST_TARGET=str(self.skills / "junction"))
            subprocess.run([ps, "-NoProfile", "-Command",
                            "New-Item -ItemType Junction -Path $env:TEST_LINK -Value $env:TEST_TARGET | Out-Null"],
                           env=env, check=True, capture_output=True)
            (self.skills / "junction").rmdir()
            junction = self.installed / "junction"
            self.addCleanup(lambda: os.rmdir(junction) if os.path.lexists(junction) else None)
        for _ in range(2):
            self.run_installer(shell, powershell)
            for removed in ("retired", "relative", "junction"):
                self.assertFalse(os.path.lexists(self.installed / removed), removed)
            self.assertEqual(set(p.name for p in self.installed.iterdir()),
                             {"active", "fresh", "external", "prefix", "alias", "copy"})
            self.assertEqual((self.skills / "deprecated/retired/SKILL.md").read_text(), "retired")
            self.assertEqual((self.installed / "active/SKILL.md").read_text(), "active")
            self.assertEqual((self.installed / "copy/local.txt").read_text(), "keep")
        # 仓库目录暂时不可访问时，不应把本地技能全部判成已删除。
        self.skills.rename(self.repo / "skills-away")
        env_missing = self.base / "missing-root"
        env_missing.mkdir()
        self.repo = env_missing
        self.run_installer(shell, powershell, expected_code=1)
        self.assertTrue(os.path.lexists(self.installed / "active"))

    @unittest.skipUnless(find_bash(), "Bash unavailable")
    def test_bash(self):
        self.check_install(find_bash())

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell"), "Windows PowerShell unavailable")
    def test_windows_powershell(self):
        self.check_install(shutil.which("powershell"), powershell=True)

    @unittest.skipUnless(os.name == "nt" and shutil.which("pwsh"), "PowerShell 7 unavailable")
    def test_pwsh(self):
        self.check_install(shutil.which("pwsh"), powershell=True)


if __name__ == "__main__":
    unittest.main()
