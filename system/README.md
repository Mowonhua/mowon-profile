# system

各 harness 全局指令的源文件。安装脚本在这里组合出每个工具的一份提示词，再链接到该工具的用户配置目录。

| 路径 | 作用 |
| --- | --- |
| `AGENTS.md` | 通用部分，所有 harness 都包含 |
| `fragments/<name>.md` | 按能力复用的片段，可被多个 harness 引用 |
| `harness/<key>.md` | 单个 harness 独有的内容；每个 harness 一个文件，空文件表示没有定制 |
| `composed/<key>.md` | 组合产物，由脚本生成，不入库 |

## 组合规则

单个 harness 的提示词依次是 `AGENTS.md`、清单声明的片段（按声明顺序）、`harness/<key>.md`，文件之间隔一个空行，结果写入 `composed/<key>.md`。

分发清单是 `install/prompts.list`，每行一项：

```text
<harness>|<目标路径，相对 $HOME>|<片段，逗号分隔，可空>
```

`<harness>` 同时是 `harness/<key>.md` 与 `composed/<key>.md` 的文件名。清单里的片段与 harness 文件都是空文件时，该项不产生产物，目标直接链接 `AGENTS.md`。空文件只是占位，往里写内容即生效。

新增一个 harness：在清单追加一行；需要定制时再添加 `fragments/` 或 `harness/` 下的文件。`composed/` 是生成物，不要手写或提交。

## 生效时机

不存在定制的 harness，目标是 `AGENTS.md` 的软链接，改源文件立即生效。

存在定制的 harness，目标指向 `composed/<key>.md`。软链接只能指向一个文件，拼接结果无法是链接，所以组合必须落盘。改完源文件后由两处触发重新组合：

- 运行安装脚本。
- 提交：安装脚本把仓库的 `core.hooksPath` 指向 `install/hooks`，`post-commit` 只在提交确实改动 `AGENTS.md`、`fragments/`、`harness/` 或 `install/prompts.list` 时重新组合。

重新组合只读写本地文件，不联网，也不涉及 skills 安装。

已有 `core.hooksPath` 且指向别处时，安装脚本只告警，不覆盖。
