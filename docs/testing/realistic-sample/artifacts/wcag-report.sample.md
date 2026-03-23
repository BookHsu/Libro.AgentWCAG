Execution mode: apply-fixes
Task mode: modify
Files modified by core workflow: yes
Modification executed by: core-workflow
Debt trend: new=0, accepted=0, retired=0, regressed=0 (window=5)
Debt trend delta: new=0, accepted=0, retired=0, regressed=0

| Issue ID | Source | WCAG Version | Level | SC | Current | Fix | Changed Target | Citation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ISSUE-002 | lighthouse | 2.2 | AA | 2.4.4,4.1.2 | Links have discernible text | Ensure each link has meaningful, discernible text. | a.jump-link | 2.4.4: https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context ; 4.1.2: https://www.w3.org/WAI/WCAG22/Understanding/name-role-value | fixed |
| ISSUE-001 | lighthouse | 2.2 | AA | 1.4.4,1.4.10 | User-scalable is not disabled | Allow zoom and avoid viewport settings that block reflow or text resize. | meta[name="viewport"] | 1.4.4: https://www.w3.org/WAI/WCAG22/Understanding/resize-text ; 1.4.10: https://www.w3.org/WAI/WCAG22/Understanding/reflow | fixed |
| ISSUE-004 | axe | 2.2 | AA | 4.1.2 | Buttons must have discernible text | Give each button a discernible accessible name. | button.icon-only | 4.1.2: https://www.w3.org/WAI/WCAG22/Understanding/name-role-value | fixed |
| ISSUE-003 | axe | 2.2 | AA | 1.1.1 | Images must have alternate text | Add a meaningful alt attribute or mark decorative images with empty alt text. | img.hero | 1.1.1: https://www.w3.org/WAI/WCAG22/Understanding/non-text-content | fixed |
| ISSUE-006 | axe | 2.2 | AA | 1.3.1,2.4.6 | Heading levels should only increase by one | Use a logical heading hierarchy without skipping levels unnecessarily. | h3 | 1.3.1: https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships ; 2.4.6: https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels | open |
| ISSUE-005 | axe | 2.2 | AA | 1.3.1 | Lists must contain only li elements | Ensure list containers contain only listitem children. | ul.plain | 1.3.1: https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships | fixed |
| ISSUE-007 | manual | 2.2 | AA | 2.4.11 | Review whether focused elements remain at least partially visible. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 2.4.11: https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum | needs-review |
| ISSUE-008 | manual | 2.2 | AA | 2.4.12 | Review whether focused elements remain fully unobscured in enhanced scenarios. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 2.4.12: https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-enhanced | needs-review |
| ISSUE-009 | manual | 2.2 | AA | 2.4.13 | Review whether focus appearance meets WCAG 2.2 requirements. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 2.4.13: https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance | needs-review |
| ISSUE-010 | manual | 2.2 | AA | 2.5.7 | Review whether dragging interactions have a single-pointer alternative. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 2.5.7: https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements | needs-review |
| ISSUE-011 | manual | 2.2 | AA | 2.5.8 | Review whether targets meet minimum target size requirements. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 2.5.8: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum | needs-review |
| ISSUE-012 | manual | 2.2 | AA | 3.2.6 | Review whether help mechanisms remain consistent across pages. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 3.2.6: https://www.w3.org/WAI/WCAG22/Understanding/consistent-help | needs-review |
| ISSUE-013 | manual | 2.2 | AA | 3.3.7 | Review whether redundant-entry protections are provided where needed. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 3.3.7: https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry | needs-review |
| ISSUE-014 | manual | 2.2 | AA | 3.3.8 | Review accessible authentication without cognitive function tests. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 3.3.8: https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum | needs-review |
| ISSUE-015 | manual | 2.2 | AA | 3.3.9 | Review enhanced accessible authentication support. | Review the affected element and implement a WCAG-conformant remediation. | manual-review | 3.3.9: https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-enhanced | needs-review |

## Report Metadata

- Product: Libro.AgentWCAG
- Product version: 0.1.0
- Source revision: 40909dfb06f2ee93fca2b199abea26c4d7357117
- Report schema version: 1.0.0
