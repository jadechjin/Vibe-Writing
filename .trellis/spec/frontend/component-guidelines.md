# Component Guidelines

> How components are built in this project.

---

## Overview

Most layout components in this repository are prop-driven composition layers with inline style objects and strongly typed props. Gate-specific panels are allowed to act as feature containers when their hooks and actions are tightly scoped to that panel.

Common characteristics in the current codebase:

- props are usually declared as `Readonly<{ ... }>`
- style maps are kept in-file with `CSSProperties`
- large page behavior is assembled by composing slot-style components
- layout components do not fetch their own data

Reference files:

- `frontend/components/layout/MainShell.tsx`
- `frontend/components/layout/ProjectWorkspace.tsx`
- `frontend/components/layout/GateNav.tsx`
- `frontend/components/gates/GatePanel.tsx`
- `frontend/components/gates/SystemDefinitionForm.tsx`
- `frontend/components/tasks/StatusTray.tsx`

---

## Component Structure

A common component file structure in this repo is:

1. imports
2. prop types
3. small local helper types/functions
4. inline style constants
5. component export

Examples:

- `frontend/components/gates/SystemDefinitionForm.tsx` separates field config, helpers, styles, then the component
- `frontend/components/gates/GatePanel.tsx` defines prop types, gate-resolution helpers, style objects, then the component
- `frontend/components/layout/GateNav.tsx` keeps visual tokens and style constants in the same file as the component

This project currently prefers self-contained component files over scattering tiny styling or helper files for every component.

---

## Props Conventions

Current prop conventions:

- use `Readonly<{ ... }>` for props objects
- prefer explicit prop names over passing generic config blobs
- pass rendered panel slots as `ReactNode` when building shell/layout components
- keep transport or domain-specific types imported from hooks instead of redefining them locally

Real examples:

- `frontend/components/layout/MainShell.tsx`
- `frontend/components/layout/ProjectWorkspace.tsx`
- `frontend/components/gates/GatePanel.tsx`
- `frontend/components/evidence/EvidenceHub.tsx`

---

## Styling Patterns

The active styling system is inline object styles typed with `CSSProperties`.

Patterns already used across the repo:

- export-free local style constants near the component
- composition through object spread for variants
- design tokens represented as plain objects, for example `gateStateTokens` in `frontend/components/layout/GateNav.tsx`

There is no Tailwind, CSS Modules, or styled-components baseline in the current repository. New components should follow the existing inline-style approach unless the project intentionally migrates styles globally.

---

## Accessibility

The codebase is still lightweight here, but the good patterns already present should continue:

- semantic container elements like `main`, `section`, `nav`, `header`, `label`, `button`
- explicit `type="button"` on non-submit buttons
- `aria-label` or `aria-current` where navigation semantics matter

Real examples:

- `frontend/components/layout/GateNav.tsx` uses `nav aria-label="Gate navigation"` and `aria-current`
- `frontend/components/gates/SystemDefinitionForm.tsx` uses actual `label`, `textarea`, and `button` elements

---

## Common Mistakes

Avoid these mistakes because they break the patterns already in use:

- fetching data directly inside shell/layout components
- passing mutable props objects around and then mutating them
- introducing a second styling system for one-off components
- duplicating hook-derived domain types inside components
- burying complex state transitions inside presentation-only components
