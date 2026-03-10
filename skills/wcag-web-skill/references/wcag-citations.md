# WCAG Citations

Use official W3C sources only (`w3.org`).

## Core references by version

- WCAG 2.0: `https://www.w3.org/TR/WCAG20/`
- WCAG 2.1: `https://www.w3.org/TR/WCAG21/`
- WCAG 2.2: `https://www.w3.org/TR/WCAG22/`

## Common SC mapping starters

- 1.1.1 Non-text Content
  - Understanding: `https://www.w3.org/WAI/WCAG22/Understanding/non-text-content`
- 1.3.1 Info and Relationships
  - Understanding: `https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships`
- 1.4.3 Contrast (Minimum)
  - Understanding: `https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum`
- 2.1.1 Keyboard
  - Understanding: `https://www.w3.org/WAI/WCAG22/Understanding/keyboard`
- 2.4.7 Focus Visible
  - Understanding: `https://www.w3.org/WAI/WCAG22/Understanding/focus-visible`
- 3.3.2 Labels or Instructions
  - Understanding: `https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions`
- 4.1.2 Name, Role, Value
  - Understanding: `https://www.w3.org/WAI/WCAG22/Understanding/name-role-value`

## Citation policy

- Attach at least one official citation for each major finding/fix.
- Build Understanding URLs from the selected WCAG version (`20`, `21`, `22`) whenever the SC slug exists.
- If an SC is unresolved automatically, emit `needs-review` and include the nearest canonical SC page.
- Keep rule mappings broad enough to cover the most common axe and Lighthouse accessibility rules before falling back to manual review.
