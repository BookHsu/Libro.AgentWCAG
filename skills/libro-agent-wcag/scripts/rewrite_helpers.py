#!/usr/bin/env python3
"""Reusable text rewrite helpers for HTML, CSS, and JS snippets."""

from __future__ import annotations

import re
from typing import Pattern


def replace_first(pattern: str | Pattern[str], replacement: str, text: str, flags: int = 0) -> tuple[str, bool]:
    compiled = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
    updated, count = compiled.subn(replacement, text, count=1)
    return updated, count > 0


def ensure_css_property(css: str, selector: str, property_name: str, value: str) -> tuple[str, bool]:
    block_pattern = re.compile(rf'({re.escape(selector)}\s*\{{)([^}}]*)(\}})', flags=re.IGNORECASE | re.DOTALL)
    match = block_pattern.search(css)
    declaration = f'  {property_name}: {value};\n'
    if not match:
        appended = css.rstrip() + f'\n{selector} {{\n{declaration}}}\n'
        return appended, True
    body = match.group(2)
    property_pattern = re.compile(rf'(^|\n)\s*{re.escape(property_name)}\s*:\s*[^;]+;', flags=re.IGNORECASE)
    if property_pattern.search(body):
        new_body = property_pattern.sub(lambda m: f'{m.group(1)}  {property_name}: {value};', body, count=1)
    else:
        new_body = body + ('' if body.endswith('\n') else '\n') + declaration
    updated = css[: match.start(2)] + new_body + css[match.end(2):]
    return updated, updated != css


def ensure_js_guard(js: str, guard_name: str, guard_expression: str) -> tuple[str, bool]:
    if guard_name in js:
        return js, False
    prefix = f'const {guard_name} = {guard_expression};\nif (!{guard_name}) {{\n  return;\n}}\n'
    return prefix + js, True
