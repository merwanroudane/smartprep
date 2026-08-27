# SmartPrep — Architecture Decisions Record

Status: **FROZEN** as of 2026-08-26. These decisions resolve the conflicts found
between `smartprep_master_build_prompt_final.md` and
`intelligent_data_cleaning_preprocessing_library_plan_v9_referenced.md`.

Where the two source documents disagree, **this file wins**. Any change here is a
breaking change and requires a CHANGELOG entry.

## How to read this file

Each decision carries an implementation status. **A frozen design contract is
not an API promise.** A decision marked *Planned* describes what the code will
do when that layer is built; it is not callable today. Check the status before
writing code against anything below.

| Status | Meaning |
|---|---|
| **Implemented** | In the package and covered by tests |
| **Partial** | Some of it exists; the gap is named in the decision |
| **Planned** | Frozen design, not yet built |

---

## AD-001 — Product philosophy: Safe by default

> **Status: Implemented**

The library never trades correctness for the appearance of cleanliness.

> Automatic mode may finish with unresolved issues. It may never hide them.

Consequences:

- Ambiguous issues are **never** auto-repaired.
- Critical issues **escalate** to Guided rather than being silently skipped.
- A clean dataset that still carries warnings is a valid, expected outcome.

Supersedes: plan §52, plan §88 (which proposed Guided as the default mode).

---

## AD-002 — Public API surface is explicit; no mode inference

> **Status: Implemented**

There is **no** `sp.prepare(df)` that decides between Auto and Guided on its own.
Ambiguous entry points hide exactly the decisions this library exists to surface.

| Call | Semantics | Mutates input |
|---|---|---|
| `sp.scan(df)` | Diagnosis only. Full applicable scan, zero modification. | No |
| `sp.auto_prepare(df)` | Auto-safe. Repairs only what is provably safe. | No |
| `sp.guided_prepare(df)` | Human-in-the-loop decision queue. | No |
| `sp.studio(df)` | Interactive workspace over the same core. | No |
| `sp.clean(df)` | Convenience alias for `auto_prepare(df).clean_df` with safe defaults. | No |

`sp.clean()` is a convenience wrapper, **not** a more aggressive mode. It must not
suppress warnings; it returns the frame while the result object remains reachable
via `sp.clean(df, detailed=True)`.

Supersedes: master §4, plan §149, plan §100.17.

---

## AD-003 — No silent mutation

> **Status: Implemented - enforced at runtime by scan()**

- `inplace=False` is the default on every public operation.
- The original DataFrame is never modified.
- `result.raw_df` and `result.clean_df` are distinct objects for the lifetime of
  the result.

Supersedes: master §73.

---

## AD-004 — Completion states

> **Status: Implemented - including verified_df, finalize() and waivers**

Auto mode does not return a boolean. It returns one of:

```
CLEAN
CLEAN_WITH_NOTES
CLEAN_WITH_WARNINGS
PARTIALLY_RESOLVED
GUIDED_REVIEW_RECOMMENDED
GUIDED_REVIEW_REQUIRED
DOMAIN_REVIEW_REQUIRED
BLOCKED
```

`CLEAN_WITH_WARNINGS` is an acceptable, non-exceptional terminal state.

### Dataset naming ladder

| Attribute | Guarantee |
|---|---|
| `result.raw_df` | Untouched input |
| `result.clean_df` | Safe repairs applied; **may carry unresolved warnings** |
| `result.verified_df` | Only available after `finalize()` passes: no BLOCKING items, no unwaived required-review items. Every waiver is audited. |

Accessing `verified_df` while blocking issues remain raises
`SmartPrepUnsafeRepairError`. It is never produced implicitly.

Supersedes: plan §100.3, §100.10, §151.

---

## AD-005 — Single confidence ladder

> **Status: Implemented**

One ladder, project-wide. The two competing ladders in master §31 / plan §119 and
plan §100.8 are void.

| Band | Class |
|---|---|
| 98% – 100% | `SAFE_AUTO_FIX` |
| 90% – <98% | `AUTO_FIX_WITH_LOG` |
| 75% – <90% | `REVIEW_RECOMMENDED` |
| 60% – <75% | `USER_CONFIRMATION_REQUIRED` |
| < 60% | `ABSTAIN` |

Thresholds are configurable; the **band ordering is not**.

---

## AD-006 — Detection confidence is not repair confidence

> **Status: Implemented**

This is the single most important decision in this document.

A confident diagnosis does not imply a confident cure.

```
outlier_detected            confidence 0.99   <- detection
delete_that_row             confidence 0.30   <- repair
=> action: REVIEW, not SAFE_AUTO_FIX
```

Therefore:

- `Issue.detection_confidence` — how sure we are the problem is real.
- `TreatmentCandidate.repair_confidence` — how sure we are *this specific fix* is correct.

**The confidence ladder in AD-005 is applied to `repair_confidence` only.**
`detection_confidence` governs whether an issue is reported at all; it never
authorizes a repair.

Worked examples from the stress fixture:

| Finding | Detection | Repair | Class |
|---|---|---|---|
| Trailing whitespace in `Cash ` | 1.00 | 1.00 | `SAFE_AUTO_FIX` |
| `31/02/2025` is invalid | 1.00 | no correct date is inferable | `AMBIGUOUS` |
| `employee_count = 999999` is sentinel | 0.97 | 0.55 (missing? typo? real?) | `USER_CONFIRMATION_REQUIRED` |
| Conflicting `invoice_id` payloads | 1.00 | 0.10 (which row survives?) | `DO_NOT_TOUCH` |
| `Tourismm` to `Tourism` | 0.98 | 0.93 | `USER_CONFIRMATION_REQUIRED` (demoted, AD-007) |

---

## AD-007 — Auto-fix eligibility is multi-factor, and demotion-only

> **Status: Implemented**

Eligibility is **not** a confidence lookup:

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

Algorithm, in two stages.

**Stage 1 — routing.** These name *who must decide* rather than *how confident
we are*, so they short-circuit. Their precedence is fixed, which keeps the
outcome order-independent.

| Condition | Outcome | Precedence |
|---|---|---|
| Severity is BLOCKING | `DO_NOT_TOUCH` | 1 |
| No treatment candidate exists | `AMBIGUOUS` | 2 |
| Requires domain/business knowledge | `DOMAIN_RULE_REQUIRED` | 3 |

**Stage 2 — the autonomy ladder.** Start at the band from `repair_confidence`
(AD-005), then apply ceilings. **A ceiling may only lower the class, never raise
it.**

| Condition | Effect |
|---|---|
| Operation is irreversible | cap at `USER_CONFIRMATION_REQUIRED` |
| Information-loss risk HIGH | cap at `USER_CONFIRMATION_REQUIRED` |
| Conflicting evidence between candidates | cap at `USER_CONFIRMATION_REQUIRED` |
| Material statistical impact | cap at `REVIEW_RECOMMENDED` |

**Why two stages.** `RepairClass` needs a total order for demotion to work, so
`DOMAIN_RULE_REQUIRED` necessarily sits somewhere on that ladder. Under a single
demotion-only pass, a low-confidence repair that a domain expert could settle
immediately would land in `AMBIGUOUS` — the most actionable label lost to the
least. Routing first keeps "nobody can decide this" and "the right person can
decide this instantly" distinct.

Row deletion, column deletion, outlier removal, entity merge and category merge
are **irreversible by definition** and can therefore never reach `SAFE_AUTO_FIX`,
regardless of confidence.

---

## AD-008 — Geographic reference is an entity graph, not a lookup table

> **Status: Partial - the graph exists; installable reference packs planned**

The `Marrakech`/`Marrakesh` finding proved a static `country -> [city]` map is
insufficient; it silently under-reported mismatches (24 instead of 26).

Required model:

```
CanonicalEntity
    +-- aliases            Marrakesh, Marrakech
    +-- transliterations   Marrakech (fr), Marrakesh (en)
    +-- language variants  Arabic script forms
    +-- historical names
    +-- administrative parent -> Country
```

Resolution returns `(canonical_id, match_kind, confidence)`. An unresolved city is
reported as `UNKNOWN_ENTITY` — never silently treated as consistent. Geography
packs are plugin-loadable and versioned.

---

## AD-009 — Negative acceptance tests are first-class

> **Status: Implemented**

False positives are the primary failure mode of automated cleaning tools. The
suite therefore asserts what the library must **not** flag, with the same weight
as what it must find.

Frozen negative controls from the fixture:

| Control | Rows | Must not be flagged as |
|---|---|---|
| `Algérie` (e-acute, U+00E9) | 1 | Unicode corruption — it is correct French |
| `Overdue` + `payment_date` present | 97 | State contradiction — late payment is legitimate |
| Country/currency mismatch | 22 | Hard error — must be `CONTEXTUAL_WARNING` |
| `status = Pending` + `payment_date` missing | ~326 | Suspicious missingness — structurally expected |
| Large-but-real `annual_revenue` | — | Sentinel |

A build that detects all 14 issue categories but flags `Algérie` is a **failed**
build.

---

## AD-010 — Build order

> **Decision status: Accepted.**
>
> **Implementation state when this was written (v0.6):** steps 1-13 done.
> Core complete; publishing covering Markdown, JSON, HTML, PDF, PPTX and
> notebook; the Studio carrying the visual analytics foundation -- one shared
> interaction state (AD-015), stable row identity, drag-and-drop composition
> with a keyboard equivalent, linked brushing and cross-filtering, the smart
> grid and the treatment sandbox (AD-016). Absent at that point: the visual
> workflow canvas, faceting and multi-series composition, entity resolution,
> multi-backend, and time-series and panel diagnostics.
>
> **Current implementation state (1.0.0):** the staged build order is complete
> through the 1.0 release. The visual workflow builder and pipeline canvas
> (AD-018), faceting and multi-series composition (AD-019), entity resolution,
> and time-series and panel diagnostics (AD-021) all landed; see those records
> for their final designs. Multi-backend execution remains the one item from
> the original order that has not been built.
>
> The paragraph above is kept rather than rewritten: the reasoning in an
> architecture record is only useful if a reader can see what was true when
> the decision was made. Overwriting it would leave the decision looking
> obvious in hindsight, which is exactly the information a record exists to
> preserve.

Frontend work does not begin until Core is stable. If the UI is built first, the
UI dictates the architecture instead of the reverse.

```
1. Architecture decisions          <- this file
2. Confidence / safety policy      <- AD-005, AD-006, AD-007
3. Public API semantics            <- AD-002
4. Stress-test baseline tests      <- red
5. Detector interfaces
6. Detectors                       <- red to green
7. Issue classification
8. Triage engine
9. Auto repair engine
10. Guided engine
--- core stable ---
11. Reporting
12. Studio
```

The Final Superset Checklist (plan §124) is the **v1.0** gate, not the v0.1 gate.
v0.1 scope is plan §40.

---

## AD-013 — The report and the Studio are separate products

> **Status: Implemented**

They were one artifact, and the compromise hurt both: an archival file cannot
carry an analysis UI, and an analysis UI should not be constrained by what will
still render in ten years.

| | HTML report | Studio |
|---|---|---|
| Purpose | Archive, email, attach to a paper | Analyse and decide |
| Charts | Static SVG | Static SVG plus interaction |
| Scripts | Navigation only | Grid, explorer, stages, tooltips |
| Size | ~35 KB | 0.5-1 MB, and capped |
| Guarantee | Renders correctly with scripts disabled | Needs a browser |

The Studio's size is a design constraint, not an accident: every precomputed
chart is markup that ships inside the file, so the full cross product of a
twenty-column frame produced a 3.2 MB workspace nobody could email. Both chart
catalogues are capped, dense scatters drop per-point hover text and selection,
and a test fails if the page grows past its budget. What the caps exclude is
reachable through the Python line the builder prints.

Both render the **same** `ChartSpec` objects and the same EDA numbers, so a
figure cannot differ between them. `HtmlDocument(interactive=...)` is the
switch — a *document*-level one, deciding whether the script layer is included
at all, distinct from the per-chart ceiling in AD-014. It defaults to off,
because the archival guarantee is the one that silently breaks.

This does not settle the frontend fork in AD-010. A richer Studio may later
need a real frontend stack; the archival report never will, and separating them
is what makes that choice free.

---

## AD-014 — Interaction is a ceiling on the spec, not a renderer's opinion

> **Status: Implemented**

Interaction and animation are two axes, and collapsing them into one flag is
how a library ends up calling hover text "interactive". A chart can be:

| | not animated | animated |
|---|---|---|
| **not interactive** | a printed figure | stage frames as small multiples |
| **interactive** | a scatter you can lasso | a walkthrough you can also zoom |

All four are real, so all four must be expressible. `ChartSpec` therefore
carries `interaction: Interaction` (`NONE`, `HOVER`, `EXPLORE`) and
`animation_field` separately, and neither reads the other.

`interaction` is a **ceiling**, not a prediction. It says the most a reader may
do; each renderer delivers the lesser of that and what its medium allows:

| Renderer | Medium ceiling |
|---|---|
| Matplotlib | `NONE` — paper cannot hover |
| SVG | `HOVER` — `<title>` elements, no scripts |
| Plotly | `EXPLORE` — zoom, pan, box and lasso select |

So the default is `EXPLORE` — the most a chart could ever offer — and print
lowers it once with `spec.as_static()` rather than every screen chart having to
opt in, and rather than each renderer inventing its own rule about what print
means.

The previous field was `interactive: bool = True`, read by nothing. A field
that defaults to a claim no static rendering can honour, and that no code
consults, is the same class of dishonesty as an enum declaring a mark nothing
can draw. Both are now asserted rather than documented, in
`tests/test_architecture_invariants.py`.

---

## AD-015 — One interaction state, defined in the core

> **Status: Implemented**

The grid, the charts, the visual builder, the treatment sandbox and the
cleaning story all answer the same four questions: what is filtered, what is
selected, which chart is showing, which treatment is being weighed. Built
surface by surface, each grows its own answer, and reconciling four
almost-identical state models afterwards is the work nobody schedules.

So `StudioState` is defined once, in `core/state.py`, before any of the five
visual features — not in the page:

```text
StudioState
├── identity          StableRowIndex -- what a row *is*
├── fingerprint       which dataset this view belongs to
├── filters           FilterClause[] -- narrows a view, drops nothing
├── selection         stable row keys + whether they will survive
├── active_specs      what is showing
├── current_stage     where the walkthrough is
├── pending_treatment what is being considered, never what was applied
└── review_context    the semantic context the scan ran with
```

It is a plain serialisable value, so the browser can send a view back, Python
can construct the same view without a browser, and a view can be diffed,
logged and replayed like everything else.

### Selections are keys, never positions

Drop three rows, sort by a column, or reset an index, and row 47 is a
different row. Every linked-selection bug of that kind looks identical from
the outside: the highlight lands on the wrong records, and nobody notices,
because wrong rows still look like rows.

`StableRowIndex` therefore derives the strongest identity a frame offers —
its unique index, else a content hash, else position — and **says which one it
got**. A positional identity is not hidden; it is reported as not surviving
transformation, the same way `Fidelity` reports that a chart was sampled. The
page cannot override this: `StudioState.from_dict` takes the identity from the
frame in hand, not from the payload.

Chart marks carry the keys they were computed from, which is what makes
brushing a selection rather than a highlight.

### What the page may compute

| The page may | The page may not |
|---|---|
| Filter, select, count, highlight | Compute any statistic |
| Sort and hide columns | Aggregate, impute or repair |
| Show a precomputed spec | Build a spec of its own |

The moment a browser computes a number a reader might quote, that number has
to be reconciled with the Python one forever afterwards. So the visual builder
chooses among **precomputed** compositions, and a combination nobody
precomputed is answered with the one line of Python that produces it. That is
honest about what a single file can do (AD-013), rather than shipping a second
and worse aggregation engine in JavaScript.

---

## AD-016 — Preview is not Apply

> **Status: Implemented**

Choosing between three candidate repairs by reading their names and
confidences is choosing blind. The sandbox shows what each would *do*: how
many cells move, which values, and what it costs the statistics the reviewer
was about to reason from.

```text
Issue -> Candidates -> Preview -> Comparison -> chosen candidate -> Core operation
```

A `TreatmentPreview`:

- is computed against a copy and leaves the caller's frame untouched;
- **never enters the audit log** — considering a repair is not a thing that
  happened to the data, and a log that records deliberation alongside action
  stops being a record of what changed;
- **has no `apply()`**. Committing goes back through guided mode, the only
  path that records who decided and why.

That last point is deliberate friction. A sandbox with a commit button is a
second way to change data, and the second way is always the one that skips the
audit.

Preview and apply are not two implementations that agree — they are the *same*
operation over a copy, and a test asserts that previewing a treatment and
executing it produce an identical frame and an identical cell count. A preview
also records the fingerprint of the frame it was computed against, because the
same treatment after three other repairs touches a different number of cells,
and a sandbox that does not say which frame it saw invites a reader to compare
two numbers that were never about the same data.

### Imputation always improves completeness

That is what it is for. A sandbox reporting only completeness would recommend
imputing everything, so every preview reports the spread and the distinct
count beside it — what the repair *spends*, not only what it buys.

---

## AD-017 — Portable Studio and Live Studio

> **Status: Portable implemented. Live is a named plan, not a hidden intention.**

The Studio is a single self-contained HTML file, and that buys a great deal:
no build step, no port, no process left running, and it works identically in a
notebook, a browser, an emailed archive and a locked-down machine.

It costs one thing, and the cost is real: **the page cannot run pandas.** So
the visual builder composes from charts precomputed in Python, and a pairing
nobody precomputed is answered with the line of Python that builds it.

The alternative — a JavaScript aggregation engine inside the page — was
rejected, not deferred. The moment a browser computes a number a reader might
quote, that number has to be reconciled with the Python one forever
afterwards, and every disagreement between them is a bug nobody can reproduce
from the notebook. A second analytical engine is the most expensive thing this
project could ship.

The way out is not a bigger page. It is a second *mode*:

| | Portable Studio | Live Studio |
|---|---|---|
| **Status** | Implemented | Planned |
| Delivery | One HTML file | Connected to a Python session |
| Composition | From precomputed specs | Any composition, on demand |
| Aggregation | In Python, ahead of time | In Python, on request |
| Large data | Capped and disclosed | Backend queries |
| Workflow execution | No | Yes |
| Survives without Python | Yes | No |

Both would share the *same* `StudioState`, `Composition`, `ChartSpec` and core
operations. Only the transport differs — whether a composition is answered
from a catalogue built earlier or from a call made now. That is what lets
SmartPrep reach general visual exploration without ever embedding a second
engine: the general case becomes a round trip to the real one.

Until Live exists, the limitation is stated where a reader meets it — in the
builder panel, in `smartprep.capabilities`, and in the README — rather than
left to be discovered by trying a pairing that does not appear.

---

## AD-018 — A workflow node is a filter, not an implementation

> **Status: Implemented**

A visual pipeline is the point at which a data tool usually acquires a second
execution engine. The canvas grows its own idea of what "repair missing
values" means, the Python API keeps the original, and from then on the two
answers have to be reconciled by hand forever.

So a node implements nothing:

```text
Visual node -> serializable specification -> the same RepairPlan -> RepairExecutor
```

Each stage selects the subset of operations `auto_prepare` would have run for
its own issue categories, and hands that subset to the same executor, writing
to the same audit log. Running every stage is therefore not *similar* to
automatic mode — it is the same operations, and a test asserts the frames and
the audit records match.

What the workflow adds is control and visibility, not capability: disable a
stage, reorder within the rules, see what each one cost, export the whole
thing as Python.

### The order is not a convention

Types are repaired before ranges because a range check on the string
`"1,200.50"` is meaningless. Duplicates are resolved after categories because
`Marrakech` and `Marrakesh` are not duplicates until they are the same word. A
canvas that let a reader arrange these freely would let them arrange a wrong
answer, so `move()` and `connect()` refuse arrangements that invert the order
and say why.

### Every repair belongs to exactly one stage

A repair owned by no stage would never run, and the workflow would quietly do
less than automatic mode while looking complete. So an operation that maps to
no stage raises rather than being skipped, and a test asserts every
`IssueCategory` has a home.

---

## AD-019 — Faceting happens on the spec, not in the renderers

> **Status: Implemented**

`ChartSpec.panels()` splits a faceted spec into one ordinary spec per group.
Every backend then draws small multiples with the code it already had, so a
faceted view and an unfaceted one cannot disagree about the same numbers, and
three implementations of faceting never exist to drift apart.

Three consequences fall out of doing it there:

* **Linked selection across facets is free.** A panel is a filter over
  `spec.data`, so its marks keep their row keys, and brushing in one panel
  highlights the same rows in all of them.
* **The panels share one scale**, computed once on the spec. A grid of charts
  with private axes is a grid nobody may compare, and comparing them is the
  only reason to draw a grid.
* **Faceting an aggregate is refused.** Aggregated rows no longer line up with
  the frame, so the groups cannot be attached honestly, and attaching wrong
  ones would put points in panels they do not belong to — a failure invisible
  from outside, because a point in the wrong panel still looks like a point.

Twelve panels is the cap. More cannot be compared at a glance, which is the
only thing small multiples are for.

---

## AD-020 — An encoding channel is honoured everywhere, or refused

> **Status: Implemented**

This is the generalisation of a mistake this project kept rediscovering:

| Channel | What it claimed | What it did |
|---|---|---|
| `Mark` enum | eleven marks | three had no renderer |
| `interactive` | every chart interactive | nothing read the field |
| `color` | a colour channel | one mark, one backend |
| `facet` | small multiples | nothing drew it |
| `size` | a size channel | nothing drew it |

Each was found by a different reviewer, months apart, and each was the same
failure: a declaration nothing honoured and nothing refused.

The rule now: **a channel a spec declares must change what every renderer
draws, or be refused with a reason.** Accepted-and-quietly-ignored is the one
option that misleads, because a reader who sets it sees a chart that looks
deliberate. A test enumerates the channels on `ChartSpec` and fails on any
that is neither honoured nor refused.

`size` maps value to **area**, not radius, because area is what the eye reads
as magnitude; scaling the radius makes a doubled value look four times larger,
which is the most common way a size channel lies.

---

## AD-021 — Domain diagnostics produce ordinary findings

> **Status: Implemented**

Time-series, panel-data and entity-resolution checks each had an obvious
shape: their own report type, their own severity language, their own review
screen. Three of those and the library has four review queues, four audit
trails and four places a reviewer has to learn.

So they produce ordinary `Issue` objects. A missing quarter, an unbalanced
panel and a probable duplicate customer go through the same triage, the same
confidence ladder, the same guided queue and the same audit as a mistyped
date. The reports exist to describe *shape* — cadence, completeness,
within-variance — not to hold decisions.

### None of them repair anything

Each is a decision requiring knowledge the data does not contain:

| Finding | Why the library will not decide |
|---|---|
| A gap in a series | Filling it and dropping it give different answers, and a closed market has no Sunday |
| An unbalanced panel | Usually fine, occasionally a survivorship filter, and the counts cannot tell you which |
| A constant-within regressor | Not an error — a fact about what that variable can identify |
| A probable duplicate entity | Two branches of one company and one company twice look identical from the fields |

The single exception is chronological sorting, which changes no value and
loses nothing.

### Similarity orders a queue; it does not decide

The temptation in record linkage is a merge threshold. That produces a number
nobody can defend: at 0.85 two branches become one, at 0.86 they stay apart,
and a dataset's conclusions turn on a constant somebody chose on a Tuesday.
The score orders the review queue so the obvious pairs come first. Every pair
still gets decided.

Blocking makes the comparison tractable and costs recall, so the report states
how many pairs were never compared — a linkage run that shows only what it
found reads as exhaustive.

### Weak variation is worse than none

No within-entity variation drops a term visibly: the estimator refuses it and
the analyst notices. *Weak* variation keeps the term and returns a
coefficient identified by almost nothing, which looks exactly like an answer.
That is why it has its own finding rather than being folded into the first.

---

## AD-011 — Naming and packaging

> **Status: Implemented**

| Placeholder | Value |
|---|---|
| `{{PYPI_PACKAGE_NAME}}` | `smartprep` |
| `{{IMPORT_NAME}}` | `smartprep` |
| `{{LICENSE}}` | `Apache-2.0` |

PyPI name availability must be confirmed before first publish.

Distribution uses **extras**, not ten separate packages:
`smartprep[viz]`, `[ml]`, `[privacy]`, `[spark]`, `[all]`.
The multi-package split (master §35) is deferred past v1.0.

### License: Apache-2.0 (frozen)

The package metadata, `LICENSE` and `NOTICE` all committed to Apache-2.0 while
this section still said the choice was open. That contradiction is resolved in
favour of what shipped.

The two candidates were ecosystem-compatible; the material difference is patent
protection:

- **MIT** — maximally permissive, shortest text, no express patent grant.
- **Apache-2.0** — express patent grant plus a patent-retaliation clause; the
  choice of pandas-adjacent infrastructure projects (PyArrow, Ibis, PyGWalker,
  DataProfiler are all Apache-2.0).

**Apache-2.0 is chosen**, because the library implements algorithmic methods and
an express patent grant reduces downstream adoption friction for institutional
users. Changing it now would require re-licensing every release already built.

---

## AD-012 — Source document hygiene

> **Status: Advisory**

The reference plan has duplicate section numbers (two each of §81–§85, §100,
§145–§148) and a gap at §127–§137. Until it is renumbered, all cross-references in
code and specs must cite **section title + line number**, never the bare number.

---

## Conflict resolution index

| # | Conflict | Resolved by |
|---|---|---|
| 1 | Two confidence ladders | AD-005 |
| 2 | Default mode ambiguity | AD-001, AD-002 |
| 3 | Duplicate section numbers | AD-012 |
| 4 | Unfilled placeholders | AD-011 — all three now frozen |
| 5 | Missing stress fixture | Closed — `data_project.xlsx` verified |
| 6 | MVP vs superset gate | AD-010 |
| 7 | Frontend fork undecided | AD-010 (deferred, not decided) |
| 8 | IR vs pandas-bound features | Deferred to Phase 7; `requires_materialization` reserved on the operation model now |
| 9 | Package split vs extras | AD-011 |
| 10 | Interactive conflated with animated | AD-014 |
| 11 | Four surfaces, four state models | AD-015 |
| 12 | A sandbox that can commit | AD-016 |
| 13 | Browser aggregation vs portability | AD-017 |
| 14 | Four documents claiming what exists | `smartprep.capabilities` |
| 15 | A canvas that executes | AD-018 |
| 16 | Faceting written three times | AD-019 |
| 17 | Channels declared but not drawn | AD-020 |
| 18 | Four review queues | AD-021 |
