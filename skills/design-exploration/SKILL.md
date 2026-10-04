---
name: design-exploration
description: Explore a product's visual language, implement and show distinct directions as switchable UI prototypes, converge with the user, then delegate DESIGN.md creation to design-creator. Use for greenfield, partial-direction, or substantial visual reorientation work where the design language must be discovered rather than extracted from a mature interface.
---

# Design Exploration

Lead the discovery and convergence of a product's visual language. Turn product intent into several meaningfully different directions, implement them as comparable prototypes, and help the user select a coherent direction.

This skill owns exploration and decision evidence. After convergence, invoke `design-creator` and let that skill create and validate `DESIGN.md` from the confirmed design handoff.

## Core Principles

1. **Explore before specifying.** Do not jump from a short product description directly to a finished design system.
2. **Separate requirements from aesthetic choices.** Product goals constrain the space but do not predetermine one style.
3. **Make directions structurally distinct.** Palette or font swaps do not count as separate directions.
4. **Compare rendered evidence.** Implement every candidate direction as a directly comparable UI prototype before asking the user to choose.
5. **Explain tradeoffs.** State what each direction emphasizes, sacrifices, and risks.
6. **Converge deliberately.** A hybrid is valid only when the combined properties support one coherent thesis.
7. **Preserve uncertainty.** Keep unresolved decisions visible instead of silently turning assumptions into permanent rules.
8. **Delegate the durable artifact.** Only `design-creator` may synthesize the selected direction into `DESIGN.md`.

# Workflow

## Phase 0 — Determine the Starting State

Classify the task:

- **Greenfield:** no established visual language exists.
- **Partial direction:** references, keywords, brand fragments, or isolated UI ideas exist without a coherent system.
- **Reorientation:** an existing system is being substantially redirected.

This skill is optimized for Greenfield and Partial direction. For a mature interface that only needs its existing system documented, use a design-system extraction workflow instead.

Treat existing fragments as constraints only when the user says they must remain.

## Phase 1 — Build the Design Brief

Collect or infer only the context needed to judge directions:

- product type and core use cases
- target audience
- platform and interaction environment
- brand or product personality
- desired emotional response
- information density and usage duration
- accessibility and technical constraints
- brand assets that must remain
- explicit references, anti-references, likes, and dislikes

Summarize a concise **Design Brief**:

### Product Context
What the product is and what users do with it.

### Experience Goals
How the product should feel during use.

### Functional Design Constraints
Platform, density, interaction, accessibility, and implementation constraints.

### Visual Constraints
Only visual decisions already fixed by the user or product.

### Open Questions
Only unresolved choices that materially change the exploration space.

Do not ask the user to restate information already available.

## Phase 2 — Derive Design Criteria

Translate the brief into 4–8 observable, comparative criteria. Examples:

- supports dense operational information without visual noise
- feels arcane without resembling a fantasy inventory UI
- maintains strong hierarchy at desktop scale
- uses geometry that can be implemented consistently across controls
- keeps decorative motifs subordinate to interaction clarity

Avoid unqualified criteria such as "modern", "professional", or "looks good".

Identify the tensions that distinguish plausible directions, such as expressive versus utilitarian, dense versus spacious, ornamental versus restrained, organic versus geometric, tactile versus flat, and familiar versus distinctive. Treat them as continuums rather than binary choices.

## Phase 3 — Research References When Useful

Research only when references would answer a concrete design question. For every useful reference, extract:

- the relevant principle
- the visual mechanisms that create the effect
- transferable properties
- properties that should not be copied

Synthesize principles rather than reproducing another product's identity. If the user prohibits web research, use supplied and local context only.

## Phase 4 — Generate Design Directions

Create 3–5 directions. Default to 3 for a constrained problem and use 4–5 only when the space is genuinely broad.

Describe each direction with:

### Direction Identity
A memorable name and one-sentence thesis.

### Visual Character
Atmosphere, density, ornament, geometry, rhythm, and emotional tone.

### Composition and Layout
Grid behavior, alignment, containment, whitespace, hierarchy, and density.

### Color Strategy
Palette logic and semantic use of color. Values remain provisional until the direction is selected.

### Typography Strategy
Type roles, hierarchy, contrast, rhythm, and treatment of narrative versus technical information.

### Shape Language
Corners, linework, geometry, icons, borders, motifs, and repeated forms.

### Depth and Material
Flat contrast, tonal layers, borders, translucency, shadows, texture, or lighting.

### Component Character
How representative buttons, inputs, panels, tabs, selections, and data displays express the direction.

### Motion Character
Tempo, easing character, transition hierarchy, and whether motion is expressive or functional.

### Distinctive Signature
One to three repeatable ideas that make the direction recognizable without depending on a logo or illustration.

### Risks and Best Fit
Usability, accessibility, maintenance, implementation, and cliché risks, plus the priorities this direction serves best.

Define one representative surface and a fixed content/state fixture that exposes important hierarchy, density, controls, and edge conditions. Every direction must use this same comparison fixture.

## Phase 5 — Prototype and Compare Directions

Invoke the `prototype` skill and follow its **UI prototype** branch. Read that skill's `SKILL.md` and `UI.md` completely before implementation.

Map directions to prototype variants:

- create one variant for every direction
- prefer a suitable existing route; otherwise create one clearly named throwaway route using project conventions
- keep content, data, copy, states, viewport assumptions, and functional scope identical
- preserve structural differences in layout, hierarchy, geometry, typography, depth, components, and motion
- use the prototype skill's URL-backed switcher so all directions share one route
- keep interactions read-only or stubbed unless interaction is essential to judging the direction
- mark the implementation as throwaway and do not promote prototype shortcuts directly into production

Run the prototype and verify every shareable `?variant=` URL. Show the result:

- provide the runnable URL and variant-to-direction mapping
- when supported, present one screenshot per direction at the same viewport
- when a live preview or image cannot be exposed, provide the exact run command and variant URLs and state the limitation

Compare rendered variants against the Phase 2 criteria. Identify the strongest direction for each criterion, important tradeoffs, directions that should merge or be discarded, and properties worth borrowing across directions. Do not hide the reasoning behind an unexplained numeric score.

Ask the user to choose, reject, combine, or revise directions when interactive iteration is possible. Do not invoke `design-creator` while material visual decisions remain unresolved.

## Phase 6 — Converge and Prepare the Design Handoff

Turn the selected direction into one coherent thesis. Resolve contradictions across color, typography, layout, spacing, depth, shape, components, interaction states, motion, iconography, illustration, and domain-specific extensions.

Record a **Design Handoff** for `design-creator` containing:

- product context, audience, platform, and primary tasks
- selected direction and its visual thesis
- prototype URL, winning variant, and the reasons it won
- accepted properties borrowed from other variants and their shared rationale
- confirmed visual and functional constraints
- desired atmosphere plus density, variance, and motion intent
- chosen or strongly preferred palette roles, typography roles, layout model, shape language, depth model, component character, responsive behavior, and interaction behavior
- accessibility target and implementation constraints
- explicit anti-references and forbidden treatments
- unresolved choices that `design-creator` may decide
- user decisions that are fixed and must not be overridden by taste defaults

The handoff describes the selected design; it is not a draft `DESIGN.md`. Do not add a document schema, token schema, final headings, frontmatter, or a `DESIGN.md` skeleton.

## Phase 7 — Delegate DESIGN.md Creation

Invoke `design-creator`. Read its `SKILL.md` completely and provide the Design Handoff plus any selected prototype evidence it needs.

The delegation contract is strict:

- `design-creator` owns the `DESIGN.md` structure, exact values, synthesis, writing, and validation.
- Preserve fixed user decisions and project constraints from the handoff. Apply `design-creator` defaults only where the handoff leaves room.
- If a `design-creator` default conflicts with an explicit user decision, the user decision wins and the deviation should be stated in the resulting design guidance.
- Do not prewrite sections for the subskill, retrofit a second format afterward, or independently revise the generated file against rules from this skill.
- If `design-creator` is unavailable, stop after delivering the Design Handoff and state that `DESIGN.md` could not be created. Do not implement a fallback writer inside this skill.

After `design-creator` finishes, deliver its `DESIGN.md` together with the prototype evidence and selected-direction rationale. When the selected direction is later implemented in production, follow the `prototype` skill's capture and cleanup contract so losing variants and the switcher do not remain in production code.

# Interaction Rules

Ask questions only when missing information would materially change the design space. Prefer a few high-leverage questions over exact color, radius, or font-size choices before coherent directions exist.

If the user requests a one-pass result, still create and compare multiple prototype directions, select the strongest against the criteria, record the assumptions, prepare the handoff, and invoke `design-creator` without waiting for another turn.

When combining directions, restate the hybrid as one thesis and verify every borrowed property against it. Do not mechanically combine one direction's colors, another's typography, and a third's shapes.

# Deliverables

Depending on the current phase, produce:

- `Design Brief`
- `Design Criteria`
- `Reference Findings`
- `Design Directions`
- `Direction Prototype` with runnable URL, variant mapping, and comparable previews when supported
- `Direction Comparison`
- `Selected Direction`
- `Design Handoff`
- `DESIGN.md` created and validated by `design-creator`

The direction prototype is required throwaway implementation code. Do not implement the selected direction as production code unless the user asks.

# Suggested Working Files

```text
design/
├── brief.md
├── directions.md
├── decision.md
└── handoff.md
```

Keep prototype code on the host route or a clearly named throwaway route as required by the `prototype` skill. `design-creator` decides where and how to create the durable `DESIGN.md`.

# Failure Modes

Avoid:

1. generating `DESIGN.md` before directions are rendered and compared
2. offering directions that differ only in palette or typography
3. comparing variants with different content, data, states, or viewport conditions
4. choosing fashionable styling without tying it to product goals
5. copying a reference product's identity
6. combining directions without a coherent thesis
7. defining token rules, output headings, frontmatter, or a `DESIGN.md` skeleton in this skill
8. writing, validating, or post-processing `DESIGN.md` instead of delegating to `design-creator`
9. overriding fixed user choices with `design-creator` defaults
10. leaving losing variants or the prototype switcher in production code
