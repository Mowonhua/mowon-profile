# Mowon's Profile

个人 AI 配置的单一事实源：跨 harness（ZCode、Claude Code、ChatGPT 等）、跨主机同步的提示词、skills 与全局指令。

## 结构

| 路径 | 内容 |
| --- | --- |
| `system/` | 全局指令源文件，如各 harness 通用的 `AGENTS.md` |
| `skills/<name>/` | skill 集合，每个 skill 一个目录，含 `SKILL.md` |
| `.scratch/` | 本地草稿区，不入库 |

## 安装

克隆本仓库后执行 `./install.sh`（macOS / Linux / Windows Git Bash）或 `install.ps1`（Windows PowerShell 5.1+），幂等、可重复执行：

| 仓库内容 | 目标位置 | 方式 |
| --- | --- | --- |
| `system/AGENTS.md` | `~/.zcode/AGENTS.md`、`~/.codex/AGENTS.md`、`~/.claude/CLAUDE.md`、`~/.pi/agent/AGENTS.md`、`~/.dsh/AGENTS.md`、`~/.qoder-cn/AGENTS.md` | 软链接，映射见 `install.sh` 的 `GLOBAL_PROMPTS`（`install.ps1` 同）；目标已有不同内容时先原位备份为 `<目标>.bak-<时间戳>` 再替换 |
| `skills/<name>/` | `~/.agents/skills/<name>/` | 软链接（各 harness 共用的统一 skill 目录） |
| `install/skills-cloud.list` 中的云端 skills | `~/.agents/skills/` | `npx skills@latest add`；已记录在 `~/.agents/.skill-lock.json` 中的自动跳过，更新用 `npx skills update` |

两个脚本的提示信息均为英文。Windows 下创建符号链接需要管理员或开发者模式：目录链接自动降级为 junction，文件降级为复制。

云端 skill 的分发目标 agent 默认 `codex`（skills CLI 对这类 universal agent 只写入统一目录 `~/.agents/skills`，不改动各 harness 目录），可用 `SKILLS_AGENTS=... ./install.sh` 覆盖。按 skill 配置各模型可见性的分发暂未实现。
