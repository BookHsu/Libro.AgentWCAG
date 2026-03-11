#!/usr/bin/env python3
"""Reusable remediation strategies for common accessibility issues."""

from __future__ import annotations

from typing import Any

DEFAULT_STRATEGY = {
    "summary": "Review the affected element and implement a WCAG-conformant remediation.",
    "priority": "medium",
    "confidence": "medium",
    "auto_fix_supported": False,
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
    },
    "input-image-alt": {
        "summary": "Provide alternative text for image inputs via the alt attribute.",
        "priority": "high",
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
    },
    "button-name": {
        "summary": "Give each button a discernible accessible name.",
        "priority": "high",
        "confidence": "high",
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
    },
    "heading-order": {
        "summary": "Use a logical heading hierarchy without skipping levels unnecessarily.",
        "priority": "medium",
        "confidence": "medium",
        "auto_fix_supported": False,
    },
    "meta-viewport": {
        "summary": "Allow zoom and avoid viewport settings that block reflow or text resize.",
        "priority": "medium",
        "confidence": "medium",
        "auto_fix_supported": True,
    },
}


def get_strategy(rule_id: str) -> dict[str, Any]:
    strategy = DEFAULT_STRATEGY.copy()
    specific = RULE_STRATEGIES.get(rule_id, {})
    merged = {**strategy, **specific}
    merged["framework_hints"] = {
        **DEFAULT_STRATEGY["framework_hints"],
        **specific.get("framework_hints", {}),
    }
    return merged
