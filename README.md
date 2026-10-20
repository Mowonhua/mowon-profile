# Mowon's Profile

**一处维护 AI 工作习惯，多台主机共用。**

集中保存全局指令、本地 skills 和 DeepSeek Harness 中文预设，通过安装脚本分发到各 AI 工具的用户配置目录。

[快速安装](#快速安装) · [仓库内容](#仓库内容) · [安装行为](#安装行为) · [MIT 许可证](LICENSE)

```text
system/AGENTS.md           →  Codex · Claude Code · ZCode · Pi · DSH · Qoder CN
skills/<name>/            →  ~/.agents/skills/
install/skills-cloud.list →  按清单安装云端 skills
```

## 快速安装

### 只安装 skills

需要 Git、Node.js 和 npx。交互选择本仓库中的 skills，安装到用户级目录：

```sh
npx skills@latest add Mowonhua/mowon-profile -g
```

指定单个 skill，例如：

```sh
npx skills@latest add Mowonhua/mowon-profile -g --skill feature-unit-development
```

### 安装完整配置

需要 Git。安装云端 skills 还需要 Node.js 和 npx。

```sh
git clone https://github.com/Mowonhua/mowon-profile.git
cd mowon-profile
```

**Windows · PowerShell 5.1+**

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

**macOS / Linux / Windows Git Bash**

```sh
./install.sh
```

安装脚本会替换目标位置的全局指令；已有不同内容时，先备份为 `<目标>.bak-<时间戳>`。脚本可重复执行，已就绪的项会跳过。

## 仓库内容

| 内容 | 入口 |
| --- | --- |
| 全局指令：沟通、执行、注释与验证约定 | [system/AGENTS.md](system/AGENTS.md) |
| 本地 skills：项目初始化、功能建模、设计与评审 | [skills/](skills/) |
| 云端 skills：按清单从上游安装 | [install/skills-cloud.list](install/skills-cloud.list) |
| DeepSeek Harness 标准模式中文预设 | [standard-zh](dsh/presets/standard-zh/README.md) |

`skills/deprecated/` 保存归档 skill，不参与安装。`.scratch/` 是本地草稿区，不入库。

## 安装行为

全局指令和本地 skills 通过链接引用仓库源文件。修改仓库文件即可更新链接目标；Windows 文件复制降级的情况除外。

<details>
<summary>全局指令的目标位置</summary>

`system/AGENTS.md` 分发到以下位置：

| 工具 | 用户配置文件 |
| --- | --- |
| Codex | `~/.codex/AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md` |
| ZCode | `~/.zcode/AGENTS.md` |
| Pi | `~/.pi/agent/AGENTS.md` |
| DeepSeek Harness | `~/.dsh/AGENTS.md` |
| Qoder CN | `~/.qoder-cn/AGENTS.md` |

Windows 创建符号链接需要管理员权限或开发者模式。权限不足时，目录降级为 junction，文件降级为复制。两个脚本的提示信息均为英文。

</details>

<details>
<summary>本地 skills 与云端 skills</summary>

本地 skill 只从 `skills/` 的一级目录安装到 `~/.agents/skills/<name>/`。脚本跳过 `deprecated` 和不含 `SKILL.md` 的目录，不递归安装归档内容。

安装前，脚本会清理指向本仓库 `skills/<同名目录>`、但目标已不存在的链接。有效链接、其他来源的链接和普通目录会保留。

云端 skills 通过 `npx skills@latest add` 安装。脚本跳过已记录在 `~/.agents/.skill-lock.json` 中的项；更新时执行：

```sh
npx skills update
```

云端 skill 默认分发给 `codex`。这类 universal agent 共用 `~/.agents/skills`，不改动各工具的独立 skill 目录。可通过环境变量 `SKILLS_AGENTS` 覆盖目标，例如：

```sh
SKILLS_AGENTS=codex ./install.sh
```

按 skill 配置各模型可见性的分发暂未实现。

</details>

DeepSeek Harness 预设需要单独安装，不经过上述脚本。安装命令与依赖见 [standard-zh 说明](dsh/presets/standard-zh/README.md#安装)。

## 许可证

本仓库采用 [MIT 许可证](LICENSE)。通过云端清单安装的第三方 skills 遵循各自上游许可证。
