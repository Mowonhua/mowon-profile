# 双向追踪与自动化检查规范

## 1. 追踪模型与引用语法

**正向关联写在 `features/*.md`；反向索引通过脚本从 `features/*.md` 实时生成。**

不要手工建立或维护独立的功能总表、代码到功能反向表或测试映射表。

统一格式为 `项目相对路径::定位符`。第一个 `::` 分隔文件路径与定位符，后续内容保留语言或框架的原生名称。文件扩展名不限，也允许无扩展名文件；路径必须指向项目内的真实文件。

定位符应能通过项目工具或代码阅读定位到具体声明或用例。可使用限定函数名、方法签名、组件名、声明名、测试全名或框架选择器；不使用行号或随测试顺序变化的序号。没有稳定符号的脚本或声明式文件，可沿用项目约定的入口或声明名称，并在复核时确认其含义。

以下示例只展示写法，不构成支持语言清单：

| 引用对象 | 示例 |
|---|---|
| Python 方法 / pytest 用例 | `src/inventory.py::Inventory.transfer` / `tests/test_inventory.py::TestTransfer::test_success` |
| C++ 方法 / GoogleTest 用例 | `src/inventory.cpp::inventory::Inventory::transfer(int, int)` / `tests/inventory_test.cpp::InventoryTest.TransferSuccess` |
| TypeScript 方法 / 描述式用例 | `src/inventory.ts::Inventory.transfer` / `tests/inventory.spec.ts::inventory > transfers items` |
| Rust 函数 | `src/inventory.rs::inventory::transfer` |
| Go 方法 | `inventory.go::(*Inventory).Transfer` |
| GDScript 方法 | `scripts/inventory.gd::Inventory.transfer` |
| C# 重载方法 | `src/Inventory.cs::Inventory.Transfer(int, string)` |

关联约束：

- **实现关联**：一个 `F-ID` 可关联多个入口与关键实现；一个公共函数也可被多个 `F-ID` 引用。
- **测试关联**：一个 `S-ID` 可关联多个测试节点（以逗号 `,` 分隔）；一个测试节点也可验证多个 `S-ID`。测试代码只有明确断言或观察该场景的预期结果时，才写入 `测试` 列；仅在执行路径上经过某函数不算验证该功能。
- **字符转义**：`测试` 列中的半角或全角逗号分隔多条引用，定位符本身的逗号写为 `\,` 或 `\，`，例如 `tests/math.spec.ts::adds 1\, 2`。单元格内的竖线写为 `\|`；脚本生成索引、查询符号前会还原这些转义。`实现` 列每格只有一条引用，逗号直接保留。路径建议统一使用 `/`，也兼容 Windows 的 `\`。

## 2. 代码与测试变更时的同步动作

**代码符号或测试节点变化时，在同一变更集中同步更新模块文档。**

| 变更动作 | 模块文档同步要求 |
|---|---|
| 重命名或移动源文件、类、函数 | 更新所有引用该符号的 `实现` 表，保留原 `F-ID` |
| 拆分或合并内部实现函数 | 更新 `实现` 表的主入口与关键实现，保留原 `F-ID` |
| 重命名、移动或合并测试 | 更新所有引用该节点的 `行为场景` 表 `测试` 列 |
| 删除测试 | 移除失效测试引用；若场景仍有效且无其他测试，填 `-` |
| 修改代码逻辑 | 结合反向索引、功能关系和代码调用链筛选回归测试 |
| 修改场景预期 | 同步修改关联测试的断言，并检查依赖该功能的上游 `F-ID` |

## 3. `featurectl.py` 检查与索引工具

**使用 `scripts/featurectl.py` 执行静态校验、生成反向索引、统计关联率和计算变更影响候选。**

在包含 Python 3.9+ 的环境中运行以下命令（将 `<skill-dir>` 替换为本 Skill 目录，将 `<project-root>` 替换为目标项目根目录）：

1. 校验文档格式、ID 唯一性、关系合法性、引用路径，并按可用检查器确认定位符：
   `python <skill-dir>/scripts/featurectl.py validate --project <project-root>`
   如果需要 JSON 报告，追加 `--json`。
2. 生成实现符号 → 功能、测试节点 → 场景、功能关系的反向索引 JSON：
   `python <skill-dir>/scripts/featurectl.py index --project <project-root>`
3. 统计行为场景的结构性测试关联比例：
   `python <skill-dir>/scripts/featurectl.py coverage --project <project-root>`
4. 根据改动文件或 Git 基准提交计算受影响的功能候选与待复核测试：
   `python <skill-dir>/scripts/featurectl.py impact --project <project-root> --changed <改动文件路径>`
   或使用 Git 差异：
   `python <skill-dir>/scripts/featurectl.py impact --project <project-root> --git-base HEAD~1 --depth 1`

## 4. 任意语言的符号检查接入

文档解析、反向索引、关联统计和文件级影响分析均不解析目标语言。默认情况下，Python 文件使用内置 `ast` 检查类、函数和方法；其他文件统一检查路径，并提示“仅检查了文件存在，未确认符号”。C/C++ 也遵循这一提示规则。

需要符号级自动校验时，通过 `validate --symbol-checker` 接入项目提供的命令。检查器可调用目标语言的编译器、语言服务、语法树工具或测试发现工具。一个命令接收项目的所有实现和测试引用，混合语言项目由该命令自行分派。无需修改 Skill 脚本或为每种语言增加内置解析器。

```text
python <skill-dir>/scripts/featurectl.py validate --project <project-root> --json --symbol-checker node tools/check-symbol.mjs
```

`--symbol-checker` 必须放在最后，其后的命令及参数全部原样传递，包括以 `--` 开头的参数。命令按参数数组执行，不经 shell；工作目录为项目根目录。解释器后的相对脚本路径以项目根目录为准。每次引用查询默认超时 30 秒，可在 `--symbol-checker` 前设置 `--symbol-checker-timeout <秒数>`。

每条引用启动一次检查器。检查器从标准输入读取一个 UTF-8 JSON 对象：

```json
{"path": "src/inventory.ts", "symbol": "Inventory.transfer", "kind": "implementation"}
```

`path` 为已确认存在且位于项目内的相对文件路径，分隔符统一为 `/`；`symbol` 为还原转义后的完整定位符；`kind` 为 `implementation` 或 `test`。

检查器在标准输出返回一个 UTF-8 JSON 对象，以退出码 `0` 结束；诊断日志写入标准错误。返回格式如下：

```json
{"status": "found", "message": ""}
```

- `found`：已确认定位符存在。
- `missing`：确认定位符不存在，校验报告为 `error`。
- `unknown`：工具无法判断或暂不支持该引用，校验报告为 `warning`，保留复核缺口。

`message` 可省略；提供时必须为字符串。命令无法启动、超时、非零退出、JSON 无效或状态不合法均报告 `error`，不降级为已通过。检查器只查询声明或发现测试，不执行被查询的业务入口或测试用例；实际测试由项目测试命令单独运行。

## 5. 工具边界与静态检查限制

**脚本结果是静态辅助证据，不替代测试运行和代码语义审查。**

- **表格语法约束**：表格使用标准 Markdown `|` 分隔，单元格内的竖线按第 1 节转义，内容保持在同一行，不使用 HTML 换行标签 `<br>`。
- **内置解析边界**：Python `ast` 只确认静态类、函数和方法，不检查类型、调用行为或断言充分性。参数化测试如 `test_fn[case]` 只确认函数名 `test_fn`；动态声明、别名和其他测试选择器按需交给项目检查器或人工复核。配置项目检查器后，由它处理所有语言的引用，替代内置 Python 检查。
- **告警与错误分级**：重复 ID、非法表头、悬空关系目标、缺失源文件、确认缺失的符号或项目检查器失败会报告 `error`（退出码 `1`）；缺少实现表、场景测试填 `-` 或符号尚未确认只报告 `warning`（退出码 `0`），允许未实现草案通过校验。零错误不等于全部符号已经确认。
- **影响分析边界**：`impact` 命令仅根据登记的文件路径及显式 `依赖` / `触发` 关系推导候选集。未登记的共享状态、公共底层函数或动态分发需结合代码搜索或 CodeGraph 补充排查。
