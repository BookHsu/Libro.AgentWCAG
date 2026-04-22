#!/usr/bin/env python3
"""Renderers for aggregate WCAG reports.

Implements TODO items B2, B3, and B5 from 20260328_report_todo.md:
  B2: Terminal output with colour, bar charts, severity icons
  B3: Markdown output with tables, emoji markers, <details> folds
  B5: CSV output with one finding per row
"""

from __future__ import annotations

from typing import Any

SEVERITY_ICONS = {
    "critical": "\U0001f534",   # 🔴
    "serious": "\U0001f7e0",    # 🟠
    "moderate": "\U0001f7e1",   # 🟡
    "minor": "\U0001f535",      # 🔵
    "info": "\u26aa",           # ⚪
}

TARGET_STATUS_ICONS = {
    "clean": "\u2713",      # ✓
    "issues": "\u26a0",     # ⚠
    "critical": "\u2717",   # ✗
}
PLAIN_SEVERITY_MARKERS = {
    "critical": "[critical]",
    "serious": "[serious]",
    "moderate": "[moderate]",
    "minor": "[minor]",
    "info": "[info]",
}
PLAIN_TARGET_STATUS_MARKERS = {
    "clean": "OK",
    "issues": "WARN",
    "critical": "FAIL",
}

LABELS = {
    "en": {
        "title": "WCAG Aggregate Report",
        "scope": "Scope",
        "total_targets": "Total targets",
        "targets_with_issues": "Targets with issues",
        "clean_targets": "Clean targets",
        "total_findings": "Total findings",
        "compliance_rate": "Compliance rate",
        "verdict": "Verdict",
        "severity_breakdown": "Severity Breakdown",
        "fixability_analysis": "Fixability Analysis",
        "fix_coverage": "Auto-fix coverage",
        "per_target": "Per-Target Breakdown",
        "target": "Target",
        "findings": "Findings",
        "auto_fixable": "Auto-fixable",
        "status": "Status",
        "auto_fix_opportunity": "Auto-Fix Opportunity",
        "fixable_count": "Fixable findings",
        "estimated_residual": "Estimated residual",
        "command": "Suggested command",
        "remediation": "Remediation Lifecycle",
        "planned": "Planned",
        "implemented": "Implemented",
        "verified": "Verified",
        "manual_review": "Manual review required",
        "wcag_standard": "WCAG standard",
        "generated_at": "Generated at",
        "wcag_principles": "WCAG Principle Coverage",
        "top_issues": "Top Issues",
        "rule_id": "Rule",
        "count": "Count",
        "sc": "SC",
    },
    "zh-TW": {
        "title": "WCAG 彙總報告",
        "scope": "總覽",
        "total_targets": "掃描目標數",
        "targets_with_issues": "有問題的目標",
        "clean_targets": "無問題的目標",
        "total_findings": "總缺失數",
        "compliance_rate": "合規率",
        "verdict": "結論",
        "severity_breakdown": "嚴重度分級",
        "fixability_analysis": "可修正性分析",
        "fix_coverage": "自動修正覆蓋率",
        "per_target": "各目標明細",
        "target": "目標",
        "findings": "缺失數",
        "auto_fixable": "可自動修正",
        "status": "狀態",
        "auto_fix_opportunity": "自動修正機會",
        "fixable_count": "可修正缺失",
        "estimated_residual": "預估殘餘缺失",
        "command": "建議指令",
        "remediation": "修復生命週期",
        "planned": "已計畫",
        "implemented": "已實作",
        "verified": "已驗證",
        "manual_review": "需人工審核",
        "wcag_standard": "WCAG 標準",
        "generated_at": "產生時間",
        "wcag_principles": "WCAG 原則涵蓋分析",
        "top_issues": "熱點分析",
        "rule_id": "規則",
        "count": "數量",
        "sc": "SC",
    },
}

VERDICT_LABELS = {
    "en": {"pass": "PASS", "fail": "FAIL", "needs-review": "NEEDS REVIEW"},
    "zh-TW": {"pass": "通過", "fail": "不通過", "needs-review": "需要審查"},
}

_BAR_WIDTH = 30
_SEVERITY_ORDER = ("critical", "serious", "moderate", "minor", "info")
_FIXABILITY_ORDER = ("auto-fix", "assisted", "manual")


def _resolve_language(language: str | None) -> str:
    if language and language.lower().startswith("en"):
        return "en"
    return "zh-TW"


def _extract_report_sections(report: dict[str, Any]) -> dict[str, Any]:
    """Extract common sections from an aggregate report dict.

    Centralises the .get() fallback pattern so each renderer does not
    repeat it.  The returned dict has guaranteed keys with safe defaults.
    """
    return {
        "scope": report.get("scope", {}),
        "severity": report.get("severity", {}),
        "fixability": report.get("fixability", {}),
        "targets": report.get("targets", []),
        "standard": report.get("standard", {}),
        "wcag_principles": report.get("wcag_principles", {}),
        "top_rules": report.get("top_rules", []),
        "remediation": report.get("remediation_lifecycle", {}),
        "auto_fix": report.get("auto_fix_opportunity", {}),
        "baseline_diff": report.get("baseline_diff"),
        "generated_at": report.get("generated_at", "N/A"),
    }


# ---------------------------------------------------------------------------
# B2: Terminal renderer
# ---------------------------------------------------------------------------

_ANSI_COLORS = {
    "critical": "\033[91m",  # red
    "serious": "\033[93m",   # yellow
    "moderate": "\033[33m",  # dark yellow
    "minor": "\033[94m",     # blue
    "info": "\033[90m",      # grey
    "pass": "\033[92m",      # green
    "fail": "\033[91m",      # red
    "needs-review": "\033[93m",  # yellow
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "header": "\033[1;36m",  # bold cyan
}


def _bar(count: int, total: int, width: int = _BAR_WIDTH) -> str:
    if total == 0:
        return " " * width
    filled = round(count / total * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def _render_bar(count: int, total: int, *, use_color: bool, width: int = _BAR_WIDTH) -> str:
    if use_color:
        return _bar(count, total, width)
    if total == 0:
        return " " * width
    filled = round(count / total * width)
    return "#" * filled + "-" * (width - filled)


def _severity_marker(level: str, *, use_color: bool) -> str:
    if use_color:
        return SEVERITY_ICONS.get(level, " ")
    return PLAIN_SEVERITY_MARKERS.get(level, f"[{level}]")


def _target_status_marker(status: str, *, use_color: bool) -> str:
    if use_color:
        return TARGET_STATUS_ICONS.get(status, "?")
    return PLAIN_TARGET_STATUS_MARKERS.get(status, status.upper())


def _colored(text: str, color_key: str, *, use_color: bool = True) -> str:
    if not use_color:
        return text
    color = _ANSI_COLORS.get(color_key, "")
    reset = _ANSI_COLORS["reset"]
    return f"{color}{text}{reset}" if color else text


def render_terminal(report: dict[str, Any], language: str | None = None, *, use_color: bool = True) -> str:
    """Render aggregate report for terminal display with ANSI colours."""
    lang = _resolve_language(language)
    lbl = LABELS[lang]
    verdict_lbl = VERDICT_LABELS[lang]
    lines: list[str] = []

    sec = _extract_report_sections(report)
    scope = sec["scope"]
    severity = sec["severity"]
    fixability = sec["fixability"]
    targets = sec["targets"]
    standard = sec["standard"]

    # Title
    title = f"  {lbl['title']}  "
    lines.append("")
    lines.append(_colored(f"{'=' * len(title)}", "header", use_color=use_color))
    lines.append(_colored(title, "header", use_color=use_color))
    lines.append(_colored(f"{'=' * len(title)}", "header", use_color=use_color))
    lines.append("")

    # A1: Scope / Executive Summary
    lines.append(_colored(f"## {lbl['scope']}", "bold", use_color=use_color))
    lines.append(f"  {lbl['wcag_standard']}: WCAG {standard.get('wcag_version', '2.1')} {standard.get('conformance_level', 'AA')}")
    lines.append(f"  {lbl['total_targets']}: {scope.get('total_targets', 0)}")
    lines.append(f"  {lbl['clean_targets']}: {scope.get('clean_targets', 0)}")
    lines.append(f"  {lbl['targets_with_issues']}: {scope.get('targets_with_issues', 0)}")
    lines.append(f"  {lbl['total_findings']}: {scope.get('total_findings', 0)}")
    rate = scope.get("compliance_rate", 0)
    lines.append(f"  {lbl['compliance_rate']}: {rate:.0%}")
    verdict = scope.get("verdict", "needs-review")
    verdict_text = verdict_lbl.get(verdict, verdict)
    lines.append(f"  {lbl['verdict']}: {_colored(verdict_text, verdict, use_color=use_color)}")
    lines.append("")

    # A2: Severity Breakdown
    total_findings = scope.get("total_findings", 0)
    lines.append(_colored(f"## {lbl['severity_breakdown']}", "bold", use_color=use_color))
    for level in _SEVERITY_ORDER:
        data = severity.get(level, {})
        count = data.get("count", 0)
        pct = data.get("percentage", 0.0)
        bar = _render_bar(count, total_findings, use_color=use_color)
        lines.append(
            f"  {_severity_marker(level, use_color=use_color)} {level:10s} {_colored(bar, level, use_color=use_color)} {count:4d} ({pct:5.1f}%)"
        )
    lines.append("")

    # A3: Fixability Analysis
    lines.append(_colored(f"## {lbl['fixability_analysis']}", "bold", use_color=use_color))
    for level in _FIXABILITY_ORDER:
        data = fixability.get(level, {})
        count = data.get("count", 0)
        pct = data.get("percentage", 0.0)
        bar = _render_bar(count, total_findings, use_color=use_color)
        lines.append(f"  {level:10s} {bar} {count:4d} ({pct:5.1f}%)")
    auto_fix_pct = fixability.get("auto-fix", {}).get("percentage", 0.0)
    lines.append(f"  {lbl['fix_coverage']}: {auto_fix_pct / 100:.0%}")
    lines.append("")

    # A5: WCAG Principle Coverage
    wcag_principles = sec["wcag_principles"]
    if wcag_principles:
        lines.append(_colored(f"## {lbl['wcag_principles']}", "bold", use_color=use_color))
        for principle, data in wcag_principles.items():
            count = data.get("count", 0)
            sc_list = ", ".join(data.get("sc", []))
            bar = _render_bar(count, total_findings, use_color=use_color)
            lines.append(f"  {principle:15s} {bar} {count:4d}  SC: {sc_list or '-'}")
        lines.append("")

    # A6: Top Issues
    top_rules = sec["top_rules"]
    if top_rules:
        lines.append(_colored(f"## {lbl['top_issues']}", "bold", use_color=use_color))
        lines.append(f"  {lbl['rule_id']:25s} {lbl['count']:>6s}  {lbl['sc']}")
        lines.append(f"  {'-' * 25} {'-' * 6}  {'-' * 20}")
        for rule in top_rules:
            sc_text = ", ".join(rule.get("sc", []))
            lines.append(f"  {rule.get('rule_id', '?'):25s} {rule.get('count', 0):6d}  {sc_text}")
        lines.append("")

    # A4: Per-Target Breakdown
    lines.append(_colored(f"## {lbl['per_target']}", "bold", use_color=use_color))
    if targets:
        # Header
        lines.append(f"  {'':2s} {lbl['target']:40s} {lbl['findings']:>8s} {lbl['auto_fixable']:>12s} {lbl['status']:>8s}")
        lines.append(f"  {'':2s} {'-' * 40} {'-' * 8} {'-' * 12} {'-' * 8}")
        for t in targets:
            status = t.get("status", "issues")
            icon = _target_status_marker(status, use_color=use_color)
            target_name = t.get("target", "?")
            if len(target_name) > 40:
                target_name = "..." + target_name[-37:]
            lines.append(
                f"  {icon:2s} {target_name:40s} {t.get('total_findings', 0):8d} {t.get('auto_fixable', 0):12d} {status:>8s}"
            )
    lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# B3: Markdown renderer
# ---------------------------------------------------------------------------

def render_markdown(report: dict[str, Any], language: str | None = None) -> str:
    """Render aggregate report as GitHub-flavoured Markdown."""
    lang = _resolve_language(language)
    lbl = LABELS[lang]
    verdict_lbl = VERDICT_LABELS[lang]
    lines: list[str] = []

    sec = _extract_report_sections(report)
    scope = sec["scope"]
    severity = sec["severity"]
    fixability = sec["fixability"]
    targets = sec["targets"]
    standard = sec["standard"]
    remediation = sec["remediation"]
    auto_fix = sec["auto_fix"]

    # Title
    lines.append(f"# {lbl['title']}")
    lines.append("")
    lines.append(f"> {lbl['wcag_standard']}: WCAG {standard.get('wcag_version', '2.1')} {standard.get('conformance_level', 'AA')}")
    lines.append(f"> {lbl['generated_at']}: {sec['generated_at']}")
    lines.append("")

    # A1: Scope
    verdict = scope.get("verdict", "needs-review")
    verdict_text = verdict_lbl.get(verdict, verdict)
    rate = scope.get("compliance_rate", 0)
    lines.append(f"## {lbl['scope']}")
    lines.append("")
    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| {lbl['total_targets']} | {scope.get('total_targets', 0)} |")
    lines.append(f"| {lbl['clean_targets']} | {scope.get('clean_targets', 0)} |")
    lines.append(f"| {lbl['targets_with_issues']} | {scope.get('targets_with_issues', 0)} |")
    lines.append(f"| {lbl['total_findings']} | {scope.get('total_findings', 0)} |")
    lines.append(f"| {lbl['compliance_rate']} | {rate:.0%} |")
    lines.append(f"| {lbl['verdict']} | **{verdict_text}** |")
    lines.append("")

    # A2: Severity
    lines.append(f"## {lbl['severity_breakdown']}")
    lines.append("")
    lines.append(f"| | Level | Count | % |")
    lines.append(f"|---|---|---:|---:|")
    for level in _SEVERITY_ORDER:
        data = severity.get(level, {})
        icon = SEVERITY_ICONS.get(level, "")
        lines.append(
            f"| {icon} | {level} | {data.get('count', 0)} | {data.get('percentage', 0.0):.1f}% |"
        )
    lines.append("")

    # A3: Fixability
    lines.append(f"## {lbl['fixability_analysis']}")
    lines.append("")
    lines.append(f"| Level | Count | % |")
    lines.append(f"|---|---:|---:|")
    for level in _FIXABILITY_ORDER:
        data = fixability.get(level, {})
        lines.append(
            f"| {level} | {data.get('count', 0)} | {data.get('percentage', 0.0):.1f}% |"
        )
    auto_fix_pct = fixability.get("auto-fix", {}).get("percentage", 0.0)
    lines.append("")
    lines.append(f"{lbl['fix_coverage']}: **{auto_fix_pct / 100:.0%}**")
    lines.append("")

    # A5: WCAG Principle Coverage
    wcag_principles = sec["wcag_principles"]
    if wcag_principles:
        lines.append(f"## {lbl['wcag_principles']}")
        lines.append("")
        lines.append(f"| Principle | Count | SC |")
        lines.append(f"|---|---:|---|")
        for principle, data in wcag_principles.items():
            sc_text = ", ".join(data.get("sc", []))
            lines.append(f"| {principle} | {data.get('count', 0)} | {sc_text or '-'} |")
        lines.append("")

    # A6: Top Issues
    top_rules = sec["top_rules"]
    if top_rules:
        lines.append(f"## {lbl['top_issues']}")
        lines.append("")
        lines.append(f"| {lbl['rule_id']} | {lbl['count']} | Fixability | SC |")
        lines.append(f"|---|---:|---|---|")
        for rule in top_rules:
            sc_text = ", ".join(rule.get("sc", []))
            lines.append(
                f"| `{rule.get('rule_id', '?')}` | {rule.get('count', 0)} | {rule.get('fixability', 'manual')} | {sc_text} |"
            )
        lines.append("")

    # A4: Per-Target
    lines.append(f"## {lbl['per_target']}")
    lines.append("")
    if targets:
        lines.append(f"| | {lbl['target']} | {lbl['findings']} | {lbl['auto_fixable']} | {lbl['status']} |")
        lines.append(f"|---|---|---:|---:|---|")
        for t in targets:
            status = t.get("status", "issues")
            icon = TARGET_STATUS_ICONS.get(status, "?")
            lines.append(
                f"| {icon} | `{t.get('target', '?')}` | {t.get('total_findings', 0)} | {t.get('auto_fixable', 0)} | {status} |"
            )
        # Fold per-target severity details
        lines.append("")
        lines.append(f"<details><summary>{lbl['severity_breakdown']}</summary>")
        lines.append("")
        for t in targets:
            if t.get("total_findings", 0) == 0:
                continue
            lines.append(f"### `{t.get('target', '?')}`")
            lines.append("")
            for sl in _SEVERITY_ORDER:
                c = t.get("severity", {}).get(sl, 0)
                if c > 0:
                    lines.append(f"- {SEVERITY_ICONS.get(sl, '')} {sl}: {c}")
            lines.append("")
        lines.append("</details>")
    lines.append("")

    # Remediation lifecycle
    if remediation:
        lines.append(f"## {lbl['remediation']}")
        lines.append("")
        lines.append(f"| | |")
        lines.append(f"|---|---:|")
        lines.append(f"| {lbl['planned']} | {remediation.get('planned', 0)} |")
        lines.append(f"| {lbl['implemented']} | {remediation.get('implemented', 0)} |")
        lines.append(f"| {lbl['verified']} | {remediation.get('verified', 0)} |")
        lines.append(f"| {lbl['manual_review']} | {remediation.get('manual_review_required', 0)} |")
        lines.append("")

    # Auto-fix opportunity
    if auto_fix:
        lines.append(f"## {lbl['auto_fix_opportunity']}")
        lines.append("")
        lines.append(f"- {lbl['fixable_count']}: **{auto_fix.get('fixable_count', 0)}**")
        lines.append(f"- {lbl['estimated_residual']}: **{auto_fix.get('estimated_residual', 0)}**")
        lines.append(f"- {lbl['command']}: `{auto_fix.get('command', '')}`")
        lines.append("")

    # A9: Baseline diff
    baseline_diff = sec["baseline_diff"]
    if baseline_diff:
        lines.append("## Baseline Diff")
        lines.append("")
        lines.append("| | |")
        lines.append("|---|---:|")
        lines.append(f"| New findings | {baseline_diff.get('new_count', 0)} |")
        lines.append(f"| Resolved | {baseline_diff.get('resolved_count', 0)} |")
        lines.append(f"| Persistent | {baseline_diff.get('persistent_count', 0)} |")
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# B5: CSV renderer
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "target",
    "rule_id",
    "severity",
    "fixability",
    "sc",
    "status",
    "source",
    "current",
    "changed_target",
]


def _csv_escape(value: str) -> str:
    """Escape a value for CSV (RFC 4180)."""
    if any(c in value for c in (",", '"', "\n", "\r")):
        return '"' + value.replace('"', '""') + '"'
    return value


def render_csv(
    reports: list[dict],
    aggregate: dict[str, Any] | None = None,
) -> str:
    """Render per-finding CSV from the original reports (not the aggregate).

    Each row represents one finding with its target context.
    If only the aggregate is passed (no original reports), extracts what it can.
    """
    lines: list[str] = [",".join(_CSV_COLUMNS)]

    for report in reports:
        target = report.get("target", {}).get("value", "")
        for finding in report.get("findings", []):
            row = [
                _csv_escape(target),
                _csv_escape(finding.get("rule_id", "")),
                finding.get("severity", ""),
                finding.get("fixability", ""),
                _csv_escape(";".join(finding.get("sc", []))),
                finding.get("status", ""),
                finding.get("source", ""),
                _csv_escape(finding.get("current", "")),
                _csv_escape(finding.get("changed_target", "")),
            ]
            lines.append(",".join(row))

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# B6: Badge renderer (Shields.io endpoint JSON)
# ---------------------------------------------------------------------------

def render_badge(report: dict[str, Any]) -> str:
    """Render a Shields.io endpoint JSON badge based on compliance rate.

    Output format follows https://shields.io/endpoint.
    Colour changes by compliance rate: green >=90%, yellow >=50%, red <50%.
    """
    import json as json_mod

    scope = report.get("scope", {})
    rate = scope.get("compliance_rate", 0)
    total = scope.get("total_findings", 0)

    if rate >= 0.9:
        color = "brightgreen"
    elif rate >= 0.5:
        color = "yellow"
    else:
        color = "red"

    badge = {
        "schemaVersion": 1,
        "label": "WCAG",
        "message": f"{rate:.0%} ({total} findings)",
        "color": color,
    }
    return json_mod.dumps(badge, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------
# B4: HTML Dashboard renderer
# ---------------------------------------------------------------------------

_SEVERITY_COLORS_HEX = {
    "critical": "#e53e3e",
    "serious": "#dd6b20",
    "moderate": "#d69e2e",
    "minor": "#3182ce",
    "info": "#a0aec0",
}

_FIXABILITY_COLORS_HEX = {
    "auto-fix": "#38a169",
    "assisted": "#d69e2e",
    "manual": "#e53e3e",
}

_STATUS_COLORS_HEX = {
    "clean": "#38a169",
    "issues": "#d69e2e",
    "critical": "#e53e3e",
}

_STATUS_HTML_ENTITIES = {
    "clean": "&#x2713;",
    "issues": "&#x26a0;",
    "critical": "&#x2717;",
}

_VERDICT_COLORS_HEX = {
    "pass": "#38a169",
    "fail": "#e53e3e",
    "needs-review": "#d69e2e",
}


def _svg_bar_chart(data: dict[str, int], colors: dict[str, str], width: int = 400, bar_height: int = 28) -> str:
    """Generate an inline SVG horizontal bar chart."""
    total = sum(data.values()) or 1
    lines: list[str] = []
    height = len(data) * (bar_height + 8) + 10
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    y = 5
    for label, count in data.items():
        bar_w = max(1, int(count / total * (width - 120)))
        color = colors.get(label, "#718096")
        pct = count / total * 100
        lines.append(f'  <text x="0" y="{y + bar_height - 8}" font-size="13" fill="#2d3748">{label}</text>')
        lines.append(f'  <rect x="90" y="{y}" width="{bar_w}" height="{bar_height - 4}" rx="3" fill="{color}" />')
        lines.append(f'  <text x="{90 + bar_w + 5}" y="{y + bar_height - 8}" font-size="12" fill="#4a5568">{count} ({pct:.0f}%)</text>')
        y += bar_height + 8
    lines.append('</svg>')
    return "\n".join(lines)


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_html(report: dict[str, Any], language: str | None = None) -> str:
    """Render a self-contained HTML dashboard (B4).

    Single file with inline CSS + inline SVG charts, zero external dependencies.
    """
    lang = _resolve_language(language)
    lbl = LABELS[lang]
    verdict_lbl = VERDICT_LABELS[lang]

    sec = _extract_report_sections(report)
    scope = sec["scope"]
    severity = sec["severity"]
    fixability = sec["fixability"]
    targets = sec["targets"]
    standard = sec["standard"]
    wcag_principles = sec["wcag_principles"]
    top_rules = sec["top_rules"]
    remediation = sec["remediation"]
    auto_fix = sec["auto_fix"]
    baseline_diff = sec["baseline_diff"]

    rate = scope.get("compliance_rate", 0)
    verdict = scope.get("verdict", "needs-review")
    verdict_text = verdict_lbl.get(verdict, verdict)
    verdict_color = _VERDICT_COLORS_HEX.get(verdict, "#718096")

    # Severity bar chart data
    sev_data = {level: severity.get(level, {}).get("count", 0) for level in _SEVERITY_ORDER}
    sev_chart = _svg_bar_chart(sev_data, _SEVERITY_COLORS_HEX)

    # Fixability bar chart data
    fix_data = {level: fixability.get(level, {}).get("count", 0) for level in _FIXABILITY_ORDER}
    fix_chart = _svg_bar_chart(fix_data, _FIXABILITY_COLORS_HEX)

    # Build target rows
    target_rows: list[str] = []
    for t in targets:
        status = t.get("status", "issues")
        status_icon = _STATUS_HTML_ENTITIES.get(status, "?")
        status_color = _STATUS_COLORS_HEX.get(status, "#718096")
        target_rows.append(
            f'<tr>'
            f'<td style="color:{status_color}">{status_icon}</td>'
            f'<td><code>{_html_escape(t.get("target", "?"))}</code></td>'
            f'<td style="text-align:right">{t.get("total_findings", 0)}</td>'
            f'<td style="text-align:right">{t.get("auto_fixable", 0)}</td>'
            f'<td style="color:{status_color}">{status}</td>'
            f'</tr>'
        )

    # Top rules rows
    rule_rows: list[str] = []
    for rule in top_rules[:10]:
        sc_text = ", ".join(rule.get("sc", []))
        rule_rows.append(
            f'<tr>'
            f'<td><code>{_html_escape(rule.get("rule_id", ""))}</code></td>'
            f'<td style="text-align:right">{rule.get("count", 0)}</td>'
            f'<td>{rule.get("fixability", "manual")}</td>'
            f'<td>{sc_text}</td>'
            f'</tr>'
        )

    # Baseline diff section
    baseline_html = ""
    if baseline_diff:
        baseline_html = f"""
    <section>
      <h2>Baseline Diff</h2>
      <table><tbody>
        <tr><td>New findings</td><td style="text-align:right">{baseline_diff.get("new_count", 0)}</td></tr>
        <tr><td>Resolved</td><td style="text-align:right">{baseline_diff.get("resolved_count", 0)}</td></tr>
        <tr><td>Persistent</td><td style="text-align:right">{baseline_diff.get("persistent_count", 0)}</td></tr>
      </tbody></table>
    </section>"""

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{lbl['title']}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 960px; margin: 0 auto; padding: 24px; color: #2d3748; background: #f7fafc; }}
  h1 {{ font-size: 1.8em; margin-bottom: 8px; color: #1a202c; }}
  h2 {{ font-size: 1.3em; margin: 24px 0 12px; color: #2d3748; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; }}
  .meta {{ color: #718096; font-size: 0.9em; margin-bottom: 20px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }}
  .card {{ background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
  .card .value {{ font-size: 2em; font-weight: bold; }}
  .card .label {{ font-size: 0.85em; color: #718096; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
  th, td {{ padding: 8px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 0.95em; }}
  th {{ background: #edf2f7; font-weight: 600; }}
  code {{ background: #edf2f7; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
  section {{ margin-bottom: 24px; }}
  svg {{ display: block; margin: 8px 0; }}
  .verdict {{ display: inline-block; padding: 4px 12px; border-radius: 4px; color: #fff; font-weight: bold; }}
</style>
</head>
<body>
  <h1>{lbl['title']}</h1>
  <p class="meta">WCAG {standard.get('wcag_version', '2.1')} {standard.get('conformance_level', 'AA')} &middot; {sec['generated_at']}</p>

  <section>
    <h2>{lbl['scope']}</h2>
    <div class="cards">
      <div class="card"><div class="value">{scope.get('total_targets', 0)}</div><div class="label">{lbl['total_targets']}</div></div>
      <div class="card"><div class="value">{scope.get('clean_targets', 0)}</div><div class="label">{lbl['clean_targets']}</div></div>
      <div class="card"><div class="value">{scope.get('total_findings', 0)}</div><div class="label">{lbl['total_findings']}</div></div>
      <div class="card"><div class="value">{rate:.0%}</div><div class="label">{lbl['compliance_rate']}</div></div>
      <div class="card"><div class="value verdict" style="background:{verdict_color}">{verdict_text}</div><div class="label">{lbl['verdict']}</div></div>
    </div>
  </section>

  <section>
    <h2>{lbl['severity_breakdown']}</h2>
    {sev_chart}
  </section>

  <section>
    <h2>{lbl['fixability_analysis']}</h2>
    {fix_chart}
  </section>

  <section>
    <h2>{lbl['per_target']}</h2>
    <table>
      <thead><tr><th></th><th>{lbl['target']}</th><th style="text-align:right">{lbl['findings']}</th><th style="text-align:right">{lbl['auto_fixable']}</th><th>{lbl['status']}</th></tr></thead>
      <tbody>{''.join(target_rows)}</tbody>
    </table>
  </section>

  <section>
    <h2>{lbl['top_issues']}</h2>
    <table>
      <thead><tr><th>{lbl['rule_id']}</th><th style="text-align:right">{lbl['count']}</th><th>Fixability</th><th>SC</th></tr></thead>
      <tbody>{''.join(rule_rows)}</tbody>
    </table>
  </section>

  <section>
    <h2>{lbl['remediation']}</h2>
    <div class="cards">
      <div class="card"><div class="value">{remediation.get('planned', 0)}</div><div class="label">{lbl['planned']}</div></div>
      <div class="card"><div class="value">{remediation.get('implemented', 0)}</div><div class="label">{lbl['implemented']}</div></div>
      <div class="card"><div class="value">{remediation.get('verified', 0)}</div><div class="label">{lbl['verified']}</div></div>
      <div class="card"><div class="value">{remediation.get('manual_review_required', 0)}</div><div class="label">{lbl['manual_review']}</div></div>
    </div>
  </section>

  <section>
    <h2>{lbl['auto_fix_opportunity']}</h2>
    <p>{lbl['fixable_count']}: <strong>{auto_fix.get('fixable_count', 0)}</strong> &middot;
       {lbl['estimated_residual']}: <strong>{auto_fix.get('estimated_residual', 0)}</strong></p>
    <p>{lbl['command']}: <code>{_html_escape(auto_fix.get('command', ''))}</code></p>
  </section>
{baseline_html}
  <footer style="margin-top:40px;padding-top:16px;border-top:1px solid #e2e8f0;color:#a0aec0;font-size:0.8em;">
    Generated by Libro.AgentWCAG
  </footer>
</body>
</html>
"""
    return html
