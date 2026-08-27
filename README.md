# SmartPrep

[![PyPI](https://img.shields.io/pypi/v/smartprep.svg)](https://pypi.org/project/smartprep/)
[![Python](https://img.shields.io/pypi/pyversions/smartprep.svg)](https://pypi.org/project/smartprep/)
[![License](https://img.shields.io/pypi/l/smartprep.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-777-brightgreen.svg)](#testing)

**Intelligent, auditable data preparation for Python.**

```bash
pip install smartprep
```

SmartPrep is not another `fillna()` wrapper. It is a decision system for data
preparation: it diagnoses problems, explains the evidence, quantifies how sure it
is, proposes alternatives, and then — critically — **refuses to act when acting
would be a guess**.

```python
import smartprep as sp

scan = sp.scan(df)
print(scan.summary())
```

```
Rows 1210  Columns 21
Scan coverage 100% of applicable enabled checks (14 completed, 0 skipped)

34 issues detected:
  AMBIGUOUS                      4
  AUTO_FIX_WITH_LOG              4
  DOMAIN_RULE_REQUIRED          10
  DO_NOT_TOUCH                   1
  SAFE_AUTO_FIX                  8
  USER_CONFIRMATION_REQUIRED     7

Scan coverage measures checks executed, not data correctness.
```

Eight findings can be repaired without asking. Twenty-one need a human. One must
not be touched at all — and the library says which is which, and why.

---

## Status

**v1.0.3.** Diagnosis, safe repair, guided review,
preprocessing, validation, privacy, drift, EDA, three renderer backends,
publishing to five formats, and a Studio with one shared interaction state —
linked brushing, cross-filtering, a visual builder and a treatment sandbox —
all work end to end.

**What 1.0 promises.** The public API is stable. Every name in `sp.__all__` is
supported, and removing or changing one requires a major version — a snapshot
test fails if the surface moves by accident, which is the only way a
commitment like this survives a refactor.

**What it does not promise.** Multi-backend execution (Polars, DuckDB, Arrow),
semantic rule packs, root-cause analysis and a hosted documentation site are
not here. They are additions rather than corrections, and none of them changes
what the current API means.

| Capability | Status |
|---|---|
| `sp.scan()` — full diagnosis, no mutation | **Implemented** |
| `sp.auto_prepare()` — apply only what is provably safe | **Implemented** |
| `sp.guided_prepare()` — human-in-the-loop decisions | **Implemented** |
| `sp.clean()` — convenience alias | **Implemented** |
| 14 detectors, issue model, triage policy | **Implemented** |
| Audit trail, snapshots, rollback, idempotence | **Implemented** |
| Data health score | **Implemented** |
| `verified_df`, `finalize()`, waivers | **Implemented** |
| Markdown + JSON reports | **Implemented** |
| `recommend_preprocessing()` — goal-aware advice | **Implemented** |
| `Preprocessor` — impute, encode, scale, leakage guard | **Implemented** |
| `ValidationPlan` and `DataContract` | **Implemented** |
| `PrivacyScanner` and PII transformations | **Implemented** |
| Drift and cleaning drift | **Implemented** |
| `profile()`, `associations()`, `missingness()` | **Implemented** |
| `ChartSpec` + SVG renderer | **Implemented** |
| Self-contained HTML reports | **Implemented** |
| Matplotlib and Plotly renderers | **Implemented** |
| PNG / PDF / SVG / HTML chart export | **Implemented** |
| PDF, PowerPoint and notebook publishing | **Implemented** |
| Shared interaction state, stable row identity | **Implemented** |
| Drag-and-drop composition, keyboard equivalent | **Implemented** |
| Linked brushing and cross-filtering | **Implemented** |
| Smart data grid, treatment sandbox | **Implemented** |
| `sp.studio()` — grid, builder, sandbox, brushing, stages | **Implemented** |
| Faceting and multi-series composition | **Implemented** |
| Visual Workflow Builder / Pipeline Canvas | **Implemented** |
| Entity resolution, record linkage | **Implemented** |
| Time-series and panel diagnostics | **Implemented** |
| Missingness mechanism evidence (MCAR testing) | **Implemented** |
| Multivariate and contextual outliers | **Implemented** |
| Learn validation rules from a trusted sample | **Implemented** |
| Journal-convention tables in text, Markdown, HTML and LaTeX | **Implemented** |
| Multi-backend execution | Planned |

This table is generated from `smartprep.capabilities`, and a test fails if it
drifts from what the package actually exports. Four documents used to claim
what existed, and they disagreed within a day.

**On "Studio".** The v0.6 Studio implements the visual analytics foundation:
one shared interaction state, stable row identity, drag-and-drop composition
with a keyboard equivalent, linked brushing, cross-filtering, the smart grid
and the treatment sandbox.

It also carries faceting, multi-series composition and the visual workflow
canvas, and shares the same core operations, audit semantics and analytical
results as the code-first API. Filtering and selection change the current
view; they never alter the underlying dataset.

The one limit worth stating plainly: the portable Studio composes from charts
precomputed in Python rather than aggregating in the browser, so a pairing
nobody precomputed is answered with the line of Python that builds it. That is
a deliberate property of a single self-contained file, not an oversight — see
**Portable Studio and Live Studio** below.

This README documents what exists. Nothing below describes a feature that is not
in the package.

---

## Why this exists

Automated cleaning tools fail in a specific way: they are confident. They parse
an ambiguous date, drop a conflicting duplicate, or replace a placeholder with a
mean, and the dataset comes back looking clean. The damage is invisible because
the tool reported success.

SmartPrep is built on the opposite premise:

> Automatic mode may finish with unresolved issues. It may never hide them.

That single rule produces everything else in the design.

---

## Installation

```bash
pip install smartprep
```

For reading Excel fixtures:

```bash
pip install "smartprep[excel]"
```

Requires Python 3.10+.

---

## The core idea: two different confidences

Most tools carry one confidence number. SmartPrep carries two, because they
answer different questions:

```
outlier_detected            0.99   <- how sure are we there is a problem?
delete_that_row             0.30   <- how sure are we this is the right fix?
```

Being certain a value is wrong tells you nothing about what the right value is.
`31/02/2025` is invalid with complete certainty — and there is no defensible
correction for it. So SmartPrep reports it and offers **no treatment at all**.

Only `repair_confidence` reaches the autonomy ladder:

| Band | Class |
|---|---|
| 98–100% | `SAFE_AUTO_FIX` |
| 90–<98% | `AUTO_FIX_WITH_LOG` |
| 75–<90% | `REVIEW_RECOMMENDED` |
| 60–<75% | `USER_CONFIRMATION_REQUIRED` |
| <60% | `ABSTAIN` |

And confidence alone never decides. Eligibility is:

```
AutoFixEligibility = f(
    repair_confidence,
    severity,
    reversibility,
    information_loss_risk,
    domain_sensitivity,
    statistical_impact
)
```

Row deletion, column deletion, outlier removal, entity merge and category merge
are irreversible by definition. **They can never reach `SAFE_AUTO_FIX`, at any
confidence.**

---

## Public API

The API is deliberately explicit. There is no call that decides on your behalf
whether to repair automatically or ask you.

| Call | Semantics | Mutates input |
|---|---|---|
| `sp.scan(df)` | Diagnose only | No |
| `sp.auto_prepare(df)` | Repair only what is provably safe | No |
| `sp.guided_prepare(df)` | Ask about everything else | No |
| `sp.studio(df)` | Same engine, with a screen | No |
| `sp.clean(df)` | Convenience alias for `auto_prepare` | No |

`sp.clean()` is a shortcut, **not** a more aggressive mode. It does not suppress
warnings — when findings remain it says so on stderr.

All five entry points are implemented.

---

## `sp.scan()`

### Syntax

```python
sp.scan(
    frame,
    *,
    registry=REGISTRY,
    **context,
)
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `frame` | `pd.DataFrame` | required | Input data. Never modified. |
| `registry` | `DetectorRegistry` | built-in | Detector set to run. |
| `identifier` | `str` | — | Business key column, for duplicate analysis. |
| `compare_to` | `str` | — | Column to validate identifier-embedded metadata against. |
| `date_columns` | `tuple[str, ...]` | inferred | Columns to run date analysis on. |
| `categorical` | `tuple[str, ...]` | inferred | Columns to run category analysis on. |
| `ranges` | `tuple[RangeConstraint, ...]` | defaults | Hard domain bounds. |

### Returns

`ScanResult`, with two independent measures that must never be conflated:

```python
scan.coverage            # share of applicable checks that ran
scan.issues              # what was found
```

```python
scan.by_severity()       # dict[Severity, list[Issue]]
scan.by_category()       # dict[IssueCategory, list[Issue]]
scan.by_repair_class()   # dict[RepairClass, list[Issue]]

scan.auto_fixable        # may be applied without asking
scan.needs_review        # requires a human decision
scan.blocking            # must not be touched

scan.get("DUP-CONFLICT-invoice_id")
scan.find(IssueCategory.INVALID_DATE)
scan.summary()
```

### Example

```python
import pandas as pd
import smartprep as sp

df = pd.read_excel("invoices.xlsx", dtype=object)

scan = sp.scan(
    df,
    identifier="invoice_id",
    compare_to="invoice_date",
    date_columns=("invoice_date",),
)

for issue in scan.blocking:
    print(f"BLOCKING {issue.id}")
    print(f"   {issue.evidence.summary}")

# Why will automatic mode leave something alone?
for issue in scan.needs_review[:4]:
    cls, reasons = issue.triage()
    print(f"{issue.id}: {cls.name}")
    for reason in reasons:
        print(f"   {reason}")
```

```
BLOCKING DUP-CONFLICT-invoice_id
   9 identifiers appear on rows whose other columns disagree

MISS-SUSPICIOUS-payment_date: DOMAIN_RULE_REQUIRED
   resolution depends on a business rule the dataset does not contain
MISS-SUSPICIOUS-payment_amount: DOMAIN_RULE_REQUIRED
   resolution depends on a business rule the dataset does not contain
RANGE-quantity: USER_CONFIRMATION_REQUIRED
   repair confidence 85% is below the 90% threshold for autonomous repair
   candidate treatments disagree; evidence is not decisive
RANGE-discount_pct: USER_CONFIRMATION_REQUIRED
   repair confidence 85% is below the 90% threshold for autonomous repair
   candidate treatments disagree; evidence is not decisive
```

`blocking` and `needs_review` are disjoint: a `DO_NOT_TOUCH` finding is not
something to review, it is something to leave alone until a precedence rule
exists.

### Notes

`scan()` copies the frame and asserts equality afterwards. If a detector mutates
the input, it raises rather than returning a silently corrupted result.

---

## Reading the output

Every result renders as a table rather than a dataclass dump. In a notebook the
cell output *is* the summary; in a terminal, `.display()` prints it.

```python
result = sp.scan(df)

result.display("severity")     # findings, severity, columns, categories
result.to_frame("columns")     # the same view as a DataFrame
result.table("findings")       # the Table object, for other formats
```

```text
Findings by severity

--------------------------------
Severity         Findings  Share
--------------------------------
Blocking                1     3%
Critical review         6    18%
High warning           14    41%
Warning                 7    21%
--------------------------------
```

For a preparation run, `explain()` answers the question the status alone
cannot:

```python
prepared = sp.auto_prepare(df)
prepared.display("declined")   # audit, applied, declined, health, findings
print(prepared.explain())
```

```text
Blocked  |  17 cells changed by 12 operations  |  27 findings left open  |  health 70 -> 76

27 findings were left open. Automatic mode repairs only what it can justify;
the rest is reported.
   10  Domain rule required
    7  User confirmation required
    5  Safe auto fix
    4  Ambiguous
    1  Do not touch

Use guided_prepare() to decide these, or finalize() to accept the dataset with
the remaining findings waived on the record.
```

### Tables for papers

Four formats from one definition — plain text, Markdown, HTML, and LaTeX with
`booktabs`:

```python
table = sp.scan(df).table("columns")
print(table.to_latex(label="tab:quality"))
```

```latex
\begin{tabular}{lrrrr}
\toprule
Column & Findings & Worst severity & Rows affected & Auto-fixable \\
\midrule
invoice\_date & 5 & High warning & 12 & 2 \\
\bottomrule
\end{tabular}
```

Underscores and percent signs are escaped, so it compiles in your manuscript
rather than in ours. No `\hline` and no vertical rules — `booktabs` exists to
prevent exactly those.

The conventions are the ones journals enforce, and they are not house style:
**horizontal rules only**, because vertical ones add ink without adding
information; **figures right-aligned**, so the units digit sits under the
units digit and two numbers can be compared without counting characters; **one
precision per column**, taken from the quantity rather than the float's
accidental tail, so `0.9500000000000001` prints as `95%`; and **notes below
the foot rule**, where a reader looks for what the numbers do not say.

Absence prints as a dash, never a zero. They are different claims.

### The view computes nothing

Every figure in every table came from the object being described. Nothing is
counted, aggregated or re-derived in the display layer, because a view that
calculates its own number can disagree with its source — and a reader holding
two figures has no way to choose between them. Tests assert the agreement
rather than the docstring claiming it.

The same rule puts **detection and repair confidence side by side** in every
findings table, with the note that explains them. It is what the library rests
on, and it used to be visible only to someone who knew to look for two
similarly named fields in a `repr`.

---

## `sp.auto_prepare()`

Scans, applies only what is provably safe, re-scans what those repairs
invalidated, and reports everything — including what it refused to do.

```python
result = sp.auto_prepare(df, identifier="invoice_id", date_columns=("invoice_date",))
print(result.summary())
```

```
Status: BLOCKED

Scan coverage           100%
Data health             70 -> 76
Operations applied      12
Cells changed           17
Issues                  34 -> 27
Resolved                7
Still open              27
Needs review            22
Blocking                1

Auto Mode intentionally left the following unchanged:

  DUP-CONFLICT-invoice_id [DO_NOT_TOUCH] 2 rows -- identifiers appear on rows
  whose other columns disagree
      why: severity is BLOCKING; repairing could destroy valid information
  RANGE-quantity [USER_CONFIRMATION_REQUIRED] 2 rows
      why: repair confidence 85% is below the 90% threshold for autonomous repair
      why: candidate treatments disagree; evidence is not decisive
  ...

clean_df contains unresolved findings. It is not a verified dataset.
```

`BLOCKED` is not a failure. It is the library declining to guess, and saying
exactly why.

### The result object

```python
result.raw_df            # untouched input
result.clean_df          # safe repairs applied; may carry open findings
result.verified_df       # only after finalize() succeeds

result.status            # CompletionState
result.fixed_issues      # resolved by this run
result.review_queue      # what a human must decide, most urgent first
result.blocking_issues   # what must not be touched at all

result.health_before     # decomposable score, per dimension
result.health_after
result.cells_changed

result.audit             # every change AND every refusal
result.plan              # the operations, in dependency order
result.snapshots         # restore points
result.rollback(0)       # the data as it was

result.report()          # Markdown
result.to_json()         # machine-readable
```

### Three names, three guarantees

| Attribute | What it promises |
|---|---|
| `raw_df` | Nothing was touched |
| `clean_df` | Safe repairs applied. **Open findings may remain.** |
| `verified_df` | Nothing is unresolved or unwaived |

`verified_df` raises until you call `finalize()`, and `finalize()` raises while
anything is still open. To proceed anyway you must waive each finding, with a
reason, on the record:

```python
result.waive("DUP-CONFLICT-invoice_id", "two source systems, both retained on purpose")
result.finalize()
clean = result.verified_df
```

### Dependency order, not detector order

Repairs run in scope order — representation, then text, then values, then
structure — because a range check against a column still holding `"1,200.50"` as
text gives a confident answer to the wrong question. After the plan runs, the
detectors those repairs invalidated are re-run rather than carried forward.

### Idempotence

```python
second = sp.auto_prepare(result.clean_df)
assert second.cells_changed == 0
```

`clean(clean(df)) == clean(df)` is asserted in the test suite, not assumed.

---

## `sp.guided_prepare()`

Guided mode is not a second implementation of cleaning. It is the same engine
with the abstentions turned into questions: **everything auto mode refused to
decide is exactly what guided mode asks about.**

```python
session = sp.guided_prepare(df, identifier="invoice_id")
print(session.next_question().render())
```

```
Issue 1 of 21
  id         DUP-CONFLICT-invoice_id
  columns    invoice_id
  severity   BLOCKING
  class      DO_NOT_TOUCH
  rows       2

Problem    1 identifiers appear on rows whose other columns disagree
Evidence   detection confidence 100%, source statistical_rule

Why automatic mode did not act:
  - severity is BLOCKING; repairing could destroy valid information

No treatment can be carried out for this finding. The correct value is not
inferable from the data.

  skip / waive(reason) / leave_unresolved
```

The card offers **only treatments that can actually be carried out**. A menu
item that does nothing is worse than no menu item.

### Answering

```python
session.answer(issue_id, "use_recommendation")
session.answer(issue_id, "choose_alternative", treatment="parse_numeric")
session.skip(issue_id)
session.waive(issue_id, reason="two source systems, both retained on purpose")

result = session.finish()      # a PreparationResult, same as auto mode
```

Nothing is applied until `finish()`. Safe repairs are applied there too, so a
guided run is never worse-informed than an automatic one.

### Decisions are data

```python
saved = session.export_decisions()          # JSON

later = sp.guided_prepare(new_df, decisions=saved)
assert later.remaining == 0                 # same answers, no re-asking
```

A decision you cannot replay is a click, and a click is not reproducible.

### Continuing from auto mode

```python
auto = sp.auto_prepare(df)
if auto.needs_guided_review:
    result = auto.open_guided().accept_all_recommendations().finish()
```

The scan, the applied repairs, the issue ids and the audit all carry across.
Nobody restarts the analysis.

### How much to ask

```python
sp.guided_prepare(df, level="minimal")         #  7 questions
sp.guided_prepare(df, level="important_only")  # 17
sp.guided_prepare(df, level="standard")        # 21
sp.guided_prepare(df, level="expert")          # 22
```

---

## Preprocessing

**A different job from cleaning**, and kept separate on purpose:

```
Cleaning       "this value is wrong"
Preprocessing  "this value is right, but the model needs it differently"
```

Conflating them is how a scaled column ends up in a descriptive report. So
preprocessing never runs inside `auto_prepare()` — you ask for it.

```python
prep = sp.Preprocessor(target="churn")
prep.add_missing_indicator("income")
prep.impute("income", method="median")
prep.encode("sector", method="one_hot")
prep.scale("income", method="robust")

train_out = prep.fit_transform(train)
test_out = prep.transform(test)      # uses the training parameters
```

`transform()` before `fit()` raises. Fitting on everything and then
transforming is the leakage this class exists to prevent.

| Kind | Methods |
|---|---|
| Impute | mean, median, mode, constant, group_median, forward_fill, backward_fill, interpolate |
| Encode | one_hot, ordinal, frequency, count, target (leave-one-out, smoothed) |
| Scale | standard, minmax, robust, maxabs, log1p, yeo_johnson, quantile_rank |

### Advice, with reasons

```python
advice = sp.recommend_preprocessing(df, goal="machine_learning", target="churn")
print(advice.summary())
```

```
  income     impute   median      (85%)
      skew is 1.77; the mean is pulled by the tail, the median is not
      not mean: distorted by the skew in this column
  city       encode   target      (70%)
      25 levels across 65 rows; one-hot would add 25 sparse columns
      not one_hot: would add 25 columns, most of them near-empty
      not frequency: cheaper and leak-free, but discards the outcome signal
  income     scale    robust      (85%)
      8.3% of values sit outside the fences; median/IQR resists them
      not standard: mean and standard deviation move with the outliers
```

`goal="econometrics"` recommends **no scaling and no encoding at all** — those
change how coefficients read, and a descriptive model does not need them.

### Leakage guard

```
[HIGH_WARNING] encode_target on ['city']: target encoding learns from the
outcome, so any fit on data the model will later be scored on leaks
  remedy: fit on the training partition only, and prefer cross-fitted encoding
```

It also flags sequential fills that read future rows, and any feature
correlating with the target above 0.98.

---

## Validation and data contracts

```python
result = (sp.ValidationPlan()
          .not_null("invoice_id")
          .unique("invoice_id")
          .between("rating", 1, 5)
          .isin("status", ["Paid", "Pending", "Overdue"])
          .implies("status == 'Paid'", "payment_amount > 0")
          .run(df))

print(result.summary())
valid, invalid = result.split()
```

```
Validation: ERROR
42 rows, 5 rules

  PASS      not_null:invoice_id      0/42 failed (0.00%)
  ERROR     unique:invoice_id        4/42 failed (9.52%)
  WARNING   between:rating           2/42 failed (4.76%)

  35 rows pass every rule, 7 do not.
```

Failures are **graded against thresholds you set**, not binary. Every rule runs,
so one failure cannot hide the next. `raise_if_failed()` turns the plan into a
CI gate.

### Contracts inferred, not hand-written

```python
contract = sp.DataContract.infer(clean_df, name="invoices")
contract.to_yaml()

changes = contract.diff(sp.DataContract.infer(next_batch, name="invoices"))
if sp.DataContract.is_breaking(changes):
    ...
```

Changes are classified, because "a column was added" and "a column changed
meaning" need different responses:

```
[backward_compatible] note: column added
[breaking]            amount: column removed
[semantic_breaking]   amount: unit changed EUR -> DZD; the numbers still parse
                      but no longer mean the same thing
```

---

## Privacy

```python
report = sp.PrivacyScanner().scan(df)
print(report.summary())
print(report.reidentification_risk(df))
```

Detection uses checksums and ranges, not regex alone — a 16-digit order
reference is neither a card number (fails Luhn) nor a phone number (exceeds the
E.164 15-digit limit).

Quasi-identifiers are reported separately, because a table with no names in it
can still identify people by combination:

```python
{'columns': ['postcode', 'city'], 'unique_rows': 3, 'unique_rate': 1.0,
 'smallest_group': 1, 'level': 'high'}
```

```python
from smartprep.privacy import mask, hash_value, pseudonymise, generalise

mask("merwan@example.com")   # 'm*****@example.com' — the domain survives
generalise(37, bucket=10)    # '[30, 40)'
```

**Every report says detection cannot prove absence.** A scanner that reports
"no PII" without that caveat invites someone to publish on its say-so.

---

## Drift

```python
report = sp.compare_reference(reference_df, new_batch)
print(report.summary())
```

```
Drift: CRITICAL
reference 500 rows, current 500 rows

  x        critical  psi=2.201 ks=0.594
      mean -0.0357 -> 1.462, sd 0.913 -> 1.011
  cat      severe    jensen_shannon=0.227
      3 -> 3 categories; unseen: ['d']; disappeared: ['c']

Primary contributors:
  x        91%
  cat       9%
```

"Drift detected: True" is not actionable, so drift is always attributed. And a
distribution change is not automatically an error — a genuine population shift,
a quality problem and a source change all look alike here and need different
responses.

### Cleaning drift

```python
verdict = sp.cleaning_drift(last_month_scan, this_month_scan)
```

If the **problems** change between batches rather than the values, the cause is
upstream:

> problems appeared that the reference batch did not have. This usually means
> the source changed, and no local cleaning rule will fix the cause.

---

## The audit trail

Every operation is recorded. So is every refusal — a log of only successful
edits cannot answer the question users actually ask, which is *why is this still
wrong?*

```python
print(result.audit.summary())
```

```
12 operations applied, 22 refused
  applied OP-00025 parse_numeric          unit_price      rows=0     cells=2
  applied OP-00027 canonicalise_mechanical country        rows=0     cells=3
  REFUSED SKIP-00003 abstained            quantity        rows=2     cells=0
      reason: repair confidence 85% is below the 90% threshold for autonomous
              repair; candidate treatments disagree; evidence is not decisive
```

Each record carries the issue it answers, the rule that justified it, who
decided, what it touched, and dataset fingerprints on both sides of the change.

---

## Reports

```python
result.report("scan")         # pre-cleaning, marked RAW DATA
result.report("preparation")  # what changed, and what did not
result.report("comparison")   # issue-by-issue before and after
result.export_report("report.md")
```

Every preparation report contains a section titled **What auto mode did NOT
do**. It is mandatory and it is never placed in an appendix.

---

## Detectors

Fourteen detectors ship in the default registry.

### Structural

| Detector | Finds |
|---|---|
| `mixed_physical_type` | Columns storing more than one representation family — text where a number belongs. `int`/`float` mixing is *not* reported; that is how spreadsheets store numbers. |
| `duplicate_identifier` | Splits identical duplicates from **conflicting** ones. Identical payloads are redundant; conflicting payloads mean two sources disagree, and choosing a survivor without a precedence rule destroys information. |
| `identifier_embedded_metadata` | Metadata encoded inside an identifier (`INV-2025-00109`) contradicting its own row. |

### Temporal

`date_integrity` classifies string dates into four outcomes that must never
share a code path:

| Class | Example | Meaning |
|---|---|---|
| `invalid` | `31/02/2025` | No valid reading exists. No correction is offered. |
| `ambiguous` | `04/05/2024` | Two valid readings. The data cannot choose. |
| `format_conflict` | `08-26-2024` | One valid reading, in a layout that contradicts the column. A root-cause signal about the upstream export. |
| `ok` | `2026-06-26` | Unambiguous. |

The dominant layout is inferred from unambiguous values only — letting ambiguous
values vote would make the inference circular. ISO-8601 is self-describing and
never counts as a conflict.

### Text

| Detector | Finds |
|---|---|
| `unicode_confusable` | Homoglyphs (`Manufacturıng`, U+0131) and invisible characters. **Accented Latin letters are never flagged** — `Algérie` is correct French, not damage. |
| `category_variant` | Surface variants of one category, graded separately: whitespace and case fold mechanically; spelling and language variants are *proposed*, never merged silently. |

### Numeric

| Detector | Finds |
|---|---|
| `range_violation` | Values outside a declared hard bound. |
| `sentinel_candidate` | Placeholder codes wearing a number's clothes. `999999` employees is not a very large company. Requires combined evidence — a repeated round value, far outside the genuine distribution — because any single signal produces false positives on legitimately large values. |

### Cross-field

| Detector | Finds |
|---|---|
| `formula_invariant` | Arithmetic relationships, reported with their fit rate. **Proposed, never enforced.** A 92% fit is evidence of a rule and evidence that the rule is not the whole story. |
| `state_consistency` | Workflow states contradicted by their supporting fields. |
| `geographic_consistency` | City/country conflicts via a canonical entity graph. |
| `currency_context` | Currency differing from the country's domestic one — a **question, not a defect**. |
| `accounting_plausibility` | Profit exceeding revenue, as a soft check. |
| `missingness` | Missingness split by whether absence is structurally *expected*. |

---

## Missingness has semantics

A headline rate is close to useless:

```
payment_date missing: 333 (27.52%)
```

Split by state, it says something completely different:

| Status | Missing | Class |
|---|---|---|
| Pending | 229 | structural — unpaid, absence is correct |
| Overdue | 96 | structural — unpaid, absence is correct |
| Paid | 7 | **suspicious** |
| Partial | 1 | **suspicious** |

325 structural, 8 suspicious. The 8 are the finding. A flat 27.52% buries them,
and imputing across all 333 would fabricate payment events that never happened.

---

## Reference data is an entity graph

A flat `country -> [city]` map is not sufficient. Building one during
development under-reported city/country conflicts — 24 instead of 26 — purely
because `Marrakesh` and `Marrakech` were treated as different places.

```
CanonicalEntity
    ├── aliases
    ├── transliterations    Marrakech (fr) / Marrakesh (en)
    ├── language variants
    ├── historical names
    └── administrative parent
```

Resolution reports *how* it matched, and an unrecognised entity is reported as
`UNKNOWN_ENTITY` — never silently treated as consistent.

---

## What SmartPrep must not flag

False positives are the primary failure mode of automated cleaning tools. A tool
that over-reports trains people to ignore it.

The test suite therefore asserts what must **not** be detected, with the same
weight as what must:

| Control | Must not be reported as |
|---|---|
| `Algérie` | Unicode corruption — it is correct French |
| `Overdue` + payment date present | State contradiction — that is a late payment |
| Foreign currency | Hard error — that is ordinary commerce |
| `Pending` + no payment date | Suspicious missingness — structurally expected |
| `int` and `float` in one column | Mixed-type defect |

A build that detects every real issue but flags `Algérie` is a failed build.

---

## EDA

Every statistic is a plain object before it is a picture. A profiling layer that
only exists inside an HTML template cannot be tested, diffed or driven from a
notebook — and the interface ends up dictating the statistics.

```python
p = sp.profile(df)
print(p.summary())
```

```
42 rows x 20 columns, 28.9 KB
14 missing cells (1.67%), 1 duplicate rows

column                 kind          missing  distinct
invoice_date           datetime         0.0%        40
country                categorical      0.0%         9
unit_price             numeric          0.0%        12
```

```python
p.get("unit_price").numeric.skew        # 1.77
p.get("unit_price").numeric.outliers_iqr
p.get("invoice_id").is_identifier_like  # True
p.to_dict()                             # fully serialisable
```

### Associations across mixed types

```python
print(sp.associations(df).summary())
```

```
  city       unit_price        correlation_ratio  +0.998
  sector     payment_method    cramers_v          +0.907
  invoice_amount payment_amount spearman          +0.928
```

Each pair gets the measure that applies to it, and the measure is reported.
A Pearson-only matrix silently drops every categorical column, which tells the
reader those columns carry no signal — usually false.

Identifier and constant columns are excluded: correlating a key with anything
measures row order, not a relationship.

### Missingness structure

```python
print(sp.missingness(df).summary())
```

```
Columns that go missing together:
  city                 reported_profit      1.00
  payment_date         payment_amount       0.50
```

Two columns absent on the same rows usually share one upstream cause. Fixing
the cause fixes both; a rate alone never shows it.

### What cleaning did to the statistics

```python
comparison = result.compare_profiles()
for where, what in comparison.red_flags:
    print(where, "—", what)
```

```
x — variance shrank 41.2% -- imputation at the centre narrows every interval
    computed from this column
c — distinct values fell from 6 to 3 -- categories may have been merged
```

The question after a repair is not "is it clean now?" but "did you change what
the data says?".

---

## Charts

A chart is a **specification**, not plotting code:

```python
chart = sp.viz.distribution_chart(p.get("employee_count"))
chart.rationale
# 'skew +4.41, so the mean is not the centre; 8 values outside the IQR fences'
chart.fidelity          # Fidelity.BINNED
chart.to_json()         # serialisable, diffable, replayable

svg = sp.render_svg(chart)
```

Three properties every chart carries:

- **A rationale.** Selection is diagnostic-driven — a histogram because the
  column is skewed, not because it is a float. A chart nobody can justify is
  decoration.
- **A fidelity.** `FULL`, `BINNED`, `RANDOM_SAMPLE`, `AGGREGATED`. A reader who
  thinks they are seeing every point will over-read the picture.
- **No dependency.** `render_svg` is built in, so a report can always draw its
  own charts. Matplotlib and Plotly are optional accelerants.

---

## HTML reports

```python
result.export_report("report.html")     # format inferred from the suffix
scan.report("html", df)                 # pre-cleaning, with profile and charts
```

One file. No CDN, no build step, no server — a report that needs a network
stops working the moment it is archived or emailed. Charts are inline SVG, cell
values are escaped, and the print stylesheet lays every section out on its own
page.

Every preparation report carries **What auto mode did NOT do**, never in an
appendix.

---

## `sp.studio()`

```python
sp.studio(df)                    # renders inline in a notebook
sp.studio(result).save("studio.html")
sp.studio(result).open()         # in the default browser
```

Overview, profile, EDA, issue inbox, guided decision cards and the audit
timeline, in one self-contained page.

### The Studio applies nothing

This is the constraint that keeps it honest. The interface holds **no cleaning
logic**: every number in it was computed by the core, and decisions recorded in
it are exported as the same JSON that guided mode replays.

```python
workspace = sp.studio(df)
# ... make decisions in the page, click Export ...
result = workspace.apply_decisions(exported_json, df)
```

That is the whole contract between interface and engine. The page emits JSON;
`guided_prepare` applies it. So the Studio can never become a second
implementation of cleaning, and no click is unreproducible.

It is a single HTML page rather than a client/server app — a deliberate trade.
No build step, no port, no process left running, and it works identically in a
notebook, a browser and an archived file. What it gives up is writing changes
back into the live session, which is exactly the capability that would let
clicks become unreproducible.

---

## Renderer backends

One specification, three outputs. The destination chooses the renderer, not the
author — so a figure in a PDF and the same figure on screen cannot disagree.

```python
chart = sp.viz.distribution_chart(sp.profile(df).get("income"))

sp.render_svg(chart)          # built in, no dependency
sp.viz.to_matplotlib(chart)   # publication figures, PNG and PDF
sp.viz.to_plotly(chart)       # zoom, pan, box and lasso select
```

| Backend | Needs | Interaction ceiling |
|---|---|---|
| `svg` | nothing | `HOVER` — always available, escaped, accessible |
| `matplotlib` | `smartprep[viz]` | `NONE` — print-quality static figures |
| `plotly` | `smartprep[viz]` | `EXPLORE` — zoom, pan, box and lasso select |

### Interaction is not animation

Two axes, never one flag. A chart can be animated and static — stage frames
printed as small multiples — or interactive and unanimated, or both, or
neither. Collapsing them is how a library ends up calling hover text
interactive.

```python
chart.interaction     # NONE | HOVER | EXPLORE -- what a reader may do
chart.animation_field # what orders the frames -- says nothing about the above
chart.as_static()     # the same chart, for print
```

`interaction` is a **ceiling**, not a prediction: each renderer delivers the
lesser of it and what its medium allows. Paper cannot hover, so Matplotlib
draws a spec identically whether its ceiling is `EXPLORE` or `NONE`. Print
lowers the ceiling once, on the spec, rather than each renderer deciding for
itself what print means.

```python
sp.viz.save_chart(chart, "figure.png")    # also .pdf .svg .html .json
sp.viz.available_backends()
```

A missing backend raises `BackendUnavailable` naming the install command — not
an `ImportError` from somewhere deep inside a report.

### The chart vocabulary

Eleven marks, every one implemented. Beyond the basics:

```python
sp.viz.box_chart(*columns)          # whiskers clipped to the fences
sp.viz.ecdf_chart(column)           # no bin width to argue about
sp.viz.scatter_chart(df, "a", "b")  # sampled above 3,000 points, and says so
sp.viz.target_chart(df, "sector", "churn")
```

`box_chart` clips whiskers to the IQR fences deliberately: one distant value
would otherwise flatten every box into a sliver. `ecdf_chart` exists because a
histogram can be made to tell a different story by rebinning, and an ECDF
cannot.

---

## Publishing

```python
result.publish("report.pdf")     # multi-page, publication figures
result.publish("deck.pptx")      # slides with speaker notes
result.publish("analysis.ipynb") # runnable code, not a transcript
result.publish("report.html")
result.publish("report.md")
```

Every format is built from the same `Deck` of the same chart specs. The
notebook is **runnable code that reproduces the analysis** rather than prose
describing it — a report the reader can run is a report they can disagree with.

The PDF has contents with real page numbers, a running header, a caption under
every figure, and a methodology appendix stating the four distinctions the
library rests on. A reader holding only the PDF should not need the
documentation to know that scan coverage is not data health.

Every deck carries **What auto mode did NOT do** as its own slide. Never an
appendix.

---

## Report or Studio — two products

These were one artifact, and the compromise hurt both. An archival file cannot
carry an analysis UI; an analysis UI should not be constrained by what will
still render in ten years.

| | HTML report | Studio |
|---|---|---|
| For | Archiving, emailing, attaching to a paper | Analysing and deciding |
| Charts | Static SVG | Static SVG plus interaction |
| Scripts | Navigation only | Grid, explorer, stages, tooltips |
| Size | ~35 KB | 0.5–1 MB, capped and tested |
| Guarantee | Renders correctly with scripts disabled | Needs a browser |

Both draw the **same** specs and the same EDA numbers.

```python
result.export_report("report.html")   # archival
sp.studio(result)                     # workspace
```

### Inside the Studio

Nine sections: Overview, Data, **Grid**, EDA, **Explore**, Issues, Guided,
**Stages**, Audit.

**Smart grid** — sortable, searchable, filterable, with per-cell quality
overlays. The overlay is why this is not merely a table: missing cells and
cells belonging to a finding are coloured, so you see *where* a problem is
rather than reading that one exists. Capped at 500 rows, and it says so; the
full dataset stays in Python.

**Explore** — choose a question, not a chart type. Two numerics scatter; a
category against a numeric compares group means. The pairing decides the chart,
so nobody has to justify a choice the data already implied.

**Stages** — step or play through raw → repaired → by dimension. The only
animation in the library, because these frames are ordered steps of a real
process. Nothing moves for decoration. Play, **pause**, speed, and a button per
step: motion a reader cannot stop is motion imposed on them.

Still nothing is applied in the browser. Decisions export as the JSON
`guided_prepare(decisions=...)` replays — and a test asserts that replaying
them through the page and through Python produces an identical frame, an
identical audit log and the same status. The Studio holds no cleaning logic,
and that is checked rather than asserted in prose.

### Accessibility

Every chart carries `<title>` and `<desc>` as its first children, and the
description repeats the rationale **and the sampling caveat** — a reader using
a screen reader is exactly the reader who cannot see the footnote, and a
sampled chart that reads as a full one is the worst thing the library could
say.

The grid is operable from a keyboard: focus a header, press Enter to sort,
`aria-sort` announces the change. Flagged and changed cells carry a marker and
a weight, not colour alone. `prefers-reduced-motion` is honoured — stage
playback still works, it simply will not start on its own.

---

## Linked analytics

Every panel in the Studio reads **one** state. Filter in the grid and the
charts narrow; click a bar and the rows behind it are selected everywhere at
once. Built surface by surface, each would grow its own answer to "what is
selected", and reconciling four almost-identical state models afterwards is
the work nobody schedules.

```python
state = sp.StudioState.of(df)
state.filter_by(sp.FilterClause("country", sp.Comparison.EQUALS, "Morocco"))
state.select_rows(keys, origin="grid")

state.view(df)       # the filtered frame -- a copy, always
state.describe()     # "filtered where country is 'Morocco'; 12 rows selected"
state.to_json()      # exactly what the page sends back
```

A filter here narrows a **view**. It never drops a row from anybody's data —
the same distinction the grid states on its own face.

### A selection is rows, not positions

Drop three rows, sort by a column, or reset an index, and row 47 is a
different row. That bug is invisible from outside: the highlight lands on the
wrong records and nobody notices, because wrong rows still look like rows.

So a selection is carried as **keys**, from the strongest identity the frame
offers — and the library says which one it got:

| Identity | When | Survives a transformation |
|---|---|---|
| index | the frame's index is unique | yes |
| content | rows are unique, the index is not | yes |
| positional | neither | **no, and it says so** |

A positional identity is reported, not hidden, exactly as a sampled chart says
it was sampled. The page cannot claim otherwise: identity comes from the frame
in hand, never from the payload.

---

## The visual builder

Drag a field onto a shelf — or focus one and press <kbd>1</kbd> or <kbd>2</kbd>.
Both routes build the same `Composition`; an accessible alternative that
builds something *different* is not an alternative.

```python
fields = sp.fields_of(sp.profile(df))
spec = sp.compose(df, fields, sp.Composition(x="country", y="revenue", aggregate="mean"))

for suggestion in sp.recommend_charts(fields):
    print(suggestion.label, "--", suggestion.why)
```

It refuses two things. A field with nine thousand levels does not become a bar
chart — a wall of unreadable labels is worse than an empty panel, and the
refusal says what to do instead. And it never recommends without explaining:
every suggestion carries the sentence that justifies it, because a
recommendation you cannot argue with is one you cannot learn from.

The builder does not aggregate in the browser. Every combination the page can
show was composed in Python before the file was written; a combination nobody
precomputed is answered with the line of Python that produces it. The Studio
is one file and cannot run pandas — pretending otherwise would mean shipping a
second, worse implementation of it.

---

## The treatment sandbox

Choosing between three candidate repairs by reading their names and
confidences is choosing blind.

```python
for candidate in sp.preview_candidates(df, issue):
    print(candidate.summary())
```

```text
parse_numeric: 2 cells across 2 rows; unit_price.max: 500 -> 1,200;
  unit_price.mean: 121.7 -> 147.4; unit_price.std: 80.12 -> 184.3
```

That is the point of it. Parsing `1,200.50` is obviously right and it still
doubles the standard deviation — which anyone about to reason from that
distribution needs to know *before* they choose, not after.

Imputation always improves completeness; that is what it is for. A sandbox
reporting only completeness would recommend imputing everything, so the spread
and the distinct count are shown beside it: what the repair spends, not only
what it buys.

**A preview never applies anything, and there is no way to make it.** It has
no `apply()`, writes no audit record, and leaves your frame untouched.
Committing goes back through `guided_prepare`, the only path that records who
decided and why. That friction is deliberate — a sandbox with a commit button
is a second way to change data, and the second way is always the one that
skips the audit.

Preview and apply are not two implementations that agree. They are the same
operation over a copy, and a test asserts they produce an identical frame.

---

## The pipeline

A preparation run as stages you can see, disable and export.

```python
workflow = sp.default_workflow()
workflow.disable("node-outliers")
run = workflow.run(df)
print(run.summary())
```

```text
8 of 9 stages ran
  Type repair                 26 cells  health -0.5
  Categories                  46 cells  health +3.6
- Ranges and outliers          0 cells
```

That `health -0.5` on type repair is the canvas earning its keep: parsing
`"1,200.50"` into a number is obviously right, and it *exposes* range
violations that were hidden inside strings. A pipeline that only showed
improvements would have hidden it.

**A node implements nothing.** Each stage selects the operations
`auto_prepare` would have run for its own issue categories and hands them to
the same executor, writing to the same audit. Running every stage produces the
frame and the audit that `auto_prepare` produces — and a test asserts it, on
both fixtures.

The order is not a convention. Types are repaired before ranges because a
range check on the string `"1,200.50"` is meaningless; duplicates are resolved
after categories because *Marrakech* and *Marrakesh* are not duplicates until
they are the same word. Rearranging into an order that would produce a wrong
answer is refused, with the reason.

```python
workflow.to_python()   # the pipeline as a readable script
workflow.to_json()     # the pipeline as data, replayable
```

---

## Faceting and multi-series

```python
sp.compose(df, fields, sp.Composition(x="quantity", y="revenue", facet="region"))
sp.compose(df, fields, sp.Composition(x="date", y="revenue", color="region"))
```

Faceting happens on the **spec**: `spec.panels()` splits it into one ordinary
chart per group, so every backend draws small multiples with the code it
already had. Three things fall out of that — brushing links across panels
because a panel keeps its row keys, the panels share one scale because a grid
with private axes is a grid nobody may compare, and faceting an aggregate is
refused because aggregated rows no longer line up with the frame.

Twelve panels is the cap. More cannot be compared at a glance, which is the
only thing small multiples are for.

Every encoding channel — `x`, `y`, `color`, `facet`, `size` — changes what
**all three** renderers draw, or is refused with a reason. A test enumerates
them and fails on any that is neither.

---

## Time-series, panel data and record linkage

Three diagnostics about the *shape* of data rather than its values. None of
them repairs anything, and all three produce ordinary findings that go through
the same triage and the same guided queue as everything else.

```python
sp.timeseries(df, time="date")
sp.panel(df, entity="firm", time="year")
sp.link(df, fields=("name", "city", "tax_id"))
```

### Series

Cadence (with **how much of the series actually keeps it** — a daily series
with gaps and a weekly one with noise both infer "daily"), missing periods,
duplicate timestamps, ordering, mixed timezones, and stale runs.

A gap gets no automatic repair: filling it and dropping it give different
answers, and a closed market has no Sunday. Sorting chronologically is the one
exception, because it changes no value.

### Panels

```text
panel firm x year: 3 entities, 5 periods, 13 rows (unbalanced)
  completeness 87% of a full grid
  sector never changes within an entity -- collinear with an entity fixed effect
  region_size: 0% of variance is within-entity
```

The within/between decomposition every panel estimator depends on, and few
datasets are checked for. A **constant-within** regressor is collinear with
the fixed effect and drops out, taking its coefficient with it. A **weakly**
varying one is worse: it stays in and returns an estimate identified by almost
nothing, which looks exactly like an answer.

An unbalanced panel is reported, not corrected. It is usually fine and
occasionally a survivorship filter, and the counts alone cannot tell you
which.

### Linkage

Candidate pairs with per-field evidence, each naming the comparator it used —
"90% similar" means different things for a name and a staff count.

**Nothing is merged.** There is no threshold: at 0.85 two branches of one
company become one, at 0.86 they stay apart, and a dataset's conclusions must
not turn on a constant somebody chose on a Tuesday. The score orders the
review queue; every pair is still decided, and `map_to_canonical` offers a
reversible alternative to merging.

Blocking keeps the comparison tractable and costs recall, so the report says
how many pairs were never compared — a linkage run that shows only what it
found reads as exhaustive.

---

## Portable Studio and Live Studio

The Studio is one self-contained HTML file. No build step, no port, no process
left running — it works the same in a notebook, a browser, an emailed archive
and a locked-down machine.

It costs one thing, and the cost is real: **the page cannot run pandas.** The
builder composes from charts precomputed in Python, and a pairing nobody
precomputed is answered with the line of Python that builds it.

Putting an aggregation engine in the page was rejected, not deferred. The
moment a browser computes a number someone might quote, that number has to be
reconciled with the Python one forever afterwards, and every disagreement is a
bug nobody can reproduce from the notebook.

| | Portable Studio | Live Studio |
|---|---|---|
| Status | **Implemented** | Planned |
| Composition | From precomputed specs | Any composition, on demand |
| Aggregation | In Python, ahead of time | In Python, on request |
| Survives without Python | Yes | No |

Both modes share the same `StudioState`, `Composition`, `ChartSpec` and core
operations. Only the transport differs — which is what lets general visual
exploration arrive without a second analytical engine ever being written.

---

## Testing

```bash
pip install -e ".[dev]"
pytest
```

**775 tests.** 724 of them run anywhere, against a deterministic fixture that
ships with the package — so the contract described here is one you can execute,
not one you have to take on trust.

| Suite | What it holds |
|---|---|
| `test_synthetic_acceptance.py` | The shipped contract. Exercises all 14 detectors. |
| `test_false_positives.py` | What must **not** be flagged. |
| `test_eligibility_policy.py` | The safety policy as a pure function. |
| `test_repair.py` | Repair, audit, rollback, idempotence, waivers. |
| `test_guided.py` | Decision cards, replay, the auto handoff. |
| `test_preprocessing.py` | fit/transform discipline and the leakage guard. |
| `test_validation.py` | Graded rules, sundering, schema evolution. |
| `test_privacy_drift.py` | PII checksums, re-identification, drift metrics. |
| `test_scan_api.py` | Coverage honesty, failure policy, row references. |
| `test_reporting.py` | Reports disclose rather than flatter. |
| `test_eda.py` | Profiles, associations, missingness, before/after. |
| `test_viz_studio.py` | Chart specs, SVG, HTML reports, the Studio. |
| `test_renderers_publish.py` | Backends, export, publishing, interactivity. |
| `test_architecture_invariants.py` | The rules two components must agree on. |
| `test_linked_analytics.py` | State, identity, the builder, the sandbox. |
| `test_workflow.py` | The pipeline, faceting, multi-series. |
| `test_domain.py` | Time-series, panel data, entity resolution. |
| `test_mechanism.py` | Missingness mechanism evidence, and its limits. |
| `test_anomaly.py` | Multivariate and contextual outliers. |
| `test_dtypes.py` | Every pandas dtype, and the type map. |
| `test_learning.py` | Learned rules, and the ones refused. |
| `test_public_api.py` | The public surface, frozen against accident. |
| `test_display.py` | Journal-convention tables, and that views compute nothing. |
| `test_benchmarks.py` | Performance budgets — scaling guards, not a comparative benchmark. Marked `slow`. |
| `test_baseline_detection.py` | The real 1,210-row workbook. Marked `stress`. |

The 51 `stress` tests need a workbook that is not distributed; they skip
cleanly without it.

```bash
pytest -m "not stress"   # what a PyPI install runs: 724 tests
pytest -m stress         # the real-workbook regression suite
```

Every count in both suites is a frozen contract. Changing one is a behaviour
change that must be justified, never silently accepted.

---

## Design principles

1. **Never mutate silently.** `inplace=False` everywhere; the original frame is
   never touched.
2. **Diagnose before repair.** No treatment without evidence.
3. **Preserve evidence.** The original value survives alongside the repair.
4. **Prefer explainable recommendations.** Every proposal carries its reason,
   its confidence and its alternatives.
5. **Reproducibility over clicks.** Every decision becomes code.
6. **Abstain when uncertain.** "I don't know — this needs review" is a correct
   answer, and a better one than a confident guess.

---

## Documentation

- `_ARCHITECTURE_DECISIONS.md` — frozen design decisions and their rationale
- `_STRESS_TEST_BASELINE.md` — the verified acceptance baseline
- `REFERENCES.md` — prior art reviewed and what was learned from each

---

## Contributing

See `CONTRIBUTING.md`. A new detector is not complete until it ships with both a
positive test and a negative control.

---

## Citation

See `CITATION.cff`.

---

## License

Apache-2.0. See `LICENSE`.

---

## Author

**Dr Merwan Roudane**
<merwanroudane920@gmail.com>
<https://github.com/merwanroudane>
