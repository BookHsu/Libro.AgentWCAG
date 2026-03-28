#!/usr/bin/env python3
"""Reusable remediation strategies for common accessibility issues."""

from __future__ import annotations

from typing import Any

DEFAULT_STRATEGY = {
    "summary": "Review the affected element and implement a WCAG-conformant remediation.",
    "priority": "medium",
    "confidence": "medium",
    "auto_fix_supported": False,
    "auto_fix_reason": "Requires manual review to determine correct remediation",
    "assisted_steps": [
        "Identify the affected DOM node and confirm the semantic role expected by WCAG.",
        "Apply a minimal structural change that preserves existing behavior and layout.",
        "Re-run scanner checks and validate keyboard/screen-reader behavior manually.",
    ],
    "verification_rules": [
        "The finding no longer appears in scanner output for the modified target.",
        "Keyboard navigation and focus order remain functional after the change.",
    ],
    "framework_hints": {
        "html": "Use semantic HTML and explicit accessible names.",
        "react": "Prefer semantic JSX and explicit aria/label props.",
        "vue": "Bind semantic attributes explicitly in templates.",
        "nextjs": "Preserve semantic output after server/client rendering.",
    },
}

RULE_STRATEGIES = {
    "image-alt": {
        "summary": "Add a meaningful alt attribute or mark decorative images with empty alt text.",
        "priority": "high",
        "confidence": "high",
        "auto_fix_supported": True,
        "framework_hints": {
            "react": "In JSX, ensure every <img> has an explicit alt prop; keep icon-only media as alt=\"\".",
            "vue": "In Vue templates, provide alt or :alt bindings for each img element.",
            "nextjs": "For next/image, require alt on every <Image> usage and keep decorative media alt=\"\".",
        },
    },
    "input-image-alt": {
        "summary": "Provide alternative text for image inputs via the alt attribute.",
        "priority": "high",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "area-alt": {
        "summary": "Provide alternative text for image map areas via the alt attribute.",
        "priority": "high",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "meta-refresh": {
        "summary": "Remove timed refresh behavior or replace it with a user-triggered control.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "html-xml-lang-mismatch": {
        "summary": "Keep lang and xml:lang synchronized with the same valid language code.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "valid-lang": {
        "summary": "Normalize invalid language-of-parts lang attributes to a valid BCP-47 value.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "label": {
        "summary": "Associate each form control with a visible label or accessible name.",
        "priority": "high",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "select-name": {
        "summary": "Ensure select elements expose a visible label and accessible name.",
        "priority": "high",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "color-contrast": {
        "summary": "Adjust foreground/background colors to meet the required contrast ratio.",
        "priority": "high",
        "confidence": "medium",
        "auto_fix_supported": False,
        "auto_fix_reason": "Color choices require design intent",
    },
    "button-name": {
        "summary": "Give each button a discernible accessible name.",
        "priority": "high",
        "confidence": "high",
        "auto_fix_supported": True,
        "framework_hints": {
            "react": "Prefer aria-label props for icon-only JSX buttons and keep visible text when present.",
            "vue": "Use aria-label or v-bind:aria-label on icon-only template buttons.",
            "nextjs": "Apply the same button-name rule in app/layout and client components; avoid empty interactive controls.",
        },
    },
    "aria-toggle-field-name": {
        "summary": "Ensure toggle widgets expose a discernible accessible name.",
        "priority": "high",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "aria-tooltip-name": {
        "summary": "Ensure tooltips expose a discernible accessible name.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "aria-progressbar-name": {
        "summary": "Ensure progress bars expose a discernible accessible name.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "aria-meter-name": {
        "summary": "Ensure meters expose a discernible accessible name.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "aria-required-attr": {
        "summary": "Add the role-required ARIA attributes with safe default values.",
        "priority": "high",
        "confidence": "medium",
        "auto_fix_supported": True,
    },
    "aria-valid-attr-value": {
        "summary": "Normalize invalid ARIA attribute values to valid safe defaults.",
        "priority": "medium",
        "confidence": "medium",
        "auto_fix_supported": True,
    },
    "link-name": {
        "summary": "Ensure each link has meaningful, discernible text.",
        "priority": "high",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "html-has-lang": {
        "summary": "Set the document language with a valid lang attribute on the html element.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
        "framework_hints": {
            "react": "Set lang on the root html template emitted by your React app shell.",
            "vue": "Set lang on the root html element in Vue entry templates or SSR shell.",
            "nextjs": "Set lang on <Html> in _document or app router root layout html element.",
        },
    },
    "html-lang-valid": {
        "summary": "Use a valid BCP-47 language code in the lang attribute.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "duplicate-id-aria": {
        "summary": "Ensure every ID referenced by ARIA relationships is unique.",
        "priority": "high",
        "confidence": "medium",
        "auto_fix_supported": False,
        "auto_fix_reason": "Renaming IDs requires understanding of cross-reference relationships",
        "assisted_steps": [
            "Locate duplicated IDs used by aria-* relationships.",
            "Rename duplicated IDs to unique values and update all references.",
            "Re-run accessibility scan to confirm relationship integrity.",
        ],
        "verification_rules": [
            "All ID values are unique in document scope.",
            "aria-labelledby/aria-describedby/aria-controls references resolve to existing elements.",
        ],
    },
    "heading-order": {
        "summary": "Use a logical heading hierarchy without skipping levels unnecessarily.",
        "priority": "medium",
        "confidence": "medium",
        "auto_fix_supported": False,
        "auto_fix_reason": "Heading hierarchy depends on content structure and design intent",
        "assisted_steps": [
            "Identify heading level jumps in document reading order.",
            "Adjust heading tags or section structure to maintain a logical hierarchy.",
            "Confirm visual style remains consistent after semantic heading changes.",
        ],
        "verification_rules": [
            "Heading levels do not skip more than one level in sequence.",
            "Document outline preserves section meaning after remediation.",
        ],
    },
    "td-has-header": {
        "summary": "Link table data cells to matching header cells using headers/id attributes.",
        "priority": "high",
        "confidence": "medium",
        "auto_fix_supported": True,
    },
    "th-has-data-cells": {
        "summary": "Add explicit scope attributes on table headers for data-cell association.",
        "priority": "medium",
        "confidence": "medium",
        "auto_fix_supported": True,
    },
    "presentation-role-conflict": {
        "summary": "Remove presentational roles from interactive elements or restore required semantics.",
        "priority": "high",
        "confidence": "medium",
        "auto_fix_supported": False,
        "auto_fix_reason": "Resolving role conflicts requires understanding element purpose",
        "assisted_steps": [
            "Find elements where role='presentation' or role='none' conflicts with interactive semantics.",
            "Remove conflicting role or replace element with semantically correct markup.",
            "Validate keyboard and screen reader behavior after updates.",
        ],
        "verification_rules": [
            "Interactive elements expose expected role/name/value semantics.",
            "No role='presentation' or role='none' remains on focusable interactive controls.",
        ],
    },
    "region": {
        "summary": "Wrap significant page sections with landmark regions and ensure each region has a clear accessible name when needed.",
        "priority": "medium",
        "confidence": "medium",
        "auto_fix_supported": False,
        "auto_fix_reason": "Landmark structure depends on page layout and content organization",
        "assisted_steps": [
            "Locate repeated structural containers and decide whether they should be landmarks (main/nav/aside/section).",
            "Promote non-semantic wrappers to semantic landmarks or add region roles conservatively.",
            "When multiple identical landmarks exist, add concise labels to distinguish them.",
        ],
        "verification_rules": [
            "Each significant page section is represented by an appropriate landmark or semantic region element.",
            "Duplicate landmarks are distinguishable by accessible names where required.",
        ],
    },
    "skip-link": {
        "summary": "Provide a visible-on-focus skip link that moves keyboard users directly to the main content landmark.",
        "priority": "high",
        "confidence": "medium",
        "auto_fix_supported": False,
        "auto_fix_reason": "Skip link placement and styling require design coordination",
        "assisted_steps": [
            "Add a first-focusable skip link near the beginning of the document.",
            "Ensure the skip link target points to an existing main content container with a stable id.",
            "Keep skip link styling discoverable on keyboard focus without harming layout.",
        ],
        "verification_rules": [
            "The first Tab press exposes an operable skip link.",
            "Activating the skip link moves focus to main content and bypasses repeated navigation.",
        ],
    },
    "tabindex": {
        "summary": "Remove positive tabindex values and keep focus order aligned with DOM reading order.",
        "priority": "high",
        "confidence": "medium",
        "auto_fix_supported": False,
        "auto_fix_reason": "Focus order depends on visual layout and interaction design",
        "assisted_steps": [
            "Find elements using positive tabindex and review whether they are natively focusable.",
            "Replace positive tabindex with semantic controls or tabindex='0' only when necessary.",
            "Retest full keyboard traversal to confirm predictable focus order.",
        ],
        "verification_rules": [
            "No interactive element relies on positive tabindex for focus sequencing.",
            "Tab and Shift+Tab order follows a logical visual and DOM progression.",
        ],
    },
    "nested-interactive": {
        "summary": "Separate nested interactive controls so each actionable element has its own valid focus and activation behavior.",
        "priority": "high",
        "confidence": "medium",
        "auto_fix_supported": False,
        "auto_fix_reason": "Separating nested controls requires markup restructuring",
        "assisted_steps": [
            "Locate interactive descendants placed inside other interactive ancestors.",
            "Refactor markup so only one interactive root handles the action, or split controls into sibling elements.",
            "Retest keyboard focus, Enter/Space activation, and screen reader announcements.",
        ],
        "verification_rules": [
            "No interactive element is nested within another interactive control.",
            "Each control exposes a distinct role/name/value and predictable keyboard behavior.",
        ],
    },
    "document-title": {
        "summary": "Ensure the document has a non-empty, descriptive title.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "list": {
        "summary": "Ensure list containers contain only listitem children.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "listitem": {
        "summary": "Ensure each listitem is nested inside a semantic list container.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "table-fake-caption": {
        "summary": "Convert caption-like header rows into semantic table captions when safe.",
        "priority": "medium",
        "confidence": "high",
        "auto_fix_supported": True,
    },
    "meta-viewport": {
        "summary": "Allow zoom and avoid viewport settings that block reflow or text resize.",
        "priority": "medium",
        "confidence": "medium",
        "auto_fix_supported": True,
    },
}

FRAMEWORK_STRATEGIES = {
    'image-alt': {
        'react': 'Use JSX rewrite helper to append alt on bare <img> tags.',
        'vue': 'Use template rewrite helper to append alt on <img> when missing alt/:alt.',
        'nextjs': 'Use next/image rewrite helper to append alt on <Image> components.',
    },
    'html-has-lang': {
        'nextjs': 'Prefer setting lang on <Html> or root <html> in layout.tsx/_document.tsx.',
    },
    'button-name': {
        'react': 'Add aria-label for icon-only JSX buttons while preserving visible labels.',
        'vue': 'Add aria-label (or :aria-label) for icon-only Vue template buttons.',
        'nextjs': 'Apply button-name remediations consistently across server/client components.',
    },
}


def get_framework_strategy(rule_id: str, framework: str) -> str:
    normalized_framework = framework.lower()
    rule_map = FRAMEWORK_STRATEGIES.get(rule_id, {})
    if normalized_framework in rule_map:
        return rule_map[normalized_framework]
    strategy = get_strategy(rule_id)
    return strategy['framework_hints'].get(normalized_framework, strategy['summary'])


def get_strategy(rule_id: str) -> dict[str, Any]:
    strategy = DEFAULT_STRATEGY.copy()
    specific = RULE_STRATEGIES.get(rule_id, {})
    merged = {**strategy, **specific}
    merged["framework_hints"] = {
        **DEFAULT_STRATEGY["framework_hints"],
        **specific.get("framework_hints", {}),
    }
    return merged





