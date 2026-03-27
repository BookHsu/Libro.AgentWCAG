#!/usr/bin/env python3
"""Reusable text rewrite helpers for HTML, CSS, and JS snippets."""

from __future__ import annotations

import re


def replace_first(pattern: str | re.Pattern[str], replacement: str, text: str, flags: int = 0) -> tuple[str, bool]:
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


def _inject_attr(tag: str, attr_name: str, attr_value: str) -> tuple[str, bool]:
    if re.search(rf'\b{re.escape(attr_name)}\s*=', tag, flags=re.IGNORECASE):
        return tag, False
    if re.search(r'/\s*>$', tag):
        updated = re.sub(r'/\s*>$', f' {attr_name}={attr_value} />', tag)
        return updated, updated != tag
    updated = re.sub(r'>$', f' {attr_name}={attr_value}>', tag)
    return updated, updated != tag


def ensure_react_img_alt(jsx: str, alt_value: str = '""') -> tuple[str, bool]:
    pattern = re.compile(r'<img\b(?![^>]*\balt\s*=)[^>]*?/?>', flags=re.IGNORECASE)
    for match in pattern.finditer(jsx):
        tag = match.group(0)
        updated_tag, changed = _inject_attr(tag, 'alt', alt_value)
        if not changed:
            continue
        updated = jsx[: match.start()] + updated_tag + jsx[match.end() :]
        return updated, True
    return jsx, False


def ensure_vue_img_alt(template: str, alt_value: str = '""') -> tuple[str, bool]:
    pattern = re.compile(r'<img\b(?![^>]*\b(?:alt|:alt|v-bind:alt)\s*=)[^>]*?/?>', flags=re.IGNORECASE)
    for match in pattern.finditer(template):
        tag = match.group(0)
        updated_tag, changed = _inject_attr(tag, 'alt', alt_value)
        if not changed:
            continue
        updated = template[: match.start()] + updated_tag + template[match.end() :]
        return updated, True
    return template, False


def ensure_nextjs_layout_lang(source: str, lang: str = 'en') -> tuple[str, bool]:
    html_component_pattern = re.compile(r'<Html\b[^>]*>', flags=re.IGNORECASE)
    html_tag_pattern = re.compile(r'<html\b[^>]*>', flags=re.IGNORECASE)

    for pattern in (html_component_pattern, html_tag_pattern):
        match = pattern.search(source)
        if not match:
            continue
        tag = match.group(0)
        updated_tag, changed = _inject_attr(tag, 'lang', f'"{lang}"')
        if not changed:
            return source, False
        updated = source[: match.start()] + updated_tag + source[match.end() :]
        return updated, True
    return source, False


def ensure_nextjs_image_alt(source: str, alt_value: str = '""') -> tuple[str, bool]:
    pattern = re.compile(r'<Image\b(?![^>]*\balt\s*=)[^>]*?/?>', flags=re.IGNORECASE)
    for match in pattern.finditer(source):
        tag = match.group(0)
        updated_tag, changed = _inject_attr(tag, 'alt', alt_value)
        if not changed:
            continue
        updated = source[: match.start()] + updated_tag + source[match.end() :]
        return updated, True
    return source, False
