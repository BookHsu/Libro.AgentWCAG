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


def _colored(text: str, color_key: str) -> str:
    color = _ANSI_COLORS.get(color_key, "")
    reset = _ANSI_COLORS["reset"]
    return f"{color}{text}{reset}" if color else text


def render_terminal(report: dict[str, Any], language: str | None = None) -> str:
    """Render aggregate report for terminal display with ANSI colours."""
    lang = _resolve_language(language)
    lbl = LABELS[lang]
    verdict_lbl = VERDICT_LABELS[lang]
    lines: list[str] = []

    scope = report.get("scope", {})
    severity = report.get("severity", {})
    fixability = report.get("fixability", {})
    targets = report.get("targets", [])
    standard = report.get("standard", {})

    # Title
    title = f"  {lbl['title']}  "
    lines.append("")
    lines.append(_colored(f"{'=' * len(title)}", "header"))
    lines.append(_colored(title, "header"))
    lines.append(_colored(f"{'=' * len(title)}", "header"))
    lines.append("")

    # A1: Scope / Executive Summary
    lines.append(_colored(f"## {lbl['scope']}", "bold"))
    lines.append(f"  {lbl['wcag_standard']}: WCAG {standard.get('wcag_version', '2.1')} {standard.get('conformance_level', 'AA')}")
    lines.append(f"  {lbl['total_targets']}: {scope.get('total_targets', 0)}")
    lines.append(f"  {lbl['clean_targets']}: {scope.get('clean_targets', 0)}")
    lines.append(f"  {lbl['targets_with_issues']}: {scope.get('targets_with_issues', 0)}")
    lines.append(f"  {lbl['total_findings']}: {scope.get('total_findings', 0)}")
    rate = scope.get("compliance_rate", 0)
    lines.append(f"  {lbl['compliance_rate']}: {rate:.0%}")
    verdict = scope.get("verdict", "needs-review")
    verdict_text = verdict_lbl.get(verdict, verdict)
    lines.append(f"  {lbl['verdict']}: {_colored(verdict_text, verdict)}")
    lines.append("")

    # A2: Severity Breakdown
    total_findings = scope.get("total_findings", 0)
    lines.append(_colored(f"## {lbl['severity_breakdown']}", "bold"))
    for level in _SEVERITY_ORDER:
        data = severity.get(level, {})
        count = data.get("count", 0)
        pct = data.get("percentage", 0.0)
        bar = _bar(count, total_findings)
        lines.append(
            f"  {SEVERITY_ICONS.get(level, ' ')} {level:10s} {_colored(bar, level)} {count:4d} ({pct:5.1f}%)"
        )
    lines.append("")

    # A3: Fixability Analysis
    lines.append(_colored(f"## {lbl['fixability_analysis']}", "bold"))
    for level in _FIXABILITY_ORDER:
        data = fixability.get(level, {})
        count = data.get("count", 0) if isinstance(data, dict) else 0
        pct = data.get("percentage", 0.0) if isinstance(data, dict) else 0.0
        bar = _bar(count, total_findings)
        lines.append(f"  {level:10s} {bar} {count:4d} ({pct:5.1f}%)")
    fix_cov = fixability.get("fix_coverage", 0)
    if isinstance(fix_cov, (int, float)):
        lines.append(f"  {lbl['fix_coverage']}: {fix_cov:.0%}")
    lines.append("")

    # A5: WCAG Principle Coverage
    wcag_principles = report.get("wcag_principles", {})
    if wcag_principles:
        lines.append(_colored(f"## {lbl['wcag_principles']}", "bold"))
        for principle, data in wcag_principles.items():
            count = data.get("count", 0)
            sc_list = ", ".join(data.get("sc", []))
            bar = _bar(count, total_findings)
            lines.append(f"  {principle:15s} {bar} {count:4d}  SC: {sc_list or '-'}")
        lines.append("")

    # A6: Top Issues
    top_rules = report.get("top_rules", [])
    if top_rules:
        lines.append(_colored(f"## {lbl['top_issues']}", "bold"))
        lines.append(f"  {lbl['rule_id']:25s} {lbl['count']:>6s}  {lbl['sc']}")
        lines.append(f"  {'-' * 25} {'-' * 6}  {'-' * 20}")
        for rule in top_rules:
            sc_text = ", ".join(rule.get("sc", []))
            lines.append(f"  {rule.get('rule_id', '?'):25s} {rule.get('count', 0):6d}  {sc_text}")
        lines.append("")

    # A4: Per-Target Breakdown
    lines.append(_colored(f"## {lbl['per_target']}", "bold"))
    if targets:
        # Header
        lines.append(f"  {'':2s} {lbl['target']:40s} {lbl['findings']:>8s} {lbl['auto_fixable']:>12s} {lbl['status']:>8s}")
        lines.append(f"  {'':2s} {'-' * 40} {'-' * 8} {'-' * 12} {'-' * 8}")
        for t in targets:
            status = t.get("status", "issues")
            icon = TARGET_STATUS_ICONS.get(status, "?")
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

    scope = report.get("scope", {})
    severity = report.get("severity", {})
    fixability = report.get("fixability", {})
    targets = report.get("targets", [])
    standard = report.get("standard", {})
    remediation = report.get("remediation_lifecycle", {})
    auto_fix = report.get("auto_fix_opportunity", {})

    # Title
    lines.append(f"# {lbl['title']}")
    lines.append("")
    lines.append(f"> {lbl['wcag_standard']}: WCAG {standard.get('wcag_version', '2.1')} {standard.get('conformance_level', 'AA')}")
    lines.append(f"> {lbl['generated_at']}: {report.get('generated_at', 'N/A')}")
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
        if isinstance(data, dict):
            lines.append(
                f"| {level} | {data.get('count', 0)} | {data.get('percentage', 0.0):.1f}% |"
            )
    fix_cov = fixability.get("fix_coverage", 0)
    if isinstance(fix_cov, (int, float)):
        lines.append("")
        lines.append(f"{lbl['fix_coverage']}: **{fix_cov:.0%}**")
    lines.append("")

    # A5: WCAG Principle Coverage
    wcag_principles = report.get("wcag_principles", {})
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
    top_rules = report.get("top_rules", [])
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
            sev_parts = []
            for sl in _SEVERITY_ORDER:
                c = t.get("severity", {}).get(sl, 0)
                if c > 0:
                    sev_parts.append(f"{SEVERITY_ICONS.get(sl, '')} {c}")
            sev_detail = " ".join(sev_parts) if sev_parts else "-"
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
    baseline_diff = report.get("baseline_diff")
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
