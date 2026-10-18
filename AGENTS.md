# AGENTS.md

本仓库是个人 AI 配置的单一事实源，在多 harness、多主机之间同步沉淀的提示词、skills 与全局指令。本文件只补充本仓库的约定，全局规则见 `system/AGENTS.md`。

## 目录结构

- `install.sh` — 一键安装脚本（macOS / Linux / Git Bash）：将全局提示词与本地 skills 软链接到用户级配置目录，按清单通过 skills CLI 安装云端 skills；幂等。
- `install.ps1` — Windows 原生安装脚本，行为与 `install.sh` 一致（PowerShell 5.1+；无符号链接权限时目录降级 junction、文件降级复制）。
- `install/` — 安装配置，目前含云端 skills 清单 `skills-cloud.list`。
- `system/` — 各 harness 全局指令的源文件，安装到各主机、各 harness 的全局配置位置。
- `dsh/presets/<preset-name>/` — DeepSeek Harness 的 agent 预设 bundle，内含 `cordis.patch.yml`（预设声明与插件清单）、`lib/`（预设自带的 Cordis 插件）与 `README.md`；用 `dsh plugin` 或 Harness 的插件管理安装，不由安装脚本处理。
- `skills/<skill-name>/` — 每个 skill 一个目录，目录名与 `SKILL.md` frontmatter 的 `name` 一致（kebab-case）。
  - `SKILL.md` — 必需。frontmatter 至少含 `name` 与 `description`；`description` 决定 skill 何时被触发，需写清适用场景与不适用情形。
  - `agents/` — 各 harness 的接口元数据（如 `openai.yaml`），按需添加。
  - `references/` — skill 引用的补充文档，按需添加。
- `.scratch/` — 本地草稿区，已 gitignore，不提交。
- `.scratch/demo` — feature-unit-development skill 的功能视图演示项目；修改视图时同步更新并验证。

## 约定

- 内容一律使用简体中文撰写，技术标识保留英文；`description` 可使用英文以提升跨模型触发稳定性。
- 新增或修改 skill 时，参照既有 skill 的目录结构保持一致；不引入仓库内其他 skill 之外的依赖。
- 新增skill时，向用户询问是否需要配置skill模型不可见，并依据答复配置openai.yaml的policy。
- 本仓库无构建与测试，验证方式为检查目录名与 `name` 一致、frontmatter 完整。
