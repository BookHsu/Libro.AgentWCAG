#!/usr/bin/env python3
"""Safe first-pass auto remediation helpers for local HTML files."""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import url2pathname

from rewrite_helpers import replace_first

LANG_PATTERN = re.compile(r'^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$')


def target_to_local_path(target: str) -> Path | None:
    candidate = Path(target)
    if candidate.exists():
        return candidate.resolve()
    parsed = urlparse(target)
    if parsed.scheme == 'file' and parsed.netloc in {'', 'localhost'}:
        return Path(url2pathname(parsed.path)).resolve()
    return None


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
    'link-name': _fix_link_name,
    'label': _fix_label,
    'select-name': _fix_label,
    'meta-refresh': _fix_meta_refresh,
    'meta-viewport': _fix_meta_viewport,
    'html-xml-lang-mismatch': _fix_html_xml_lang_mismatch,
    'valid-lang': _fix_valid_lang,
    'document-title': _fix_document_title,
}


def apply_report_fixes(local_target: Path, report: dict[str, Any]) -> tuple[dict[str, Any], str]:
    original = local_target.read_text(encoding='utf-8')
    updated = original
    applied_changes: list[dict[str, Any]] = []
    fixes_by_finding = {item['finding_id']: item for item in report.get('fixes', [])}

    for finding in report.get('findings', []):
        helper = FIXERS.get(finding.get('rule_id', ''))
        fix_record = fixes_by_finding.get(finding['id'])
        if helper is None or not fix_record or not fix_record.get('auto_fix_supported'):
            continue
        updated_candidate, change = helper(updated, finding)
        if change is None or updated_candidate == updated:
            continue
        updated = updated_candidate
        applied_changes.append(change)
        finding['status'] = 'fixed'
        finding['manual_review_required'] = False
        finding['verification_status'] = 'diff-generated'
        finding['before_after_targets'] = {
            'before_target': finding.get('changed_target'),
            'after_target': finding.get('changed_target'),
        }
        fix_record['status'] = 'implemented'
        fix_record['verification_status'] = 'diff-generated'
        fix_record['before_after_targets'] = {
            'before_target': finding.get('changed_target'),
            'after_target': finding.get('changed_target'),
        }
        fix_record['verification_evidence'] = {
            'status': 'diff-generated',
            'method': 'unified-diff',
            'artifacts': [{'type': 'modified-file', 'path': str(local_target)}],
        }

    if updated == original:
        report['run_meta']['notes'].append('No safe auto-fix changes were applied by the core workflow.')
        return report, ''

    local_target.write_text(updated, encoding='utf-8')
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
    report['run_meta'].setdefault('verification_evidence', []).append(
        {
            'status': 'diff-generated',
            'method': 'unified-diff',
            'artifact': {'type': 'modified-file', 'path': str(local_target)},
            'before_after_targets': [
                {
                    'rule_id': change['rule_id'],
                    'before_target': change['changed_target'],
                    'after_target': change['changed_target'],
                }
                for change in applied_changes
            ],
        }
    )
    report['run_meta']['notes'].append(f'Applied {len(applied_changes)} safe auto-fix change(s) to the local target.')
    report['summary']['fixed_findings'] = sum(1 for item in report['findings'] if item['status'] == 'fixed')
    report['summary']['auto_fixed_count'] = report['summary']['fixed_findings']
    report['summary']['needs_manual_review'] = sum(
        1 for item in report['findings'] if item.get('manual_review_required')
    )
    report['summary']['manual_required_count'] = report['summary']['needs_manual_review']
    report['summary'].setdefault('diff_summary', [])
    report['summary']['diff_summary'].extend(applied_changes)
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
    return report, diff


def write_diff(diff_text: str, diff_path: Path) -> None:
    if not diff_text:
        return
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(diff_text, encoding='utf-8')


def write_snapshot(report: dict[str, Any], snapshot_path: Path) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


