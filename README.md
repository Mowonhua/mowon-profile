# Mowon's Profile

个人 AI 配置的单一事实源：跨 harness（ZCode、Claude Code、ChatGPT 等）、跨主机同步的提示词、skills 与全局指令。

## 结构

| 路径 | 内容 |
| --- | --- |
| `system/` | 全局指令源文件，如各 harness 通用的 `AGENTS.md` |
| `skills/<name>/` | skill 集合，每个 skill 一个目录，含 `SKILL.md` |
| `.scratch/` | 本地草稿区，不入库 |

## 安装

将仓库内容安装到各主机的用户级配置目录：

| 仓库内容 | 目标位置 |
| --- | --- |
| `system/AGENTS.md` | `~/.zcode/AGENTS.md` |
| `skills/<name>/` | `~/.agents/skills/<name>/`（各 harness 共用的统一 skill 目录） |

目前为手动复制或链接；一键安装脚本（幂等、按映射配置模型可见性）在计划中。
