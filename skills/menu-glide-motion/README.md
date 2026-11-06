# Menu Glide Motion

菜单共享高亮技能：每个面板一块共享层，在条目之间快速改道。

## 文件

- `SKILL.md`：触发条件、执行流程、默认参数和边界。Agent 从这里读起。
- `references/implementation.md`：坐标换算、事件处理和框架接入。
- `references/acceptance.md`：交互、无障碍和性能的验收清单。
- `references/source-notes.md`：Cindy 上游出处与授权边界。
- `examples/vanilla/`：无依赖的 HTML、CSS、JavaScript 演示。

## 试用

用浏览器打开 `examples/vanilla/index.html`。缓慢移动、快速跨行、经过分割线，或用 Tab 聚焦后按方向键。示例是单列菜单，不覆盖复杂生产场景。

## 来源

依据 [makecindy/cindy](https://github.com/makecindy/cindy) 的公开 UI 实现整理，上游使用 Apache-2.0。示例为重新编写的最小演示，不是产品组件的逐行拷贝。
