# Visual Taste Guidelines

Use these product-neutral guidelines to turn a confirmed visual direction into a precise, non-generic design system. They guide unresolved decisions; they do not override explicit user choices, accessibility, product behavior, or platform constraints.

## Calibrate the Visual Character

Describe the system on three independent axes:

- **Density:** gallery-airy → balanced daily use → cockpit-dense
- **Variance:** predictable symmetry → controlled asymmetry → expressive irregularity
- **Motion:** static restraint → fluid functional motion → cinematic choreography

Do not use a universal default. Derive all three values from the product surface, usage duration, selected prototype, and user decision.

## Color Discipline

- Give each color a descriptive identity, exact value, and functional role.
- Keep neutral temperature internally consistent unless deliberate warm/cool contrast is part of the selected direction.
- Prefer restrained accents and reserve high salience for meaningful actions or status.
- Avoid neon purple/blue gradients, indiscriminate glows, and oversaturated accents unless explicitly confirmed as part of the product identity.
- Avoid pure black when a near-black better supports depth, but preserve pure black when contrast, brand, or display requirements justify it.
- Status colors are semantic infrastructure, not decorative accent proliferation.

## Typography Discipline

- Build hierarchy through role, weight, spacing, rhythm, and color rather than size alone.
- Keep body copy readable and constrain long-form line length when appropriate.
- Use distinctive fonts only when they are available, legible, and suitable for the product.
- For dashboards and technical interfaces, prefer sans-serif families with a compatible monospace face for data when this improves scanning.
- Preserve a confirmed font even when it is common; do not substitute novelty for product continuity.
- Avoid generic serif defaults in expressive work, but allow a deliberate serif system when the selected direction and platform support it.

## Surface-Specific Composition

### Marketing and Editorial Surfaces

- A Hero may use asymmetric composition, restrained inline imagery, and one dominant CTA when these serve the narrative.
- Avoid filler prompts such as “Scroll to explore”, decorative scroll arrows, and generic feature-card rows.
- Inline headline imagery is optional and must not compromise reading order or responsive behavior.

### Applications, Dashboards, Tools, and Game UI

- Prioritize scanability, persistent context, information hierarchy, task continuity, and long-session comfort.
- Do not force a Hero, editorial typography, or marketing CTA model onto operational surfaces.
- Replace decorative card grids with containment, dividers, tables, spatial grouping, or domain-specific structures when appropriate.
- Use monospace for dense numerical data only when it improves alignment and recognition.

## Component Quality

- Buttons need clear default, hover, active, focus-visible, and disabled behavior.
- Inputs use durable label, helper, validation, and error relationships; avoid novelty that obscures form state.
- Cards are justified by hierarchy or grouping, not used as a default wrapper for every block.
- Loading placeholders should match the expected content structure.
- Empty states should explain the state and the next meaningful action.
- Error states must be local, legible, and recoverable where recovery exists.
- Never use custom cursors or outer glow as a substitute for interaction feedback.

## Layout and Responsive Quality

- Prefer explicit grid and containment rules over fragile percentage arithmetic.
- Define max widths, gutters, safe areas, and density changes for supported viewports.
- Multi-column layouts should collapse according to content priority, not through an unconditional one-size-fits-all rule.
- Prevent accidental horizontal overflow on narrow viewports.
- Use `clamp()` when fluid typography or spacing materially improves continuity.
- Interactive touch targets should normally reach at least 44px on touch platforms.
- Avoid overlapping content unless overlap is a deliberate, accessible, and robust part of the confirmed direction.

## Motion and Performance

- Motion should explain state, causality, hierarchy, or continuity.
- Prefer transform and opacity animations; avoid layout-triggering properties when a compositor-friendly alternative exists.
- Use stagger only when it clarifies grouping and does not delay task access.
- Persistent motion is reserved for meaningful live status or a confirmed expressive surface.
- Define `prefers-reduced-motion` behavior for all nonessential motion.
- Do not prescribe a framework-specific animation implementation in the design system unless the project requires it.

## Anti-Generic Guardrails

Select only guardrails relevant to the product and chosen direction:

- no decorative neon glow without semantic purpose
- no arbitrary gradient text used as a substitute for hierarchy
- no generic three-equal-card composition when content relationships differ
- no placeholder names or fake metrics presented as realistic content
- no AI marketing clichés in interface copy
- no filler navigation or scroll instructions
- no inconsistent corner systems, neutral temperatures, or shadow models
- no state communicated by color alone
- no unexplained visual motif used only once

Write guardrails as product-specific Do's and Don'ts. A short enforceable list is better than a universal blacklist.
