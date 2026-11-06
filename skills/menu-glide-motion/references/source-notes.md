# 出处与迁移边界

本 Skill 归纳自 Cindy 项目的公开桌面端实现。示例代码是面向教学重新编写的版本，不是上游组件的副本。

**上游项目**：https://github.com/makecindy/cindy （Apache-2.0）

## 核心证据

- [dropdown-menu-highlight.ts](https://github.com/makecindy/cindy/blob/main/apps/desktop/src/renderer/components/ui/dropdown-menu-highlight.ts)：共享层、`transform`/`opacity`、面板整体指针坐标、最近条目、合帧、滚动裁剪、面板缩放、键盘焦点、减少动态效果、面板宽度锁定。
- [menu-row.tsx](https://github.com/makecindy/cindy/blob/main/apps/desktop/src/renderer/components/ui/menu-row.tsx)：高亮 DOM、面板挂载、行状态与排版、粗体宽度预留。
- [dropdown-menu.tsx](https://github.com/makecindy/cindy/blob/main/apps/desktop/src/renderer/components/ui/dropdown-menu.tsx)：Radix DropdownMenu 与共享层的集成。
- [dropdownMenuHighlight.test.tsx](https://github.com/makecindy/cindy/blob/main/apps/desktop/src/renderer/components/ui/__tests__/dropdownMenuHighlight.test.tsx)：单层、分割线、键盘、减少动态效果、scale 坐标修正、合帧的测试。
- [DESIGN.md](https://github.com/makecindy/cindy/blob/main/docs/design-rules/DESIGN.md)：给出 `--motion-instant:80ms`、`--motion-ease-out:cubic-bezier(0.16,1,0.3,1)`、`--motion-ease-in:cubic-bezier(0.4,0,1,1)`，并把面板浮现与高亮跟随列为两套动画。

## 容易误解的点

1. 高亮跟随不依赖 Framer Motion、弹簧物理或 canvas。桌面端用 CSS transition 加直接 DOM 样式更新。
2. 丝滑不来自长时长。80ms 的短过渡配快速起步的缓动，比长拖尾更适合菜单。
3. `transform` 便于合成，但主线程仍要测量矩形、处理事件。
4. 鼠标高亮只是视觉效果。Radix 仍负责焦点、ARIA 和选择。
5. 滚动裁剪、面板缩放、宽度锁定属于上游的复杂细节，按需求迁移。不能假设其他宿主提供相同的 DOM API。

## 授权

本 Skill 是对公开实现原理的分析性总结。Cindy 仓库使用 Apache-2.0。把上游实际代码或大段注释复制进商业或开源项目时，检查许可证和 NOTICE 义务。本 Skill 内的最小示例独立编写，可直接改编。宜保留对 Cindy 的归因链接。
