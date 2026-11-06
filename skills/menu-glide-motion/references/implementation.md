# 实现指引

本文件给框架中立的实现规则。最终代码按宿主工程的技术栈落地。

## 结构与状态

```text
菜单面板（定位上下文，指针与键盘事件的边界）
├─ 共享层（aria-hidden, pointer-events:none, absolute）
├─ 菜单项 A（可聚焦、可选中、可禁用）
├─ 分割线（非条目）
├─ 菜单项 B
└─ 菜单项 C
```

交互状态与视觉层位置分开维护。菜单库（例如 Radix）掌管角色、焦点、typeahead 和选择回调。共享层只读当前目标条目。指针指向不等于选中。子菜单各自持有一层，已展开的父项仍可被标记。

## 面板级最近条目

1. `pointermove` 只记录 `clientX/clientY`，不测量。
2. 调度至多一个 rAF；回调里读取最新坐标。
3. 指针在面板内时，读取所有条目的可见矩形（含嵌套滚动裁剪），按纵向距离取最小值。单条目的距离为 `max(top - y, y - bottom, 0)`。
4. 最近条目是禁用项或带独立高亮效果的条目时，该位置不显示共享层。非选项内容（标题、操作卡）定义显式跳过规则。
5. 指针落在面板留白、padding 和分割线上时保持最近的有效指向。离开整个面板才淡出。

纵向最近条目只适合单列菜单。网格、放射形和横向导航改用二维距离。条目多时接虚拟列表，只计算可视节点。

## 可见矩形与坐标

用 `getBoundingClientRect()` 读取条目和面板的屏幕矩形。行内滚动时，与滚动祖先的可见矩形依次求交，得到目标可见矩形。完全被裁剪的条目不能成为指针目标。

面板未缩放时，坐标按下式换算：

```ts
const panelRect = panel.getBoundingClientRect();
const rowRect = row.getBoundingClientRect();
const x = rowRect.left - panelRect.left - panel.clientLeft + panel.scrollLeft;
const y = rowRect.top - panelRect.top - panel.clientTop + panel.scrollTop;
layer.style.transform = `translate3d(${x}px, ${y}px, 0)`;
layer.style.width = `${rowRect.width}px`;
layer.style.height = `${rowRect.height}px`;
```

面板或祖先入场时被统一 scale，`getBoundingClientRect()` 返回视觉尺寸。直接把视觉尺寸写回缩放容器内的共享层，会二次缩放。按下式恢复布局尺寸：

```ts
const sx = panel.offsetWidth > 0 && panelRect.width > 0
  ? panelRect.width / panel.offsetWidth : 1;
const sy = panel.offsetHeight > 0 && panelRect.height > 0
  ? panelRect.height / panel.offsetHeight : 1;
const x = (visibleRect.left - panelRect.left) / sx - panel.clientLeft + panel.scrollLeft;
const y = (visibleRect.top - panelRect.top) / sy - panel.clientTop + panel.scrollTop;
layer.style.width = `${visibleRect.width / sx}px`;
layer.style.height = `${visibleRect.height / sy}px`;
layer.style.transform = `translate3d(${x}px, ${y}px, 0)`;
```

两式只覆盖平移和轴对齐缩放。旋转、斜切和复合 transform 应改用变换矩阵，或把共享层挂到未缩放的坐标系。

## 冷启动、改道与离开

```text
隐藏 -> 激活目标:
  transition:none; 从选中行（没有选中行时用目标行）写入初始几何; opacity:0
  提交起始帧
  transition:transform/opacity 80ms ease-out; 移到目标; opacity:1

激活 A -> 激活 B -> 激活 C:
  同一层连续写 transform，浏览器从当前插值位置改道
  不建动画队列，不替换图层实例

指针离开整个面板:
  opacity:0（80ms ease-in）；保留图层实例

滚动与布局重排:
  关闭 transform 过渡 -> 写入当前可见几何 -> 恢复后续过渡
```

首次定位要让浏览器识别两个不同的样式状态，可用一次布局提交（读取 `offsetWidth`）或连续两次 rAF。这是唯一允许的同步布局特例，不适用于每帧。

## 平滑度的工程边界

- 共享层常驻 DOM，只改单个元素的 `transform`、`opacity` 和必要的宽高。
- 用 rAF 合帧：指针、键盘焦点和滚动事件在一个帧周期内最多触发一次主要位置计算。
- 缓存结构稳定的行节点和滚动祖先，用 `MutationObserver`、`ResizeObserver` 处理失效。矩形随滚动、窗口缩放和重排变化，不能跨帧持久缓存。
- 同一帧内先测量，再写样式，不交替读写。
- `will-change` 不是必需品。菜单多时常驻会占用合成层内存，只在有性能数据时添加。
- 字重从 400 变到 500 会改变文本宽度。用不可见、零高度的粗体副本预留宽度；长文本截断时防止副本破坏省略号。也可以让字重不随状态变化，此时不需要预留。
- 行尺寸直接赋值，跟随过程中不拉伸宽高，除非产品要求变形动画。

## 组件框架接入

**React / Radix**：用 `useMenuPanel()` 一类的 ref 回调加 effect 订阅 DOM 事件，并在清理函数里释放。键盘当前项读 Radix 的 `data-highlighted` 或 `data-state`，不重复实现 Radix 的方向键语义。焦点留在搜索框或编辑器时，用当前索引或 `aria-selected` 指向菜单项，并在其变化时刷新共享层。`pointermove` 不触发 `setState`。

**Vue / Svelte**：在挂载生命周期绑定监听器，在销毁时移除。用 `ref` 持有 DOM 节点，不把高频输入接进响应式更新。`v-if` 或 keyed 重建时清理旧控制器。

**纯 DOM**：参照 `../examples/vanilla/`。示例是单列非滚动菜单的可运行教学实现；生产代码按实际情况补齐嵌套滚动裁剪、面板缩放、动态条目和现有菜单系统的焦点约定。

**Qt / 原生 UI**：每个菜单维护一个自绘的 highlight rect。指针和键盘只更新 rect 的目标位置。用约 80ms 的 ease-out 属性动画，允许从当前进度直接改道。高刷新率和窗口缩放下都要保证位置正确。
