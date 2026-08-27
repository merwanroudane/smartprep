# SmartPrep 1.0.2 — Output UX Improvement Specification

## Scope
This version should improve **presentation only** for capabilities that already exist. Do not redesign the analytical Core and do not add unrelated feature families.

The real-data test exposed the main weakness clearly: SmartPrep detects and explains issues well internally, but default Python output is too raw. Objects such as `Issue(...)`, `AuditRecord(...)`, long row tuples, enums, fingerprints and nested dataclasses are machine-readable but not pleasant for normal users.

The goal of 1.0.2 is therefore:

> **Make SmartPrep equally strong for humans and machines.**

---

# 1. Core rule

Keep:

```text
Core Result Objects
        ↓
Presentation/View Model
        ↓
Notebook / Terminal / Studio / HTML / PDF / PPTX
```

Do not recompute or reinterpret analytical results inside the display layer.

---

# 2. Three display levels

Every major result should support:

### Executive summary
Short and immediately understandable.

### Structured table
Readable, sortable, filterable findings.

### Technical details
Full raw metadata only on demand.

---

# 3. Improve `ScanResult`

Current compact repr:

```text
<ScanResult issues=28 coverage=100%>
```

is acceptable for developers but insufficient as the primary notebook output.

Recommended compact repr:

```text
<ScanResult rows=1210 cols=21 issues=28 coverage=100%>
```

In Jupyter/Colab, `scan` should render a rich HTML summary automatically.

---

# 4. Rich notebook display for `scan`

When the user runs:

```python
scan = sp.scan(df)
scan
```

show something like:

```text
SmartPrep Scan
Rows            1,210
Columns            21
Scan coverage     100%
Issues found        28

Critical              5
High Warning          9
Warning               6
Notice                5
Info                  3
```

Then show a concise table of the most important findings.

Important wording:

```text
Scan coverage: 100%
All applicable detectors completed.
This is NOT a data-quality score.
```

Coverage and health must never be confused.

---

# 5. Add `scan.to_frame()`

High-priority API addition:

```python
issues_df = scan.to_frame()
```

One row per issue.

Recommended columns:

- `issue_id`
- `category`
- `severity`
- `columns`
- `affected_rows_count`
- `detection_confidence`
- `recommended_action`
- `repair_confidence`
- `repair_class`
- `rule_source`
- `summary`
- `status`

Example:

| Severity | Issue ID | Finding | Columns | Affected | Detection | Recommendation | Repair |
|---|---|---|---|---:|---:|---|---:|
| Critical | RANGE-quantity | Values outside valid range | quantity | 5 | 100% | Quarantine rows | 85% |
| Notice | MISS-city | Missing city values | city | 26 | 100% | Record only | 99% |
| High | GEO-country-city | Country-city conflict | country, city | 26 | 98% | Review pair | 40% |

---

# 6. Add `scan.show()`

Recommended:

```python
scan.show()
scan.show(view="summary")
scan.show(view="issues")
scan.show(view="severity")
scan.show(view="columns")
scan.show(view="actions")
```

Filters:

```python
scan.show(severity="critical")
scan.show(category="missingness")
scan.show(column="payment_date")
```

Reuse existing filtering logic internally.

---

# 7. Do not print giant affected-row lists

Instead of hundreds of indices, show:

```text
Affected rows: 325
Sample: 3, 9, 14, 16, 20, ...
```

Full rows should be available only when requested.

---

# 8. Compact `Issue.__repr__`

Suggested:

```text
<Issue RANGE-quantity severity=CRITICAL_REVIEW rows=5 confidence=100%>
```

Do not dump enums, nested evidence, all rows and treatments in the default repr.

---

# 9. Beautiful issue-detail view

Example:

```text
Range violation — quantity

Severity                Critical review
Detection confidence    100%
Affected rows            5

What SmartPrep found
5 values fall outside the valid range [1, ∞).

Examples
-3
0

Recommended action
Quarantine violating rows

Repair confidence
85%

Why not auto-fixed?
The problem is certain, but the correct replacement value cannot be inferred safely.

Alternatives
- Set missing + flag
```

---

# 10. Always separate detection and repair confidence

Display:

```text
Detection confidence  100%
Repair confidence       85%
```

Never collapse both into one generic “confidence”.

This distinction is central to SmartPrep.

---

# 11. Human-readable labels

Internal enums remain unchanged.

Presentation should convert:

```text
CRITICAL_REVIEW        → Critical review
DOMAIN_RULE_REQUIRED   → Domain rule required
mixed_physical_type    → Mixed physical type
parse_numeric          → Parse numeric values
```

Do not expose `np.float64(...)`, enum reprs or raw dataclass names in normal output.

---

# 12. Severity badges

Recommended semantic labels:

- Critical review
- High warning
- Warning
- Notice
- Info

Use text plus icons; never color alone.

---

# 13. Severity summary visualization

Default small visual:

```text
Critical      █████ 5
High Warning  █████████ 9
Warning       ██████ 6
Notice        █████ 5
Info          ███ 3
```

Static in notebook/PDF, interactive in Studio/HTML.

---

# 14. Issues by category

Show counts for:

- Missingness
- Range violations
- State contradictions
- Mixed physical types
- Category variants
- Geographic conflicts
- Unicode
- Accounting
- Formula/invariant
- Sentinel candidates

---

# 15. Issues by column

Example:

```text
payment_date       3
employee_count     2
sector             2
country            2
invoice_amount     1
```

Use a horizontal bar chart and sortable table.

---

# 16. Data Quality Matrix

Add a compact matrix such as:

| Column | Missing | Type | Range | Consistency | Category | Semantic |
|---|---|---|---|---|---|---|
| payment_date | ● | ● | | ● | | |
| unit_price | | ● | | | | |
| employee_count | | | ● | | | ● |
| country | | | | ● | ● | |

This gives a rapid dataset-wide diagnosis.

---

# 17. Improve `PreparationResult`

Current:

```text
<PreparationResult status=DOMAIN_REVIEW_REQUIRED applied=11 open=24>
```

is ambiguous.

The word `applied=11` can be misunderstood because some applied records are `record_only` or `leave_unchanged`.

The display must separate:

- actions completed
- data-changing repairs
- cells changed
- no-change records
- abstentions
- open findings

Example:

```text
SmartPrep Auto Preparation

Status
Domain review required

Actions completed            11
Data-changing repairs         6
Cells changed                72
Recorded/no-change actions    5
Auto abstentions             17
Open findings                24
```

Use actual values calculated from the result.

---

# 18. Explain status

Instead of only:

```text
DOMAIN_REVIEW_REQUIRED
```

display:

```text
Domain review required

Safe automatic preparation is complete.
Some unresolved findings require business/domain decisions that SmartPrep cannot infer safely.
```

---

# 19. Add `result.summary()`

Example:

```python
result.summary()
```

Human-readable description of:

- what changed
- what did not change
- why auto stopped
- what remains open

---

# 20. Add `result.to_frame()`

One row per preparation/audit action.

Recommended columns:

- operation_id
- operation
- issue_id
- columns
- result
- repair_class
- repair_confidence
- cells_changed
- rows_affected
- decision_source
- reason

---

# 21. Improve `AuditLog`

Current raw `AuditLog(records=[AuditRecord(...), ...])` is too verbose.

Notebook default should be a table.

Example:

| Operation | Result | Issue | Column | Cells changed | Repair confidence | Reason |
|---|---|---|---|---:|---:|---|
| Parse unambiguous dates | Applied | TYPE-invoice_date | invoice_date | 7 | 99% | 7 converted; 9 left for review |
| Parse numeric values | Applied | TYPE-unit_price | unit_price | 13 | 100% | All representations parsed |
| Range treatment | Abstained | RANGE-quantity | quantity | 0 | 85% | Below autonomous threshold |
| Geographic review | Abstained | GEO-country-city | country, city | 0 | 40% | Either field could be wrong |

---

# 22. Add `result.audit.to_frame()`

Essential for notebook use:

```python
audit_df = result.audit.to_frame()
```

---

# 23. Compact `AuditRecord.__repr__`

Suggested:

```text
<AuditRecord OP-00019 parse_numeric APPLIED cells=13 confidence=100%>
```

For abstention:

```text
<AuditRecord SKIP-00003 abstained issue=RANGE-quantity>
```

Hide fingerprints and huge row lists by default.

---

# 24. Group audit output

Display sections:

### Applied changes
### Recorded / no change
### Auto abstentions

This is much clearer than one raw list.

---

# 25. Before vs After summary

Every `PreparationResult` should show what Auto Mode improved and what remained.

Example:

| Issue family | Before | After |
|---|---:|---:|
| Mixed physical types | 3 | 0 |
| Mechanical category variants | 3 | 0 |
| Suspicious missingness | 2 | 2 |
| Range violations | 5 | 5 |
| Domain contradictions | 7 | 7 |

---

# 26. Health display

If health score is available, show separately from coverage:

```text
Data Health
Before  67/100
After   82/100
Change  +15
```

Also show dimensions so the user does not overinterpret one composite score.

---

# 27. Show why Auto declined

This should be one of SmartPrep's signature outputs.

Example:

```text
Why SmartPrep did not auto-fix

Detection confidence: 100%
Repair confidence:     85%
Auto threshold:        90%

Reason:
The value is certainly invalid, but the correct replacement cannot be inferred safely.
```

---

# 28. Missing-values dashboard

Include:

- total missing
- missing by column
- structural missingness
- suspicious missingness
- expected missingness
- co-missingness
- missing patterns

Visuals:

- bar chart
- matrix
- heatmap
- pattern view

For the test dataset, `payment_date` should visually distinguish expected missing values from suspicious ones.

---

# 29. Type diagnostics dashboard

For `unit_price` show representation composition, for example:

```text
Float                    98.02%
Integer                   0.91%
Numeric string            0.58%
Formatted numeric string  0.50%
```

Use stacked bar/compact composition chart.

---

# 30. Category variants dashboard

Example:

```text
Canonical: Algeria

Mechanical variants
- Algeria
- ALGERIA
- algeria
- " Algeria"
- "Algeria "

Semantic candidate
- Algérie → Algeria
  Requires confirmation
```

Clearly distinguish safe mechanical normalization from semantic merging.

---

# 31. Unicode diagnostics

Show character-level explanation.

Example:

```text
Manufacturıng
         ↑
U+0131 LATIN SMALL LETTER DOTLESS I

Proposed:
Manufacturing
```

---

# 32. Formula/invariant dashboard

For the detected invoice relation, display:

```text
Candidate relationship
invoice_amount =
quantity × unit_price × (1-discount_pct) × (1+tax_pct)

Fit                 91.7%
Violations            101

Important:
SmartPrep did NOT overwrite the recorded amount.
The relationship requires business confirmation.
```

Add residual plot/distribution.

---

# 33. State contradiction dashboard

Show counts clearly:

```text
Paid without payment date        7
Partial without payment date     1
Paid without payment amount      8
Pending with received payment    2
Paid amount mismatch            55
```

Use a bar chart.

---

# 34. Range violation dashboard

For each field show:

- declared range
- invalid count
- below/above count
- sample invalid values
- histogram/boxplot with range bounds

---

# 35. Column-detail view

Recommended:

```python
scan.show_column("payment_date")
```

Display:

- inferred type
- missing count/rate
- issue list
- expected vs suspicious missingness
- recommendations
- related business-state findings

---

# 36. Related issues

Do not merge distinct Core findings, but show relationships.

Example:

```text
MISS-SUSPICIOUS-payment_date
Related:
- STATE-paid_without_payment_date
- STATE-partial_without_payment_date
```

This prevents the user from thinking duplicated diagnostics are unrelated.

---

# 37. Review queue grouping

Instead of one flat list, group:

- Needs user confirmation
- Needs domain/business rule
- Ambiguous
- Informational / no action

This makes the open queue actionable.

---

# 38. Data preview from issue

Every issue should offer:

```text
View affected rows
```

Display only relevant columns by default.

Example state issue:

- status
- payment_date
- payment_amount
- invoice_amount

---

# 39. Before/after change samples

Recommended:

```python
result.show_changes("unit_price")
```

Example:

| Row | Before | After |
|---:|---|---:|
| 46 | `"9,597.80"` | `9597.80` |

Sample by default; full export on request.

---

# 40. Notebook-first experience

The normal workflow should be:

```python
scan = sp.scan(df)
scan
```

then:

```python
scan.to_frame()
```

then:

```python
result = sp.auto_prepare(df)
result
```

then:

```python
result.audit.to_frame()
```

Users should not need to inspect raw dataclasses simply to understand the result.

---

# 41. Terminal experience

Terminal fallback should show clean text tables.

Avoid huge ANSI output.

Optional `rich` support is fine, but avoid making a heavy dependency mandatory purely for cosmetics.

---

# 42. Static / interactive / animated distinction

Keep the current architecture:

### Static
Notebook publication, PDF, PPTX, PNG, SVG.

### Interactive
Studio/HTML, hover, zoom, selection, filters.

### Animated
Only meaningful transitions:
- cleaning stages
- time
- treatment sensitivity
- before/after changes

---

# 43. Convenience plotting

Consider:

```python
scan.plot("severity")
scan.plot("issues_by_column")
scan.plot("missingness")
result.plot("before_after")
result.plot("changes")
result.plot("open_issues")
```

Reuse existing `ChartSpec`; do not introduce new analytical plotting logic.

---

# 44. Studio landing page

The first screen should answer:

1. How healthy is the dataset?
2. What are the biggest issues?
3. What can be fixed safely?
4. What requires me?
5. What changed?
6. Where should I go next?

---

# 45. Studio Issue Inbox

Recommended columns:

- Severity
- Issue
- Column
- Affected
- Detection
- Repair
- Decision
- Status

Filters:

- Critical
- Auto-fixable
- Needs review
- Domain review
- Resolved
- Open

---

# 46. Treatment candidate cards

Show:

- recommendation
- repair confidence
- reversibility
- information-loss risk
- statistical impact
- alternatives
- why recommended

Use the existing Treatment Sandbox for previews.

---

# 47. HTML reports

Improve first-page order:

1. Executive Summary
2. Dataset Overview
3. Main Findings
4. What Auto Mode Changed
5. What Auto Mode Refused
6. Before vs After
7. Remaining Review Queue
8. Technical details

---

# 48. PDF output

Issue sections should use human-readable tables/cards and charts.

Do not expose raw Python representations.

---

# 49. PowerPoint output

Presentation-oriented flow:

1. Dataset Overview
2. Data Quality
3. Critical Issues
4. Missingness
5. Type/Format Problems
6. Business-rule Contradictions
7. Automatic Repairs
8. Auto Abstentions
9. Before vs After
10. Required Decisions

---

# 50. Consistent number formatting

Examples:

```text
0.95       → 95%
0.0214876  → 2.15%
7608.5084  → 7,608.51
1210       → 1,210
```

Do not expose `np.float64(...)`.

---

# 51. Display modes

Recommended:

```text
compact
standard
detailed
technical
```

Notebook default: `standard`.

Technical mode exposes:

- raw enums
- fingerprints
- exact row IDs
- detector names
- parameters
- full evidence

---

# 52. Lazy rendering

Do not slow scanning just to prepare pretty visuals.

Architecture:

```text
sp.scan(df)
→ analytical result

scan.show()
→ render presentation
```

Charts should render lazily.

---

# 53. Large-output behavior

For hundreds/thousands of findings:

- paginate
- aggregate first
- lazy-load details
- virtualize Studio tables

For huge affected-row sets:

- show count + sample
- expand only on request

---

# 54. Presentation architecture

Recommended internal layer:

```text
Core Result
   ↓
ViewModel
   ├── title
   ├── metrics
   ├── tables
   ├── badges
   ├── sections
   ├── charts
   └── technical details
   ↓
Renderer
   ├── text
   ├── HTML
   └── dataframe
```

Charts remain:

```text
ChartSpec → renderer
```

---

# 55. Reuse presentation wording everywhere

The same ViewModel/presentation labels should power:

- notebook
- Studio
- HTML report
- PDF
- PPTX

This prevents contradictory wording.

---

# 56. Testing requirements

Add tests for:

- concise `Issue` repr
- concise `AuditRecord` repr
- rich HTML contains issue count
- no huge row dump by default
- no fingerprint dump by default
- no `np.float64` in normal display
- detection vs repair confidence both visible
- coverage vs health distinction
- actions completed vs cells actually changed
- accessibility labels
- DataFrame conversions preserve issue count

---

# 57. Accessibility

Maintain:

- text + color
- sufficient contrast
- keyboard navigation
- semantic table headers
- chart `<title>/<desc>`
- reduced motion
- data-table alternatives for charts

---

# 58. Minimum high-value API additions

Avoid API proliferation.

The most useful additions are:

```python
scan.show()
scan.to_frame()

result.show()
result.to_frame()

result.audit.show()
result.audit.to_frame()
```

Optional helpers may come later.

---

# 59. Must-have deliverables for 1.0.2

1. Rich notebook display for `ScanResult`.
2. Rich notebook display for `PreparationResult`.
3. Rich notebook display for `AuditLog`.
4. `scan.to_frame()`.
5. `result.to_frame()`.
6. `result.audit.to_frame()`.
7. Concise repr for `Issue`.
8. Concise repr for `AuditRecord`.
9. Human-readable enums and operation labels.
10. Hide giant row tuples by default.
11. Hide fingerprints by default.
12. Explicit detection vs repair confidence.
13. Explicit coverage vs health.
14. Explicit actions vs actual data changes.
15. Better before/after summary.
16. Severity/category/column summary visuals.
17. Better issue-detail cards.
18. Improved Studio Issue Inbox.
19. Report reuse of the same presentation layer.
20. Regression tests for all display semantics.

---

# 60. Out of scope for 1.0.2

Do not add unrelated feature families:

- Multi-backend
- new cleaning algorithms
- new anomaly algorithms
- new semantic packs
- new econometric models
- new preprocessing algorithms
- Live Studio architecture

The focus is:

> **Presentation quality for capabilities that already exist.**

---

# 61. Definition of Done — Scan

Complete when:

- `scan` is immediately readable in Jupyter/Colab.
- all findings can be displayed as a clean table.
- affected-row floods are removed.
- detection/repair confidence are clear.
- coverage is explained.
- raw objects remain accessible.

---

# 62. Definition of Done — PreparationResult

Complete when the user can immediately tell:

- what changed;
- how many cells changed;
- what was only recorded;
- what Auto Mode refused;
- what remains open;
- why Guided/Domain Review is needed.

---

# 63. Definition of Done — Audit

Complete when:

- applied, no-change and abstained records are visually distinct;
- default display is a readable table;
- low-level metadata is hidden unless requested;
- DataFrame export is trivial.

---

# 64. Definition of Done — Visual presentation

Complete when:

- severity summary is attractive;
- category summary is attractive;
- issues-by-column is attractive;
- before/after changes are attractive;
- static and interactive outputs reuse existing visualization architecture;
- accessibility remains intact.

---

# 65. Final recommendation

The real-data experiment showed that the Core is doing its job.

The weakness is not:

```text
SmartPrep does not know what happened.
```

The weakness is:

```text
SmartPrep knows what happened,
but default Python output makes the user read internal object representations.
```

`1.0.2` should therefore transform the experience from:

```text
Issue(...)
AuditRecord(...)
long nested dataclass output
```

into:

```text
Clear summary
+ beautiful tables
+ meaningful charts
+ actionable review queue
+ expandable expert details
```

without weakening machine-readable access or changing analytical semantics.

That should be the central goal of SmartPrep `1.0.2`.
