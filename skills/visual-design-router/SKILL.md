---
name: visual-design-router
description: 视觉设计路由：网页、应用与品牌的视觉设计与重设计，按任务读取对应设计技能。只改逻辑、行为或布局而不改视觉呈现，或只需评审时不触发。
---

# 视觉设计路由

根据任务选择所需方法，读取选中的技能并继续完成用户请求。

## 选择依据

先读取已有的设计约束、相关界面和用户提供的参考。已有 DESIGN.md 或已确认视觉方向时，默认沿用；用户明确要求改变风格时，以本次要求确定变更范围。

同一界面默认采用一套视觉风格。品牌资产与界面实现属于不同交付物时，可以分别选择对应技能。

## 路由表

| 任务与已有证据 | 读取的技能 |
|---|---|
| 生成品牌规范板、标志系统、品牌视觉展示图；主要交付物是图像 | [brandkit](../../../.agents/skills/brandkit/SKILL.md) |
| 新建落地页、作品集或编辑型网页，需要依据受众和参考推断合适风格 | [design-taste-frontend](../../../.agents/skills/design-taste-frontend/SKILL.md) |
| 用户要求改进已有网站或应用，主要工作是诊断并修复现有视觉问题 | [redesign-existing-projects](../../../.agents/skills/redesign-existing-projects/SKILL.md) |
| 用户或明确参考要求暖色单色、文档式排版、扁平和克制的界面 | [minimalist-ui](../../../.agents/skills/minimalist-ui/SKILL.md) |
| 用户或明确参考要求工业制图、机械终端、瑞士排版或粗野主义风格 | [industrial-brutalist-ui](../../../.agents/skills/industrial-brutalist-ui/SKILL.md) |
| 用户或明确参考要求具有空间层次、材质与精细微动效的高端网站 | [high-end-visual-design](../../../.agents/skills/high-end-visual-design/SKILL.md) |
| 用户要求以 GSAP 滚动叙事、固定分镜或堆叠动效为核心的营销页面 | [gpt-taste](../../../.agents/skills/gpt-taste/SKILL.md) |
| 用户明确需要比较多个视觉方向，各方向独立选用风格 | [design-exploration](../../../.agents/skills/design-exploration/SKILL.md) |
| 视觉方向已确认，需要创建或更新 DESIGN.md | [design-creator](../../../.agents/skills/design-creator/SKILL.md) |

对于游戏UI界面优先遵循对应项目 DESIGN.md 和引擎 UI 工作流。仅在用户需要上述品牌资产、网页原型或明确选择相应视觉方法时，才加载表中的网页或品牌技能；网页框架和 CSS 规则不直接套入引擎 UI。

## 读取与执行

1. 从表中选定技能开始执行时，用一句话说明采用的技能及其与当前任务的关系，然后继续工作。
2. 若目标文件缺失，检查当前技能安装位置，向用户报告当前情况，并询问是否需要继续执行。
