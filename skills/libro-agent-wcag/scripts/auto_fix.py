#!/usr/bin/env python3
"""Safe first-pass auto remediation helpers for local HTML files."""

from __future__ import annotations

import difflib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import url2pathname

from rewrite_helpers import (
    ensure_nextjs_image_alt,
    ensure_nextjs_layout_lang,
    ensure_react_img_alt,
    ensure_vue_img_alt,
    replace_first,
)

LANG_PATTERN = re.compile(r'^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$')
SUPPORTED_APPLY_FIXES_SUFFIXES = {'.html', '.htm', '.xhtml', '.jsx', '.tsx', '.vue'}
AUTO_FIX_READ_ENCODINGS = ('utf-8', 'utf-8-sig', 'cp1252', 'latin-1')


def target_to_local_path(target: str) -> Path | None:
    candidate = Path(target)
    if candidate.exists():
        return candidate.resolve()
    parsed = urlparse(target)
    if parsed.scheme == 'file' and parsed.netloc in {'', 'localhost'}:
        return Path(url2pathname(parsed.path)).resolve()
    return None

def supports_apply_fixes_target(local_target: Path) -> bool:
    return local_target.suffix.lower() in SUPPORTED_APPLY_FIXES_SUFFIXES

def _read_text_with_fallback_encoding(target: Path) -> tuple[str, str]:
    raw = target.read_bytes()
    for encoding in AUTO_FIX_READ_ENCODINGS:
        try:
            text = raw.decode(encoding)
            return text.replace('\r\n', '\n').replace('\r', '\n'), encoding
        except UnicodeDecodeError:
            continue
    text = raw.decode('latin-1')
    return text.replace('\r\n', '\n').replace('\r', '\n'), 'latin-1'

def _write_text_atomic(target: Path, content: str, encoding: str = 'utf-8') -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding=encoding,
            delete=False,
            dir=str(target.parent),
            prefix=f'.{target.name}.',
            suffix='.tmp',
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, target)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()

def _fix_html_has_lang(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    match = re.search(r'<html\b([^>]*)>', html, flags=re.IGNORECASE)
    if not match:
        return html, None
    tag = match.group(0)
    if re.search(r'\blang\s*=', tag, flags=re.IGNORECASE):
        return html, None
    replacement = tag[:-1] + ' lang="en">'
    updated, changed = replace_first(re.escape(tag), replacement, html)
    if not changed:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Added lang="en" to the html element.',
    }


def _fix_html_lang_valid(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'(\blang\s*=\s*["\'])([^"\']+)(["\'])', flags=re.IGNORECASE)

    def replacer(match: re.Match[str]) -> str:
        value = match.group(2)
        if LANG_PATTERN.match(value):
            return match.group(0)
        return f'{match.group(1)}en{match.group(3)}'

    updated, changed = replace_first(pattern, replacer, html)
    if not changed or updated == html:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Normalized invalid lang attribute value to "en".',
    }


def _fix_image_alt(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<img\b(?![^>]*\balt\s*=)([^>]*?)(/?)>', flags=re.IGNORECASE)
    updated, count = pattern.subn(r'<img\1 alt=""\2>', html, count=1)
    if count == 0:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Added an empty alt attribute to an img element missing alt text.',
    }


def _detect_framework(local_target: Path, source: str) -> str:
    suffix = local_target.suffix.lower()
    name = local_target.name.lower()
    if suffix == '.vue' or '<template' in source or 'data-v-app' in source:
        return 'vue'
    if 'next' in name or '<Image' in source or '<Html' in source or 'data-nextjs-root' in source:
        return 'nextjs'
    if suffix in {'.jsx', '.tsx'} or 'data-reactroot' in source or 'className=' in source:
        return 'react'
    return 'html'


def _apply_framework_fix(
    html: str, finding: dict[str, Any], framework: str
) -> tuple[str, dict[str, Any] | None]:
    rule_id = finding.get('rule_id', '')
    if rule_id == 'image-alt':
        if framework == 'react':
            updated, changed = ensure_react_img_alt(html)
        elif framework == 'vue':
            updated, changed = ensure_vue_img_alt(html)
        elif framework == 'nextjs':
            updated, changed = ensure_nextjs_image_alt(html)
        else:
            return html, None
        if not changed:
            return html, None
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': f'Applied framework-aware alt remediation for {framework}.',
        }

    if rule_id == 'html-has-lang' and framework == 'nextjs':
        updated, changed = ensure_nextjs_layout_lang(html, lang='en')
        if not changed:
            return html, None
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': 'Added lang="en" on Next.js Html/html layout root.',
        }

    return html, None

def _fix_input_image_alt(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r"<input\b(?=[^>]*\btype\s*=\s*['\"]image['\"])(?![^>]*\balt\s*=)([^>]*?)(/?)>", flags=re.IGNORECASE)
    updated, count = pattern.subn(r'<input\1 alt=""\2>', html, count=1)
    if count == 0:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Added an empty alt attribute to an image input missing alt text.',
    }


def _fix_area_alt(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<area\b(?![^>]*\balt\s*=)([^>]*?)(/?)>', flags=re.IGNORECASE)
    updated, count = pattern.subn(r'<area\1 alt=""\2>', html, count=1)
    if count == 0:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Added an empty alt attribute to an area element missing alt text.',
    }


def _guess_accessible_name(attributes: str, fallback: str = 'Control') -> str:
    for attribute in ('aria-label', 'title', 'placeholder', 'name', 'id'):
        match = re.search(rf'\b{attribute}\s*=\s*["\']([^"\']+)["\']', attributes, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip().replace('-', ' ').replace('_', ' ')
            return value[:1].upper() + value[1:] if value else fallback
    return fallback


def _fix_button_name(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<button\b([^>]*)>(.*?)</button>', flags=re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html):
        attributes = match.group(1)
        inner_html = match.group(2)
        if re.search(r'\baria-label\s*=|\baria-labelledby\s*=|\btitle\s*=', attributes, flags=re.IGNORECASE):
            continue
        visible_text = re.sub(r'<[^>]+>', '', inner_html).strip()
        if visible_text and re.search(r'[A-Za-z0-9]', visible_text):
            continue
        label = _guess_accessible_name(attributes, fallback='Button')
        replacement = f'<button{attributes} aria-label="{label}">{inner_html}</button>'
        updated = html[: match.start()] + replacement + html[match.end() :]
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': f'Added aria-label="{label}" to an icon-only button.',
        }
    return html, None


def _fix_link_name(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<a\b([^>]*)>(.*?)</a>', flags=re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html):
        attributes = match.group(1)
        inner_html = match.group(2)
        if re.search(r'\baria-label\s*=|\baria-labelledby\s*=|\btitle\s*=', attributes, flags=re.IGNORECASE):
            continue
        visible_text = re.sub(r'<[^>]+>', '', inner_html).strip()
        if visible_text and re.search(r'[A-Za-z0-9]', visible_text):
            continue
        label = _guess_accessible_name(attributes, fallback='Link')
        replacement = f'<a{attributes} aria-label="{label}">{inner_html}</a>'
        updated = html[: match.start()] + replacement + html[match.end() :]
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': f'Added aria-label="{label}" to an empty link.',
        }
    return html, None


def _fix_role_name(html: str, finding: dict[str, Any], role: str, fallback: str) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(rf"<([a-z0-9:-]+)\b([^>]*)\brole\s*=\s*['\"]{role}['\"]([^>]*)>(.*?)</\1>", flags=re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html):
        attributes = f'{match.group(2)}{match.group(3)}'
        inner_html = match.group(4)
        if re.search(r'\baria-label\s*=|\baria-labelledby\s*=|\btitle\s*=', attributes, flags=re.IGNORECASE):
            continue
        visible_text = re.sub(r'<[^>]+>', '', inner_html).strip()
        if visible_text and re.search(r'[A-Za-z0-9]', visible_text):
            continue
        label = _guess_accessible_name(attributes, fallback=fallback)
        replacement = f'<{match.group(1)}{match.group(2)} role="{role}"{match.group(3)} aria-label="{label}">{inner_html}</{match.group(1)}>'
        updated = html[: match.start()] + replacement + html[match.end() :]
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': f'Added aria-label="{label}" to a {role} widget missing an accessible name.',
        }
    return html, None


def _fix_aria_toggle_field_name(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    return _fix_role_name(html, finding, 'switch', 'Toggle')


def _fix_aria_tooltip_name(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    return _fix_role_name(html, finding, 'tooltip', 'Tooltip')


def _fix_aria_progressbar_name(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    return _fix_role_name(html, finding, 'progressbar', 'Progress')


def _fix_aria_meter_name(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    return _fix_role_name(html, finding, 'meter', 'Meter')


def _inject_attribute(tag: str, attribute: str, value: str) -> tuple[str, bool]:
    if re.search(rf'\b{re.escape(attribute)}\s*=', tag, flags=re.IGNORECASE):
        return tag, False
    if tag.endswith('/>'):
        return f'{tag[:-2]} {attribute}="{value}"/>', True
    return f'{tag[:-1]} {attribute}="{value}">', True


ROLE_REQUIRED_ATTRIBUTES: dict[str, list[tuple[str, str]]] = {
    'checkbox': [('aria-checked', 'false')],
    'radio': [('aria-checked', 'false')],
    'switch': [('aria-checked', 'false')],
    'combobox': [('aria-expanded', 'false')],
    'slider': [('aria-valuemin', '0'), ('aria-valuemax', '100'), ('aria-valuenow', '0')],
    'spinbutton': [('aria-valuemin', '0'), ('aria-valuemax', '100'), ('aria-valuenow', '0')],
    'progressbar': [('aria-valuemin', '0'), ('aria-valuemax', '100'), ('aria-valuenow', '0')],
}


def _fix_aria_required_attr(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(
        r'<([a-z0-9:-]+)\b([^>]*)\brole\s*=\s*["\']([^"\']+)["\']([^>]*)>',
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        role = match.group(3).strip().lower()
        required = ROLE_REQUIRED_ATTRIBUTES.get(role)
        if not required:
            continue
        tag = match.group(0)
        for attribute, default in required:
            if re.search(rf'\b{re.escape(attribute)}\s*=', tag, flags=re.IGNORECASE):
                continue
            replacement, changed = _inject_attribute(tag, attribute, default)
            if not changed:
                continue
            updated = html[: match.start()] + replacement + html[match.end() :]
            return updated, {
                'rule_id': finding['rule_id'],
                'changed_target': finding['changed_target'],
                'description': f'Added required ARIA attribute {attribute}="{default}" for role "{role}".',
            }
    return html, None


ARIA_BOOLEAN_ATTRIBUTES = {
    'aria-checked',
    'aria-expanded',
    'aria-hidden',
    'aria-pressed',
    'aria-required',
    'aria-selected',
}

ARIA_TRUTHY = {'true', '1', 'yes', 'on'}
ARIA_FALSY = {'false', '0', 'no', 'off'}


def _normalize_aria_value(attribute: str, value: str) -> str | None:
    normalized = value.strip().lower()
    if attribute in ARIA_BOOLEAN_ATTRIBUTES:
        if normalized in ARIA_TRUTHY:
            return 'true'
        if normalized in ARIA_FALSY:
            return 'false'
        return 'false'
    if attribute == 'aria-invalid':
        if normalized in {'grammar', 'spelling', 'true', 'false'}:
            return normalized
        if normalized in ARIA_TRUTHY:
            return 'true'
        if normalized in ARIA_FALSY:
            return 'false'
        return 'false'
    if attribute == 'aria-current':
        if normalized in {'false', 'true', 'page', 'step', 'location', 'date', 'time'}:
            return normalized
        if normalized in ARIA_TRUTHY:
            return 'true'
        if normalized in ARIA_FALSY:
            return 'false'
        return 'false'
    if attribute == 'aria-sort':
        if normalized in {'none', 'ascending', 'descending', 'other'}:
            return normalized
        return 'none'
    return None


def _fix_aria_valid_attr_value(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    supported = sorted(ARIA_BOOLEAN_ATTRIBUTES | {'aria-invalid', 'aria-current', 'aria-sort'})
    pattern = re.compile(
        rf'(\b({"|".join(supported)})\s*=\s*["\'])([^"\']+)(["\'])',
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        attribute = match.group(2).lower()
        current = match.group(3)
        normalized = _normalize_aria_value(attribute, current)
        if normalized is None or normalized == current.strip().lower():
            continue
        replacement = f'{match.group(1)}{normalized}{match.group(4)}'
        updated = html[: match.start()] + replacement + html[match.end() :]
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': f'Normalized invalid {attribute} value to "{normalized}".',
        }
    return html, None


def _fix_td_has_header(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    table_pattern = re.compile(r'<table\b[^>]*>.*?</table>', flags=re.IGNORECASE | re.DOTALL)
    row_pattern = re.compile(r'<tr\b[^>]*>.*?</tr>', flags=re.IGNORECASE | re.DOTALL)
    th_pattern = re.compile(r'<th\b([^>]*)>', flags=re.IGNORECASE)
    td_pattern = re.compile(r'<td\b([^>]*)>', flags=re.IGNORECASE)

    for table_match in table_pattern.finditer(html):
        table_html = table_match.group(0)
        if '<th' not in table_html.lower() or '<td' not in table_html.lower():
            continue
        rows = list(row_pattern.finditer(table_html))
        header_row_index = next((idx for idx, row in enumerate(rows) if '<th' in row.group(0).lower()), None)
        if header_row_index is None:
            continue
        header_row = rows[header_row_index].group(0)
        header_ids: list[str] = []
        header_count = 0

        def replace_th(match: re.Match[str]) -> str:
            nonlocal header_count
            attrs = match.group(1)
            id_match = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs, flags=re.IGNORECASE)
            if id_match:
                header_ids.append(id_match.group(1))
                return match.group(0)
            header_count += 1
            header_id = f'col-{header_count}'
            header_ids.append(header_id)
            return f'<th{attrs} id="{header_id}">'

        updated_header_row = th_pattern.sub(replace_th, header_row)
        updated_table = table_html.replace(header_row, updated_header_row, 1)
        if not header_ids:
            continue

        changed_td = False
        updated_rows: list[str] = []
        for idx, row in enumerate(row_pattern.finditer(updated_table)):
            row_html = row.group(0)
            if idx <= header_row_index or '<td' not in row_html.lower():
                updated_rows.append(row_html)
                continue

            cell_index = 0

            def replace_td(match: re.Match[str]) -> str:
                nonlocal cell_index, changed_td
                attrs = match.group(1)
                if re.search(r'\bheaders\s*=', attrs, flags=re.IGNORECASE):
                    cell_index += 1
                    return match.group(0)
                header_id = header_ids[min(cell_index, len(header_ids) - 1)]
                cell_index += 1
                changed_td = True
                return f'<td{attrs} headers="{header_id}">'

            updated_rows.append(td_pattern.sub(replace_td, row_html))

        if not changed_td:
            continue
        rebuilt_table = row_pattern.sub(lambda _: updated_rows.pop(0), updated_table)
        updated_html = html[: table_match.start()] + rebuilt_table + html[table_match.end() :]
        return updated_html, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': 'Added table header ids and linked data cells with headers attributes.',
        }
    return html, None


def _fix_th_has_data_cells(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<th\b(?![^>]*\bscope\s*=)([^>]*)>', flags=re.IGNORECASE)
    updated, count = pattern.subn(r'<th\1 scope="col">', html)
    if count == 0:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Added scope="col" to table header cells missing scope.',
    }


def _fix_document_title(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    title_match = re.search(r'<title\b[^>]*>(.*?)</title>', html, flags=re.IGNORECASE | re.DOTALL)
    replacement_text = 'Document'
    h1_match = re.search(r'<h1\b[^>]*>(.*?)</h1>', html, flags=re.IGNORECASE | re.DOTALL)
    if h1_match:
        candidate = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
        if candidate:
            replacement_text = candidate
    if title_match:
        current = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        if current:
            return html, None
        replacement = f'<title>{replacement_text}</title>'
        updated, changed = replace_first(re.escape(title_match.group(0)), replacement, html)
        if not changed:
            return html, None
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': f'Set a non-empty document title to "{replacement_text}".',
        }
    head_match = re.search(r'<head\b[^>]*>', html, flags=re.IGNORECASE)
    if not head_match:
        return html, None
    insertion = f'{head_match.group(0)}\n  <title>{replacement_text}</title>'
    updated, changed = replace_first(re.escape(head_match.group(0)), insertion, html)
    if not changed:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': f'Inserted a document title "{replacement_text}".',
    }



def _fix_list(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<(ul|ol)\b([^>]*)>(.*?)</\1>', flags=re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html):
        inner_html = match.group(3)
        if re.search(r'<li\b', inner_html, flags=re.IGNORECASE):
            continue
        stripped = inner_html.strip()
        if not stripped:
            continue
        replacement = f'<{match.group(1)}{match.group(2)}><li>{stripped}</li></{match.group(1)}>'
        updated = html[: match.start()] + replacement + html[match.end() :]
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': 'Wrapped list content with a list item element.',
        }
    return html, None


def _fix_listitem(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<li\b[^>]*>.*?</li>', flags=re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html):
        prefix = html[: match.start()]
        open_count = len(re.findall(r'<(?:ul|ol)\b[^>]*>', prefix, flags=re.IGNORECASE))
        close_count = len(re.findall(r'</(?:ul|ol)>', prefix, flags=re.IGNORECASE))
        if open_count > close_count:
            continue
        replacement = f'<ul>{match.group(0)}</ul>'
        updated = html[: match.start()] + replacement + html[match.end() :]
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': 'Wrapped an orphan list item with a parent unordered list.',
        }
    return html, None


def _fix_table_fake_caption(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<table\b([^>]*)>(.*?)</table>', flags=re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html):
        table_inner = match.group(2)
        if re.search(r'<caption\b', table_inner, flags=re.IGNORECASE):
            continue
        row_match = re.match(
            r'\s*<tr\b[^>]*>\s*<th\b[^>]*>(.*?)</th>\s*</tr>\s*',
            table_inner,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not row_match:
            continue
        caption_text = re.sub(r'<[^>]+>', '', row_match.group(1)).strip()
        if not caption_text:
            continue
        remaining_rows = table_inner[row_match.end() :].lstrip()
        replacement = f'<table{match.group(1)}><caption>{caption_text}</caption>{remaining_rows}</table>'
        updated = html[: match.start()] + replacement + html[match.end() :]
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': f'Converted the first table header row into a caption: "{caption_text}".',
        }
    return html, None
def _fix_label(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r'<(input|select|textarea)\b(?![^>]*\b(?:aria-label|aria-labelledby)\s*=)([^>]*)>', flags=re.IGNORECASE)
    for match in pattern.finditer(html):
        tag = match.group(1)
        attributes = match.group(2)
        control_id_match = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attributes, flags=re.IGNORECASE)
        control_id = control_id_match.group(1) if control_id_match else None
        if control_id:
            label_pattern = re.compile(rf'<label\b[^>]*\bfor\s*=\s*["\']{re.escape(control_id)}["\'][^>]*>.*?</label>', flags=re.IGNORECASE | re.DOTALL)
            if label_pattern.search(html):
                continue
        label = _guess_accessible_name(attributes)
        replacement = f'<{tag}{attributes} aria-label="{label}">'
        updated = html[: match.start()] + replacement + html[match.end() :]
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': f'Added aria-label="{label}" to an unlabeled form control.',
        }
    return html, None


def _fix_html_xml_lang_mismatch(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    match = re.search(r'<html\b([^>]*)>', html, flags=re.IGNORECASE)
    if not match:
        return html, None
    tag = match.group(0)
    lang_match = re.search(r"\blang\s*=\s*['\"]([^'\"]+)['\"]", tag, flags=re.IGNORECASE)
    xml_lang_match = re.search(r"\bxml:lang\s*=\s*['\"]([^'\"]+)['\"]", tag, flags=re.IGNORECASE)
    preferred = None
    if lang_match and LANG_PATTERN.match(lang_match.group(1)):
        preferred = lang_match.group(1)
    elif xml_lang_match and LANG_PATTERN.match(xml_lang_match.group(1)):
        preferred = xml_lang_match.group(1)
    if not preferred:
        preferred = 'en'
    if not lang_match:
        replacement = tag[:-1] + f' lang="{preferred}">'
    elif not xml_lang_match:
        replacement = tag[:-1] + f' xml:lang="{preferred}">'
    elif lang_match.group(1) == preferred and xml_lang_match.group(1) == preferred:
        return html, None
    else:
        replacement = re.sub(r"(\bxml:lang\s*=\s*['\"])[^'\"]+(['\"])", rf'\g<1>{preferred}\g<2>', tag, flags=re.IGNORECASE)
        replacement = re.sub(r"(\blang\s*=\s*['\"])[^'\"]+(['\"])", rf'\g<1>{preferred}\g<2>', replacement, flags=re.IGNORECASE)
    updated, changed = replace_first(re.escape(tag), replacement, html)
    if not changed:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': f'Synchronized lang and xml:lang to "{preferred}".',
    }


def _fix_valid_lang(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r"(<(?!html\b)[^>]*?\blang\s*=\s*['\"])([^'\"]+)(['\"])", flags=re.IGNORECASE)

    def replacer(match: re.Match[str]) -> str:
        value = match.group(3)
        if LANG_PATTERN.match(value):
            return match.group(0)
        return f'{match.group(1)}en{match.group(3)}'

    updated, changed = replace_first(pattern, replacer, html)
    if not changed or updated == html:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Normalized an invalid language-of-parts lang attribute to "en".',
    }


def _fix_meta_refresh(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    pattern = re.compile(r"\s*<meta\b[^>]*\bhttp-equiv\s*=\s*['\"]refresh['\"][^>]*>\s*", flags=re.IGNORECASE)
    updated, count = pattern.subn('\n', html, count=1)
    if count == 0:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Removed an automatic meta refresh tag.',
    }


def _fix_meta_viewport(html: str, finding: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    viewport_pattern = re.compile(r'<meta\b[^>]*\bname\s*=\s*["\']viewport["\'][^>]*\bcontent\s*=\s*["\']([^"\']*)["\'][^>]*>', flags=re.IGNORECASE)
    match = viewport_pattern.search(html)
    safe_content = 'width=device-width, initial-scale=1'
    if match:
        current = match.group(1)
        if current.strip() == safe_content:
            return html, None
        replacement = match.group(0).replace(current, safe_content, 1)
        updated, changed = replace_first(re.escape(match.group(0)), replacement, html)
        if not changed:
            return html, None
        return updated, {
            'rule_id': finding['rule_id'],
            'changed_target': finding['changed_target'],
            'description': 'Normalized viewport settings to an accessible value.',
        }
    head_match = re.search(r'<head\b[^>]*>', html, flags=re.IGNORECASE)
    if not head_match:
        return html, None
    insertion = f'{head_match.group(0)}\n  <meta name="viewport" content="{safe_content}">'
    updated, changed = replace_first(re.escape(head_match.group(0)), insertion, html)
    if not changed:
        return html, None
    return updated, {
        'rule_id': finding['rule_id'],
        'changed_target': finding['changed_target'],
        'description': 'Inserted an accessible viewport meta tag.',
    }


FIXERS: dict[str, Callable[[str, dict[str, Any]], tuple[str, dict[str, Any] | None]]] = {
    'html-has-lang': _fix_html_has_lang,
    'html-lang-valid': _fix_html_lang_valid,
    'image-alt': _fix_image_alt,
    'input-image-alt': _fix_input_image_alt,
    'area-alt': _fix_area_alt,
    'button-name': _fix_button_name,
    'aria-toggle-field-name': _fix_aria_toggle_field_name,
    'aria-tooltip-name': _fix_aria_tooltip_name,
    'aria-progressbar-name': _fix_aria_progressbar_name,
    'aria-meter-name': _fix_aria_meter_name,
    'aria-required-attr': _fix_aria_required_attr,
    'aria-valid-attr-value': _fix_aria_valid_attr_value,
    'link-name': _fix_link_name,
    'label': _fix_label,
    'select-name': _fix_label,
    'meta-refresh': _fix_meta_refresh,
    'meta-viewport': _fix_meta_viewport,
    'html-xml-lang-mismatch': _fix_html_xml_lang_mismatch,
    'valid-lang': _fix_valid_lang,
    'document-title': _fix_document_title,
    'list': _fix_list,
    'listitem': _fix_listitem,
    'table-fake-caption': _fix_table_fake_caption,
    'td-has-header': _fix_td_has_header,
    'th-has-data-cells': _fix_th_has_data_cells,
}


def apply_report_fixes(
    local_target: Path, report: dict[str, Any], dry_run: bool = False
) -> tuple[dict[str, Any], str]:
    original, source_encoding = _read_text_with_fallback_encoding(local_target)
    updated = original
    applied_changes: list[dict[str, Any]] = []
    fixes_by_finding = {item['finding_id']: item for item in report.get('fixes', [])}

    framework = _detect_framework(local_target, updated)

    for finding in report.get('findings', []):
        helper = FIXERS.get(finding.get('rule_id', ''))
        fix_record = fixes_by_finding.get(finding['id'])
        if helper is None or not fix_record or not fix_record.get('auto_fix_supported'):
            continue
        updated_candidate, change = _apply_framework_fix(updated, finding, framework)
        if change is None or updated_candidate == updated:
            updated_candidate, change = helper(updated, finding)
        if change is None or updated_candidate == updated:
            continue
        updated = updated_candidate
        applied_changes.append(change)
        before_after = {
            'target': finding['changed_target'],
            'before_status': 'open',
            'after_status': 'fixed',
        }
        evidence = {
            'type': 'diff-generated',
            'status': 'implemented',
            'target': finding['changed_target'],
        }
        finding['status'] = 'fixed'
        finding['manual_review_required'] = False
        finding['verification_status'] = 'diff-generated'
        finding['downgrade_reason'] = None
        finding['before_after_targets'] = [before_after]
        fix_record['status'] = 'implemented'
        fix_record['verification_status'] = 'diff-generated'
        fix_record['downgrade_reason'] = None
        fix_record['fix_blockers'] = []
        fix_record['before_after_targets'] = [before_after]
        fix_record.setdefault('verification_evidence', [])
        fix_record['verification_evidence'].append(evidence)

    if updated == original:
        report['run_meta']['notes'].append('No safe auto-fix changes were applied by the core workflow.')
        return report, ''

    if not dry_run:
        _write_text_atomic(local_target, updated, encoding=source_encoding)
    diff = ''.join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(local_target),
            tofile=str(local_target),
        )
    )
    report['run_meta']['files_modified'] = True
    report['run_meta']['modification_owner'] = 'core-workflow'
    report['run_meta'].setdefault('diff_artifacts', []).append({'path': str(local_target), 'type': 'modified-file'})
    if dry_run:
        report['run_meta']['notes'].append(
            f'Projected {len(applied_changes)} safe auto-fix change(s) (--dry-run, no files mutated).'
        )
    else:
        report['run_meta']['notes'].append(
            f'Applied {len(applied_changes)} safe auto-fix change(s) to the local target.'
        )
    report['summary']['fixed_findings'] = sum(1 for item in report['findings'] if item['status'] == 'fixed')
    report['summary']['auto_fixed_count'] = report['summary']['fixed_findings']
    report['summary']['needs_manual_review'] = sum(
        1 for item in report['findings'] if item.get('manual_review_required')
    )
    report['summary']['manual_required_count'] = report['summary']['needs_manual_review']
    report['summary'].setdefault('diff_summary', [])
    report['summary']['diff_summary'].extend(applied_changes)
    report['summary'].setdefault('before_after_targets', [])
    report['summary']['before_after_targets'].extend(
        {
            'finding_id': finding['id'],
            'target': finding['changed_target'],
            'before_status': 'open',
            'after_status': finding['status'],
        }
        for finding in report['findings']
        if finding['status'] == 'fixed'
    )
    report['summary']['fix_blockers'] = [
        item
        for item in report['summary'].get('fix_blockers', [])
        if any(finding['id'] == item.get('finding_id') and finding.get('status') != 'fixed' for finding in report['findings'])
    ]
    report['summary'].setdefault('remediation_lifecycle', {})
    report['summary']['remediation_lifecycle'].update(
        {
            'planned': sum(1 for item in report['fixes'] if item['status'] == 'planned'),
            'implemented': sum(1 for item in report['fixes'] if item['status'] == 'implemented'),
            'verified': sum(1 for item in report['fixes'] if item['status'] == 'verified'),
            'manual_review_required': sum(1 for item in report['fixes'] if item.get('manual_review_required')),
        }
    )
    report['summary']['change_summary'].extend(
        {
            'finding_id': f'FIXED-{index + 1:03d}',
            'rule_id': change['rule_id'],
            'changed_target': change['changed_target'],
            'recommended_action': change['description'],
            'remediation_priority': 'high',
        }
        for index, change in enumerate(applied_changes)
    )
    report['run_meta']['applied_changes'] = applied_changes
    mutation_counts: dict[str, int] = {}
    for change in applied_changes:
        rule_id = change.get('rule_id', 'unknown')
        mutation_counts[rule_id] = mutation_counts.get(rule_id, 0) + 1
    telemetry_key = 'projected_mutation_telemetry' if dry_run else 'mutation_telemetry'
    report['run_meta'][telemetry_key] = [
        {
            'path': str(local_target),
            'rule_id': rule_id,
            'mutation_count': mutation_count,
        }
        for rule_id, mutation_count in sorted(mutation_counts.items())
    ]
    report['run_meta'].setdefault('verification_evidence', [])
    report['run_meta']['verification_evidence'].extend(
        {
            'finding_id': fix['finding_id'],
            'fix_id': fix['id'],
            'type': 'diff-generated',
            'status': fix['verification_status'],
            'target': fix['changed_target'],
        }
        for fix in report['fixes']
        if fix.get('status') == 'implemented'
    )
    return report, diff


def write_diff(diff_text: str, diff_path: Path) -> None:
    if not diff_text:
        return
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(diff_text, encoding='utf-8')


def write_snapshot(report: dict[str, Any], snapshot_path: Path) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
