# 标准模式（中文）

DeepSeek Harness 的 agent 预设。插件清单、工具、工作流与人设都与随 DSH 发布的 `standard` 预设一致，只是系统提示词使用中文。

## 目录

| 路径 | 内容 |
| --- | --- |
| `cordis.patch.yml` | 预设声明：`id: standard-zh` 的插件清单，逐项对应 `@deepseek-ai/dsh-web-app/presets/standard.patch.yml` |
| `lib/index.js` | Cordis 插件 `dsh-preset-standard-zh`：挂载在预设 scope，监听 `system-prompt/assemble` |
| `lib/prompts.js` | 英文原文到中文译文的对照表与匹配逻辑 |

## 提示词改写的做法

系统提示词由各插件通过 `systemPrompt.section()` 注册。预设内的工具段、计划模式段与预设同处一个 scope，注册同名段会直接抛错；身份、Web GUI、MCP 资源、交付物引用等段则在全局 scope。因此本预设不改注册，而是在 `system-prompt/assemble` 瀑布里按段落文本替换：合并并排序后的每个段落交给 `localizePromptText`，命中译表就换成中文，未命中的保持英文。

匹配分三层：去掉反引号、折叠空白后的整段精确匹配；对工具名、URL、goal 阈值、MCP 服务器名单等运行时插值段落做正则抽取后重组；多段落文本按空行拆分，全部段落都有译文时才整体替换。DSH 升级改写某段提示词后，该段会退回英文而不是被错误替换，升级方可在 `lib/prompts.js` 中补译。

人设前缀与计划模式说明不是由插件注册的固定段落，而是 `cordis.patch.yml` 里的配置，已直接写成中文。

不处理的内容：运行时上下文快照、`developer` 消息里的 AGENTS.md、技能目录（都是 user 或 developer 角色的消息，不属于系统提示词），以及第三方 MCP 服务器自己下发的 server instructions。

## 安装

```sh
dsh plugin --profile <profile> add "<本目录的绝对路径>"
```

或在 Harness Web UI 的插件管理里以本目录为来源安装 bundle。安装后预设出现在预设选择器的「自定义」分组，显示名为「标准模式（中文）」；已存在的会话沿用启动时加载的预设，需新建会话才会生效。

## 依赖

- DSH `0.2.1-rc.2` 及同版本的内置插件包（`@deepseek-ai/dsh-*`）。
- 预设行带 `inject: [biliBasicCompactionPolicy]`，用于和 `billion-context` 的压缩接管保持一致：等它的 load-time overlay 装好后预设才激活，嵌套的 `compaction-basic`、`command-compact` 行才会被同样禁用。没有安装 `billion-context` 时需删除这一行，否则预设不会被激活。
