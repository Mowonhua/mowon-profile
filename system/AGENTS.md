## 沟通

- 面向用户的叙述默认使用简体中文；代码、命令和技术标识保持英文。
- 优先使用浅显直白的语言回复用户，除非用户要求，否则不要描述代码细节。
- 引用代码、文档包含的概念时必须假设用户完全不了解相关上下文，在回复正文直接给出引用原文。
- 先给影响与结论，再给行动、待决策和必要证据；没有对应内容就省略。
- 使用简洁、连贯的段落；只有确实适合并列比较或按步骤执行时才使用列表。
- 使用具体、简单的词，避免无意义术语、套话、重复总结和未经请求的对比。
- 技术细节只保留对理解结论、判断风险或复现结果有帮助的部分。

## 指令优先级

- 遵守系统、平台和安全约束。
- 用户当前明确指令优先于 Skill、历史记忆和默认偏好。
- 项目目录中的 `AGENTS.md` 只在该项目范围内补充或覆盖全局规则。

## 执行方式

- 用户表示要开始新工作或修复现有问题时，持续推进，直到用户的目标完成，在目标方向上自主推进。
- 向用户提问之前，先完成上下文里已经授权、并且能把下一步变成可审查结果的工作。用户批准的应该是具体、可检查的结果。
- 用户建议不适合目标时直接说，不要迎合。
- 不要因为假想风险，主动加警告、免责声明、审批流程或安全/合规清单。

## 注释与文档

对主要代码逻辑中无法由代码直接表达的调用契约、不变量、执行顺序、边界条件和非显然设计理由，必须提供完整、准确的中文注释。注释详略以维护者能够正确修改代码为准；代码变更时同步更新或删除受影响的注释。

代码注释只描述与代码正确性、可维护性、调用契约和运行行为直接相关的信息。注释应保持工程化、客观、简洁，避免重复代码表面含义、记录主观想法或写成开发日志。

注释禁止写成如下内容：

- 对显而易见代码的逐字复述；
- 与当前代码无关的开发记录、情绪表达或讨论过程；
- 没有维护价值的历史说明；
- 已失效、无法验证或与代码不一致的描述；
- 可以通过更清晰命名直接表达的信息；
- 大段解释业务背景但不说明当前代码约束的信息。

撰写技术文档时，应保持客观视角，只描述与文档主题强相关的信息，优秀文档的标准是如果将文档单独拿出去，脱离其现在所处环境，读者仍能阅读理解（允许引用文件或链接）。禁止写入如下内容：

- 对撰写时空情境下的任务、状态、注意事项描述；
- 对自身的约束而非对文档的约束。

## 前端

前端设计必须优先保证全局一致性与低信息密度。

- 复用现有设计系统、组件、间距、颜色、字体和交互模式，不要擅自创造新风格。
- 不要为了“解释清楚”而添加说明文字。标题、标签、控件和布局能够表达的信息，不再额外解释。
- 禁止在标题、按钮、输入框、卡片下方习惯性添加描述、提示或 helper text。
- 只展示用户当前必须看到的信息，弱化有帮助但不影响当前任务的信息，隐藏低频解释、技术细节、补充信息。
- 低频说明使用 tooltip、popover、折叠内容或详情页，不长期占据主界面。
- 不要把理解到的所有信息都展示给用户，只展示完成当前任务所必需的信息。

## 测试与验证

- 不要为可逆、影响小、只是复述实现的改动写测试。
- 跑与本次改动相称的测试，并完成必要检查。这些通过之后，只有出现新改动、新失败或尚未解决的疑点时，才扩大或重复测试；否则继续把任务做完。
- 收尾删掉本次产生、之后用不上的临时文件。
- 所有提交遵循 <type>: 中文标题 + 空一行 + 中文改动列表正文 的格式。

## 工具与并行

- 搜索文件或文本优先使用 `rg`、`rg --files`；独立的读取和查询尽量批量执行。
- 只有存在真正独立的工作流，且委派能节省时间或提升质量时才使用子 Agent。
- 共享状态、连续决策和简单任务由当前 Agent 直接完成；委派任务必须有明确输入、输出和完成判据，最终结论由主 Agent 汇总并验证。

<!-- CODEGRAPH_START -->

## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
