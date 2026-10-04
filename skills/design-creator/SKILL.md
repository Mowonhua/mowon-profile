---
name: design-creator
description: Create or update a durable, spec-compliant DESIGN.md from a confirmed design handoff, selected prototype, or settled visual direction. Combines machine-readable design tokens with precise semantic guidance and anti-generic visual standards. Use after design-exploration converges, or when the user already has enough confirmed design decisions to create the design-system source of truth. Do not use for open-ended visual exploration or UI implementation.
---

# Design Creator

Create `DESIGN.md` as a durable contract for humans, coding agents, design tools, and screen-generation agents. The result must combine two layers:

- **Normative token layer:** exact, machine-readable values in YAML frontmatter.
- **Semantic guidance layer:** visual rationale, application rules, responsive behavior, interaction behavior, and enforceable guardrails in Markdown.

This skill authors the design-system source of truth. It does not explore multiple visual directions and does not implement UI code.

## Required References

Before authoring or updating `DESIGN.md`, read both references completely:

- [references/spec.md](references/spec.md) is the authoritative format, schema, token, section-order, and consumer-behavior contract.
- [references/taste-guidelines.md](references/taste-guidelines.md) guides visual precision, anti-generic decisions, responsive behavior, motion restraint, and product-surface adaptation.

Do not replace the format contract with the taste guidelines. Do not treat taste defaults as stronger than confirmed product decisions.

## Authority Order

Resolve conflicts in this order:

1. Explicit user decisions and confirmed choices from the design handoff.
2. Product behavior, platform constraints, accessibility requirements, and implementation reality.
3. The bundled `DESIGN.md` format specification.
4. Selected prototype evidence and documented direction rationale.
5. Taste guidelines for choices still genuinely open.

The format specification governs how decisions are encoded, not which aesthetic direction wins. Taste guidance improves unresolved choices but must not erase deliberate product identity.

# Workflow

## Phase 1 — Establish the Evidence Set

Read the available inputs in full:

- Design Handoff from `design-exploration`
- selected prototype or comparable screenshots
- decision record explaining why the direction won
- existing brand assets and fixed constraints
- existing `DESIGN.md`, if present
- relevant implementation constraints or component-library limitations

Distinguish each input as:

- **Fixed:** explicitly confirmed and not open to reinterpretation.
- **Preferred:** strongly supported by the selected direction but adjustable to resolve a conflict.
- **Open:** intentionally delegated to this skill.

If the input still contains competing visual directions or unresolved choices that would materially change the design system, stop and return the unresolved decisions to `design-exploration`. Do not silently choose a direction.

If only bounded details are open, resolve them using the authority order and record the reasoning in the document where it helps future application.

## Phase 2 — Classify the Product Surface

Classify the primary surface before applying taste rules:

- marketing or editorial site
- consumer application
- desktop or productivity tool
- dashboard or operational interface
- game UI or HUD
- mixed product with multiple surface types

This classification determines which guidance is relevant. Hero composition, inline editorial imagery, and single-CTA rules apply only to marketing or editorial surfaces. Density, scanability, persistent navigation, technical typography, and restrained motion take priority in operational interfaces. Add domain-specific sections when the product needs them.

## Phase 3 — Resolve the Visual System

Synthesize one internally coherent system from the evidence.

### Atmosphere and Identity

State the visual thesis, audience, emotional response, density, variance, and motion intent. Describe how the central visual tensions are resolved.

### Color

Define semantic color roles with exact values and usage boundaries. Prefer a restrained palette, but do not impose a one-accent rule when the product needs multiple semantic statuses or the handoff confirms a broader palette.

Verify foreground/background contrast against the stated accessibility target. WCAG AA is the default minimum when no other target exists.

### Typography

Define practical semantic roles for display, headings, body text, labels, captions, and technical data as required by the product. Preserve confirmed type choices. Avoid generic defaults only when a more distinctive choice remains legible, available, and appropriate.

### Layout and Spacing

Define grid behavior, containment, max widths, gutters, spacing rhythm, density, grouping, and responsive collapse. Use tokens for reusable values instead of repeating page-specific measurements.

### Elevation and Shapes

Define one consistent depth model and shape language. Explain when hierarchy uses tonal contrast, borders, negative space, shadows, texture, or elevation. Keep corner, line, icon, and container geometry coherent.

### Components and States

Define only system-level component primitives that prevent visual drift. Cover relevant default, hover, active, focus-visible, selected, disabled, loading, empty, and error behavior. States must not rely on color alone.

### Responsive and Motion

Specify responsive behavior for actual supported viewports, minimum touch targets where applicable, overflow constraints, and content-priority changes.

Motion must communicate hierarchy, causality, continuity, or state. Prefer `transform` and `opacity` for animation performance. Persistent decorative loops are opt-in, not a universal default. Always define a `prefers-reduced-motion` behavior when motion is present.

### Guardrails

Turn relevant anti-patterns into product-specific Do's and Don'ts. Avoid generic prohibitions that do not follow from the selected direction. Each guardrail should prevent a plausible implementation drift.

## Phase 4 — Encode the Normative Token Layer

Follow [references/spec.md](references/spec.md) exactly.

- Begin and end YAML frontmatter with exact `---` delimiters.
- Use `version`, `name`, optional `description`, optional `omitted`, and supported token groups.
- Use valid CSS colors.
- Use only `px`, `em`, or `rem` for dimensions governed by the current specification.
- Prefer semantic token names describing role rather than page location.
- Use `{path.to.token}` references and ensure every reference resolves.
- Reference composite typography values only where the specification permits it.
- Represent intentional omissions through `omitted`; do not use omission to hide unfinished design work.
- Keep component tokens reusable and state-oriented rather than page-specific.

Tokens are normative. When prose and token values disagree, correct the prose or tokens before delivery rather than declaring one to be approximate.

## Phase 5 — Write the Semantic Guidance Layer

Use the standard sections and ordering defined by the specification. Preserve exact standard heading names. Add only the extensions the product needs, after the standard sections, such as:

- `## Responsive Behavior`
- `## Motion`
- `## Iconography`
- `## Illustration`
- `## Data Visualization`
- `## Game HUD`
- `## World-Space UI`

Do not duplicate standard headings. Do not turn `DESIGN.md` into a page specification, implementation diary, or catalog of every possible component.

Every prose section should answer:

- what the design rule is
- why it supports the selected direction
- where it applies
- where it must not be used
- which exact token represents it, when applicable

## Phase 6 — Validate Before Delivery

### Format Validation

- YAML is syntactically valid.
- Frontmatter matches the current specification.
- Token references resolve and point to permitted value types.
- Dimensions and color values are valid.
- Standard sections are unique and in the required order.
- Intentional omissions are declared.
- Unknown extension sections appear after standard sections.

### System Validation

- The result traces directly to the selected direction and handoff.
- Fixed user decisions remain unchanged.
- Color, typography, layout, depth, shapes, components, responsive behavior, and motion reinforce one visual thesis.
- Semantic prose and normative tokens agree exactly.
- Another agent can design an unseen screen without inventing a new visual language.
- Rules are reusable and not tied to a single prototype page.
- Guardrails are specific enough to prevent likely AI-generated design drift.

### Accessibility and Runtime Validation

- Text contrast meets the stated target.
- Focus and interaction state are visible without depending only on color.
- Text remains readable at intended sizes and densities.
- Touch targets and responsive collapse match the supported platforms.
- Motion includes reduced-motion behavior and avoids unnecessary continuous animation.
- Font, image, and implementation assumptions are actually available or explicitly documented.

Fix validation failures before delivery. Do not report a known-invalid `DESIGN.md` as complete.

# Existing DESIGN.md

When a `DESIGN.md` already exists, read it before writing.

- For an incremental update, preserve unrelated confirmed rules and token names when they remain valid.
- For an explicit reorientation, replace superseded rules coherently across both tokens and prose.
- Do not leave deprecated values referenced by components.
- Do not overwrite hand-maintained constraints merely because a taste default differs.

# Output Contract

Write the final file to the user-specified location. Otherwise use the relevant project root as `DESIGN.md`.

Deliver:

- the completed `DESIGN.md`
- a concise statement of which handoff or selected prototype it implements
- any intentionally unresolved external dependency, such as an unavailable licensed font

Do not also create an alternative competing design-system document.

# Failure Modes

Avoid:

1. accepting a handoff that still contains unresolved competing directions
2. producing prose without normative tokens
3. filling the schema mechanically without a coherent visual thesis
4. treating taste defaults as stronger than confirmed user choices
5. applying marketing Hero rules to dashboards, tools, or game HUDs
6. banning fonts, layouts, or colors without a product-specific rationale
7. defining continuous animation without reduced-motion behavior
8. using different values for the same concept in prose and tokens
9. encoding prototype-page details as system-wide primitives
10. overwriting an existing design system without reconciling preserved constraints
