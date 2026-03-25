# Next.js Accessibility Patterns

Use this reference when the target is a Next.js application.

## Common fixes

- `html-has-lang`
  - Set `lang` in the root layout output.
- `image-alt`
  - Provide `alt` text for `next/image`.
- `link-name`
  - Ensure `next/link` children render discernible text or an accessible name.
- `document-title`
  - Set page titles through metadata APIs.
- `meta-viewport`
  - Avoid viewport settings that block zoom or reflow.

## Safe repair hints

- Verify accessibility after both server render and client hydration.
- Keep route transitions from breaking focus visibility and page titling.
- Use semantic HTML inside client components instead of role-heavy wrappers.
