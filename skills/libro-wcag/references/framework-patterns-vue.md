# Vue Accessibility Patterns

Use this reference when the target is Vue or Nuxt template code.

## Common fixes

- `image-alt`
  - Bind descriptive `alt` values explicitly on `img`.
- `label` / `select-name`
  - Bind `for` on labels to stable form control IDs.
  - Keep generated IDs deterministic across renders.
- `button-name`
  - Ensure icon buttons include accessible names through text, `aria-label`, or `aria-labelledby`.
- `link-name`
  - Avoid empty `router-link` content.
- `html-has-lang`
  - In Nuxt, set the document language in app config or head metadata.

## Safe repair hints

- Prefer native controls before adding `role` attributes.
- Avoid keyboard-inaccessible custom clickable containers.
- Keep conditional rendering from breaking label/control associations.
