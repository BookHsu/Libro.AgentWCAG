# React Accessibility Patterns

Use this reference when the target is React or Next.js client-side JSX.

## Common fixes

- `image-alt`
  - Put meaningful `alt` text on `img`.
  - Use `alt=""` only for decorative images.
- `label` / `select-name`
  - Associate `<label htmlFor>` with input/select `id`.
  - If visual layout prevents visible labels, provide `aria-label` or `aria-labelledby`.
- `button-name`
  - Ensure icon-only buttons include visible text or `aria-label`.
- `link-name`
  - Avoid empty anchors or icon-only links without an accessible name.
- `html-has-lang`
  - In Next.js App Router, set document language in `app/layout.tsx`.

## Safe repair hints

- Prefer semantic JSX over role-heavy div/button replacements.
- Avoid duplicating click handlers on nested interactive elements.
- Keep focus order consistent with rendered DOM order.
