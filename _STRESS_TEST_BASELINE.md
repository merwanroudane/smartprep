# SmartPrep Stress-Test Baseline — `data_project.xlsx`

Ground truth for the real-data acceptance suite defined in
`intelligent_data_cleaning_preprocessing_library_plan_v9_referenced.md` §110–134.

Every figure below was recomputed from the workbook on 2026-08-26 and matches the
plan. Detector regression tests assert against these counts.

## Fingerprint

| Property | Value |
|---|---|
| Sheets | `raw_data`, `data_dictionary` |
| Rows | 1,210 |
| Variables | 21 |
| Data dictionary | 21 entries (`variable`, `description`) |

Columns: `invoice_id`, `customer_id`, `invoice_date`, `payment_date`, `country`,
`city`, `sector`, `quantity`, `unit_price`, `discount_pct`, `tax_pct`,
`invoice_amount`, `payment_amount`, `currency`, `payment_method`, `status`,
`employee_count`, `annual_revenue`, `reported_profit`, `customer_rating`,
`sales_channel`.

## §111 Mixed physical types within one column

| Column | Composition |
|---|---|
| `invoice_date` | datetime 1,194 (98.68%) · string 16 (1.32%) |
| `unit_price` | float 1,186 (98.02%) · int 11 (0.91%) · numeric-string 7 (0.58%) · formatted-numeric-string 6 (0.50%) |
| `annual_revenue` | float 1,184 (97.85%) · int 20 (1.65%) · formatted-numeric-string 6 (0.50%) |

`dtype == object` alone must not be treated as the column's type.

## §112 Date intelligence

16 string dates across 4 layouts. Dominant layout inferred from unambiguous
values only: **day-first**. The 16 resolve into four distinct classes:

| Class | Count | Meaning |
|---|---|---|
| **invalid** | 4 | `31/02/2025` x3, `2025-13-04` x1 — no valid reading exists |
| **ambiguous** | 5 | `04/05/2024`, `06-05-2025`, `07-10-2025`, `07/12/2024`, `12/03/2026` — two valid readings each |
| **format conflict** | 1 | `08-26-2024` — exactly one valid reading, but month-first against a day-first column |
| **ok** | 6 | unambiguous, including 2 ISO-8601 |

Three corrections to the original reading, established by implementation:

1. Ambiguity is **5**, not 1. `04/05/2024` is the plan's example, but
   `06-05-2025`, `07-10-2025`, `07/12/2024` and `12/03/2026` are equally
   two-way readable. `07-07-2025` is *not* ambiguous — both readings give the
   same date.
2. `08-26-2024` is **not** ambiguous. It has one valid reading. It belongs to
   its own class, and a single unambiguous outlier layout is a root-cause
   signal about the upstream export.
3. ISO-8601 values must **never** be reported as conflicting with a day-first
   column. ISO is self-describing; flagging it produced 2 false positives.

These four classes must never share a code path. The engine offers no treatment
that invents a date for `31/02/2025`.

## §113 Identifier integrity

| Metric | Count |
|---|---|
| Duplicated `invoice_id` values | 18 |
| Rows involved | 36 |
| Identical payload (safe to dedupe) | 9 |
| **Conflicting payload (`DO_NOT_TOUCH`)** | 9 |

## §114 Identifier-embedded metadata

`INV-(?P<year>\d{4})-\d{5}` — **6 rows** where the embedded year ≠ `invoice_date.year`.

## §115 Category variants

| Column | Distinct raw | Variants |
|---|---|---|
| `country` | 10 | `Algeria`, `ALGERIA`, `algeria`, `' Algeria'`, `'Algeria '`, `Algérie` + Egypt/France/Morocco/Tunisia |
| `sector` | 15 | `ICT`/`'ICT '`/`I.C.T` · `Retail`/`'Retail '`/`retail` · `Construction`/`construction` · `Tourism`/`Tourismm` · `Manufacturing`/`Manufacturıng` |

Case folding alone reaches only part of this. `Tourismm`→`Tourism` and
`Algérie`→`Algeria` differ by a real letter, so they require a similarity pass
and surface as **proposals**, never as silent merges. A threshold of 0.85 on
sequence similarity separates them (0.93 and 0.86) from `Cash`/`Card` (0.75),
which must stay distinct.
| `payment_method` | 11 | `Card`/`CARD` · `Cash`/`'Cash '` · `Cheque`/`'Cheque '` · `Bank Transfer`/`'Bank transfer '`/`bank transfer` · `Mobile Payment`/`mobile payment` |
| `currency` | 6 | DZD, MAD, TND, EGP, EUR, USD |
| `status` | 4 | Paid, Pending, Partial, Overdue — clean |
| `sales_channel` | 4 | Branch, Partner, Phone, Web — clean |

Triage split: whitespace/case → `SAFE_AUTO_FIX`; `I.C.T → ICT` → `AUTO_FIX_WITH_LOG`;
`Tourismm → Tourism` → `USER_CONFIRMATION_REQUIRED`; `Algérie → Algeria` →
semantic equivalence, requires confirmation.

## §116 Unicode confusables

| Value | Codepoint |
|---|---|
| `Manufacturıng` | `ı` = U+0131 LATIN SMALL LETTER DOTLESS I |
| `Algérie` | `é` = U+00E9 (legitimate French, **not** corruption) |

`.strip().lower()` does not catch U+0131. A confusable detector is required, and
it must not flag `é` as damage.

## §117 Country–city consistency — **26 mismatches**

france+algiers ×6 · algeria+tunis ×4 · algeria+casablanca ×3 · algeria+paris ×2 ·
morocco+cairo ×2 · algeria+cairo ×2 · algeria+{bizerte, rabat, lyon, mansoura, fes} ×1 ·
tunisia+paris ×1 · egypt+oran ×1

City dictionary must include the spelling variant `marrakesh`/`marrakech`.

## §118 Country–currency — **22 mismatches**, 1 `USD`

Expected: Algeria→DZD, Morocco→MAD, Tunisia→TND, Egypt→EGP, France→EUR.
Classified `CONTEXTUAL_WARNING`, never a hard error — foreign-currency invoicing
is legitimate.

## §119 Range violations

| Check | Count |
|---|---|
| `quantity < 0` | 3 |
| `quantity == 0` | 2 |
| `discount_pct < 0` | 4 |
| `discount_pct > 1` | 1 (1.25) |
| `tax_pct < 0` | 1 |
| `tax_pct > 1` | 3 (1.50) |
| `customer_rating > 5` | 5 (values 6.7, 9.9) |
| `employee_count < 0` | 1 |
| `employee_count == 0` | 1 |

`employee_count` yields **2** range violations, not 4: there is no declared
upper bound on headcount, so the two `999999` rows are a sentinel finding
(below), not a range violation. Filing them under both would double-count.

## §120 Sentinel intelligence

`employee_count == 999999` — **2 rows**. Must be classified sentinel-suspect, not
an IQR outlier.

## §121 Candidate invariant

`invoice_amount ≈ quantity × unit_price × (1 − discount_pct) × (1 + tax_pct)`

Fit **91.7%** · **101 violations** (stable across tolerance 0.01–1.0, so these are
genuine breaks, not rounding). Proposed as a candidate rule requiring
confirmation — never auto-applied.

## §122 Workflow / state consistency

| Contradiction | Count |
|---|---|
| `Paid` + `payment_date` missing | 7 |
| `Paid` + `payment_amount` missing | 8 |
| `Paid` + payment ≠ invoice amount | 55 |
| `Pending` + payment_amount > 0 | 2 |
| `Partial` + no payment_date | 1 |
| `Overdue` + has payment_date | 97 — **legitimate** (late payment), needs a state definition |
| `payment_date < invoice_date` | 0 |

## §123 Missingness semantics

| Column | Missing | % |
|---|---|---|
| `payment_date` | 333 | 27.52% |
| `city` | 26 | 2.15% |
| `reported_profit` | 18 | 1.49% |
| `payment_amount` | 16 | 1.32% |

The 333 splits by `status`:

| Status | Missing `payment_date` | Class |
|---|---|---|
| Pending | 229 | structural — unpaid, absence is correct |
| Overdue | 96 | structural — unpaid, absence is correct |
| Paid | 7 | **suspicious** |
| Partial | 1 | **suspicious** |

So **325 structural, 8 suspicious**. The plan cites 7 (the `Paid` subset); the
`Partial` row is the same kind of contradiction and belongs with it.

`payment_amount` splits the same way: Paid 8 + Partial 1 = **9 suspicious**,
Overdue 7 = structural.

A flat 27.52% headline is misleading and must not drive imputation.

## §125 Accounting plausibility

`reported_profit > annual_revenue` — **8 rows**. Soft business constraint;
requires user confirmation, no auto-repair.

## Detector coverage summary

| Category | Findings |
|---|---|
| Mixed physical types | 3 columns |
| Invalid / ambiguous dates | 4 + 2 |
| Duplicate identifiers | 18 (9 conflicting) |
| Identifier metadata mismatch | 6 |
| Category variants | 3 columns |
| Unicode confusables | 1 true positive, 1 must-not-flag |
| Geographic conflicts | 26 |
| Currency conflicts | 22 (contextual) |
| Range violations | 16 |
| Sentinel candidates | 2 |
| Formula violations | 101 |
| State contradictions | 73 (+97 legitimate) |
| Suspicious missingness | 7 of 393 |
| Accounting violations | 8 |
