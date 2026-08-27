# SmartPrep v0.6.0.dev0 — Full Technical Review, Remaining Gaps, Corrections & Roadmap

**Project:** SmartPrep  
**Version reviewed:** `0.6.0.dev0`  
**Repository:** https://github.com/merwanroudane/smartprep  
**Author:** Dr Merwan Roudane  
**Review type:** Source-package inspection + test execution + architecture/documentation consistency review  
**Overall assessment:** **9.2 / 10** against the intended SmartPrep vision.

---

# 1. Executive conclusion

`v0.6.0.dev0` is a major step beyond `v0.5.1`.

The central objective proposed for v0.6 — a shared visual analytics foundation — is substantially implemented:

- `StudioState`
- stable row identity
- drag-and-drop visual composition
- keyboard-equivalent composition
- linked brushing
- cross-filtering
- Smart Grid 2.0 foundations
- Treatment Sandbox
- one shared state across Studio panels
- architecture invariants protecting the new interaction layer

The most important architectural success is that these capabilities were **not implemented as independent UI islands**. They share Core state and preserve the earlier rule:

```text
Core != UI
```

This significantly improves the long-term maintainability of SmartPrep.

The package is nevertheless **not yet the complete final SmartPrep platform**. The largest remaining gaps are now concentrated in:

1. Visual Workflow Builder / Pipeline Canvas
2. Faceting and richer multi-series visual composition
3. Fully general visual grammar rather than precomputed browser compositions
4. Entity Resolution
5. Time-Series diagnostics/Studio
6. Panel-data diagnostics/Studio
7. Multi-backend execution
8. Advanced semantic/domain packs
9. Benchmark suite
10. Production observability and plugin ecosystem

---

# 2. Verification performed

The distributed source package was inspected directly.

The full test suite available inside the uploaded sdist was executed.

Result:

```text
491 passed
51 skipped
0 failed
```

The skipped tests explicitly require the real stress-test workbook:

```text
data_project.xlsx
```

which is intentionally not distributed in the sdist.

Therefore the skips are not test failures.

The source package contains approximately:

```text
117 files under src/smartprep
16,270 Python source lines
```

The package remains marked:

```text
Development Status :: 3 - Alpha
```

which is appropriate at this stage.

---

# 3. Tooling verification note

The test suite itself passed.

`ruff` and `mypy` could not be independently re-run in the review runtime because those executables were not installed in that environment.

This is **not evidence that the project fails ruff/mypy**. It only means this review independently verified pytest but did not independently reproduce the lint/type-check claims.

The project declares both tools correctly in the `dev` extra.

---

# 4. Current component scores

| Area | Score |
|---|---:|
| Architecture | **9.7/10** |
| Testing / invariants | **9.6/10** |
| Cleaning Core | **9.3/10** |
| Auto + Guided Preparation | **9.3/10** |
| Validation / Contracts | **9.1/10** |
| Audit / Replay / Reproducibility | **9.4/10** |
| EDA | **8.5/10** |
| Static Visualization | **8.7/10** |
| Interactive Visualization | **8.8/10** |
| Linked Analytics | **9.0/10** |
| Visual Builder | **8.3/10** |
| Smart Grid | **8.4/10** |
| Treatment Sandbox | **8.8/10** |
| Animation / Cleaning Story | **7.2/10** |
| Studio overall | **8.5/10** |
| Reporting / Publishing | **8.9/10** |
| Documentation | **8.6/10** |
| Entity Resolution | **2.0/10** |
| Time-Series / Panel | **4.0/10** |
| Multi-backend | **2.5/10** |
| Production monitoring | **3.0/10** |

These scores measure completeness against the **full intended SmartPrep platform**, not merely whether the currently documented APIs work.

---

# 5. Major v0.6 achievement — Shared interaction state

This was the correct architectural decision.

The project now has:

```text
StudioState
```

as a shared representation of interaction state.

Conceptually:

```text
Dataset
   ↓
StudioState
   ├── Filters
   ├── Row Selection
   ├── Column Selection
   ├── Active Charts
   ├── Current Stage
   ├── Pending Treatment
   └── Review Context
```

This is substantially better than implementing separate state models for:

- Grid
- Chart Builder
- Plotly charts
- Sandbox
- Stage walkthrough

The architecture should preserve this decision permanently.

---

# 6. Stable Row Identity

**Status: Implemented**

`StableRowIndex` addresses an important problem:

```text
sort
filter
drop rows
reset index
```

can make positional row identity unsafe.

SmartPrep now explicitly derives identity and reports its strength.

This is essential for:

- linked brushing
- selections
- auditability
- cross-filtering
- treatment review

This should remain a first-class Core concept.

---

# 7. Visual Builder

**Status: Implemented foundation**

The builder now supports visual composition and a keyboard-accessible route.

This closes one of the largest gaps identified in the v0.5.1 review.

The key positive architectural property is:

```text
Visual Builder
      ↓
Composition
      ↓
ChartSpec
      ↓
Renderer
```

rather than:

```text
Visual Builder
      ↓
Plotly-specific code
```

That separation must not regress.

---

# 8. Important limitation of the current Visual Builder

The current builder is **not yet a fully general PyGWalker-style visual grammar**.

The architecture record correctly states that the page chooses among compositions/specifications already produced by Python.

The browser does not contain a second pandas-like aggregation engine.

This is a good safety decision, but it creates a current product limitation:

> A composition the page has not been given in advance cannot necessarily be constructed entirely inside the standalone HTML page.

This limitation should be communicated clearly.

---

# 9. Faceting — partial representation, incomplete product support

The code model already contains:

```python
facet: str | None
```

inside `Composition`, and `ChartSpec` also has a facet encoding concept.

However, the architecture documentation correctly lists:

```text
faceting
```

as still absent from the complete builder experience.

This is not a contradiction in the Core model.

It means:

```text
representation exists
!=
full rendering/composition experience exists
```

Recommended action:

- complete facet semantics
- add renderer parity tests
- expose facet shelf in Studio
- define small-multiple layout behavior
- define high-cardinality refusal policy
- define linked-selection behavior across facets

---

# 10. Multi-series composition

**Status: Missing / incomplete**

The next visual layer should support richer multi-series composition.

Examples:

```text
X = date
Y = revenue
Color = region
```

or:

```text
X = category
Y = mean(value)
Group = segment
```

Required:

- series encoding
- legend behavior
- aggregation semantics
- missing-series handling
- category caps
- renderer parity
- linked brushing semantics

---

# 11. Linked Brushing

**Status: Implemented foundation**

This is one of the strongest improvements in v0.6.

Chart marks can carry row keys and selections can correspond to actual underlying observations.

This moves SmartPrep beyond:

```text
interactive chart
```

toward:

```text
linked analytical environment
```

The distinction is important.

---

# 12. Cross Filtering

**Status: Implemented foundation**

Filtering is now connected to the shared Studio state.

The architectural rule should remain:

```text
Filter changes a view
!=
Filter deletes data
```

This is especially important in a cleaning platform.

A visual filter must never silently become a destructive cleaning operation.

---

# 13. Smart Grid 2.0

**Status: Major foundation implemented**

The Grid is now part of the shared interaction architecture.

Remaining improvements should include, where not already complete:

- richer multi-column filtering
- grouping
- aggregation
- pivoting
- column pinning
- column resizing
- hide/show
- advanced search
- row history
- before/after cell inspection
- virtualization for very large tables
- more direct selected-row analytical actions

Any actual data edit must continue to route through auditable Core operations.

---

# 14. Treatment Sandbox

**Status: Major foundation implemented**

This is one of SmartPrep's strongest differentiating ideas.

The correct safety rule is implemented conceptually:

```text
Preview != Apply
```

The Sandbox should remain unable to become a hidden second mutation path.

Correct lifecycle:

```text
Issue
 ↓
Candidate Treatments
 ↓
Preview
 ↓
Compare
 ↓
User Decision
 ↓
Guided/Core Operation
 ↓
Audit
 ↓
Validation
```

---

# 15. Treatment Sandbox — next expansion

The Sandbox can eventually become much richer.

For missing values, compare:

```text
Original
Median
Group Median
KNN
Iterative
MICE
```

For outliers:

```text
Keep
Flag
Cap
Winsorize
Transform
Group-specific treatment
```

For category normalization:

```text
Original
Case normalization
Alias mapping
Fuzzy grouping
Canonical mapping
```

Comparison metrics should include:

- cells changed
- completeness
- distribution shift
- mean
- median
- variance
- quantiles
- skewness
- distinct count
- correlation preservation
- information-loss risk
- runtime
- repair confidence

---

# 16. Architecture invariants

The new tests protecting architectural agreements are extremely valuable.

The following rules should remain permanent regression invariants:

```text
Core != UI
ChartSpec = visualization source of truth
Interaction != Animation
Preview != Apply
Filter != Delete
Selection != Mutation
Cleaning != Preprocessing
Detection Confidence != Repair Confidence
Cleaned != Verified
```

---

# 17. Documentation defect #1 — README contradiction

This is the clearest concrete defect found in the v0.6 package.

The README capability table says:

```text
sp.studio() — grid, builder, sandbox, brushing, stages | Implemented
```

but shortly afterward says:

```text
Drag-and-drop composition, linked brushing | Not yet
```

and the explanatory paragraph also describes drag-and-drop/brushing as not yet existing.

This is now false.

The source code, tests, CHANGELOG and AD-015 show that these capabilities were implemented in v0.6.

### Required correction

Remove:

```text
Drag-and-drop composition, linked brushing | Not yet
```

and rewrite the Studio paragraph.

Recommended wording:

```text
The v0.6 Studio implements the visual analytics foundation:
shared interaction state, stable row identity, drag-and-drop composition
with a keyboard equivalent, linked brushing, cross-filtering, Smart Grid
and Treatment Sandbox.

It is not yet the final Studio. Visual Workflow/Pipeline Canvas,
faceting, richer multi-series composition and fully general composition
remain under development.
```

---

# 18. Documentation defect #2 — duplicate capability rows

The README contains both:

```text
Visual workflow / pipeline canvas | Not started
```

and:

```text
Visual workflow canvas | Not yet
```

These describe essentially the same missing capability.

Use one row.

Recommended:

```text
Visual Workflow Builder / Pipeline Canvas | Planned
```

---

# 19. CHANGELOG defect — duplicated Planned entries

The `Unreleased -> Planned` section repeats these entries:

- Entity resolution and record linkage
- Multi-backend execution
- Time-series and panel diagnostics
- Benchmark suite

They appear twice.

### Required correction

Deduplicate the list.

Recommended final list:

```text
- Visual Workflow Builder and Pipeline Canvas
- Faceting and multi-series composition
- Entity Resolution and Record Linkage
- Multi-backend execution
- Time-Series and Panel diagnostics
- Benchmark Suite
```

---

# 20. Documentation consistency rule

The project has reached a size where documentation consistency should itself be tested.

Recommended future test:

```text
README capability matrix
↔
feature registry
↔
public API
↔
architecture status
```

A lightweight machine-readable capability registry could prevent contradictions.

Example:

```python
Capability(
    name="linked_brushing",
    status="implemented",
    since="0.6.0.dev0"
)
```

Docs could eventually be generated from it.

---

# 21. Remaining Gap #1 — Visual Workflow Builder

**Priority: P0 for v0.7 product development**

This is now the largest missing visual capability.

Target:

```text
[Load]
   ↓
[Scan]
   ↓
[Type Repair]
   ↓
[Missing]
   ↓
[Categories]
   ↓
[Duplicates]
   ↓
[Outliers]
   ↓
[Validate]
   ↓
[Report]
```

Each visual node must correspond to a real Core operation.

Required:

- add node
- remove
- disable
- reorder
- inspect
- edit parameters
- connect dependencies
- prevent invalid orders
- execute
- replay
- export Python
- export YAML/JSON
- audit equivalence

---

# 22. Remaining Gap #2 — Pipeline Canvas

The Pipeline Canvas should expose execution, not just design.

For each node:

- status
- elapsed time
- rows affected
- cells affected
- issues resolved
- issues created
- warnings
- health-score delta
- validation result
- audit link

---

# 23. Visual Workflow safety invariant

The Workflow UI must never become a separate execution engine.

Required architecture:

```text
Visual Node
     ↓
Serializable Operation Specification
     ↓
Core Pipeline
```

The equivalent code-first pipeline must produce the same result.

Add an invariant test:

```text
Visual workflow replay
==
Python pipeline replay
```

---

# 24. Remaining Gap #3 — Full visual grammar

The current precomputed-composition strategy is appropriate for self-contained HTML.

However, the long-term Studio should support a broader visual grammar.

Potential fields:

```text
X
Y
Color
Size
Shape
Facet
Group
Aggregation
Filter
Sort
Tooltip
Animation
```

This can be solved through two Studio modes:

### Portable HTML Studio

Uses precomputed safe compositions.

### Live Python Studio

Communicates with the Python kernel/server and can request new compositions dynamically.

This separation would preserve:

```text
one analytical engine
```

without embedding pandas logic in JavaScript.

---

# 25. Recommended future Studio architecture

Consider explicitly defining two execution modes:

```text
Studio Portable Mode
```

- self-contained HTML
- no Python server
- precomputed compositions
- portable
- archivable

and:

```text
Studio Live Mode
```

- connected to Python
- dynamic aggregation
- arbitrary supported compositions
- large-data querying
- richer workflows

This could substantially outperform the limitations of purely static exported explorers.

---

# 26. Remaining Gap #4 — Entity Resolution

Not started at the intended level.

Required future capabilities:

- blocking
- candidate generation
- fuzzy similarity
- multi-field comparison
- candidate ranking
- pair review
- merge proposal
- canonical entity
- confidence
- audit
- replay

Example:

```text
Record A | Record B | Similarity | Evidence | Recommendation
```

---

# 27. Entity Resolution should reuse Guided Mode

Do not create a separate decision system.

Architecture:

```text
Candidate Pair
   ↓
Evidence
   ↓
Guided Decision
   ↓
Merge / Keep Separate / Map
   ↓
Audit
```

---

# 28. Remaining Gap #5 — Time-Series diagnostics

The preprocessing advisor knows about a time-series goal, but this is not equivalent to a Time-Series Studio.

Required:

- datetime identification
- frequency inference
- missing periods
- duplicate timestamps
- irregular spacing
- ordering
- timezone checks
- temporal gaps
- resampling diagnostics
- rolling diagnostics
- seasonal views
- time-aware missingness
- temporal leakage protection
- chronological split

Later:

- ACF/PACF
- stationarity-oriented diagnostics
- structural-break annotations

SmartPrep should diagnose preparation issues without becoming a forecasting package.

---

# 29. Remaining Gap #6 — Panel-data diagnostics

Especially important for econometrics.

Required:

- entity key
- time key
- duplicate entity-time
- balanced/unbalanced panel
- missing periods by entity
- within variation
- between variation
- constant-within-entity variables
- insufficient within variation
- panel completeness matrix
- entity trajectories
- chronology problems

---

# 30. Remaining Gap #7 — Multi-backend execution

Current execution remains primarily Pandas.

The optional extras currently declare:

```text
polars = []
duckdb = []
spark = []
```

This is intentionally honest because these layers are not implemented yet.

The next architecture should be:

```text
Semantic Operation
      ↓
Backend Planner
      ↓
Pandas / Polars / DuckDB / Arrow / Ibis / ...
```

Avoid copying the whole SmartPrep implementation for each backend.

---

# 31. Multi-backend rule — no silent Pandas fallback

Never silently materialize:

```text
Polars
DuckDB
Spark
Arrow
```

into Pandas when the operation could be expensive.

If fallback is necessary:

- explain it
- estimate memory
- estimate rows
- identify unsupported operation
- offer alternatives

---

# 32. Remaining Gap #8 — Advanced semantic cleaning

Continue building domain/locale-aware packs for:

- currencies
- units
- percentages
- decimal comma
- thousands separators
- phone
- email
- URL
- countries
- cities
- postal codes
- coordinates
- locale dates
- locale numbers

These should ideally be plugin-based and updateable.

---

# 33. Remaining Gap #9 — Unicode and multilingual cleaning

Extend support for:

- Unicode normalization
- confusables
- invisible characters
- control characters
- mojibake
- transliteration
- Arabic/French/English category aliases
- locale-aware case handling

The stress-test lesson about legitimate `Algérie` must remain a permanent negative control.

---

# 34. Remaining Gap #10 — Advanced anomaly system

Future optional methods:

- MAD
- robust z-score
- Isolation Forest
- LOF
- multivariate anomaly detection
- contextual anomalies
- collective anomalies
- group-aware anomalies
- time-aware anomalies
- optional PyOD integration

Important invariant:

```text
Anomaly detected
!=
Row should be deleted
```

---

# 35. Remaining Gap #11 — Missingness Lab

Expand missingness analytics toward:

- matrix
- heatmap
- co-missingness
- missingness patterns
- UpSet-like representation
- group-conditioned missingness
- target-conditioned missingness
- temporal missingness
- clustering

This is an area where SmartPrep can exceed `missingno`.

---

# 36. Remaining Gap #12 — Root Cause Analysis

Move from:

```text
8,423 invalid dates
```

to:

```text
8,423 invalid dates
82% originate from source X
first appeared after date Y
format changed from A to B
likely upstream schema/parsing change
```

This would be a major differentiator from profiling libraries.

---

# 37. Remaining Gap #13 — Rule Learning

Replay exists, but replay is not learning.

Possible future lifecycle:

```text
User Decision
 ↓
Candidate Rule
 ↓
Project Rule
 ↓
Reviewed Rule
 ↓
Organization Rule
```

Require:

- scope
- provenance
- confidence
- versioning
- conflict resolution
- human promotion

Never silently convert repeated decisions into organization-wide rules.

---

# 38. Remaining Gap #14 — Advanced Drift

Potential future additions:

- Wasserstein
- Jensen-Shannon
- MMD
- Cramér-von Mises
- classifier drift
- rolling drift
- online drift
- drift history
- reference versioning
- contributor attribution

Continue the existing principle:

```text
Drift should be attributed and explained
```

rather than merely returning a boolean.

---

# 39. Remaining Gap #15 — Production observability

Future production layer:

- scheduled validation
- data-health history
- schema history
- missingness history
- cleaning drift
- validation failure trends
- detector runtime
- pipeline runtime
- alerts
- version comparison

---

# 40. Remaining Gap #16 — Plugin ecosystem

The project needs a formal plugin model before v1.x scale.

Potential extension points:

- detector
- treatment
- semantic pack
- validation rule
- preprocessing method
- visualization
- report section
- backend

Need:

- entry points
- compatibility metadata
- SmartPrep version constraints
- optional dependencies
- backend support declarations
- plugin documentation

---

# 41. Remaining Gap #17 — Benchmark Suite

The real stress workbook is excellent as a regression fixture.

It is not yet a full benchmark suite.

Future:

```text
SmartPrepBench
```

Metrics:

- detection precision
- recall
- false-positive rate
- false-negative rate
- repair correctness
- information loss
- runtime
- memory
- report generation cost
- user decisions required
- backend parity

---

# 42. Competitor benchmarking

Benchmark by capability, not one artificial global score.

Compare against relevant tools:

### Profiling

- YData Profiling
- Sweetviz
- DataProfiler
- Skimpy

### Visual exploration

- PyGWalker
- D-Tale

### Cleaning

- PyJanitor
- AutoClean-style tools
- Skrub

### Validation

- Pandera
- Great Expectations

### Missingness

- missingno

### Preprocessing

- scikit-learn ecosystem
- Feature-engine
- category_encoders

The goal should be to demonstrate SmartPrep's integration advantage rather than claiming every competitor is inferior at every individual task.

---

# 43. Remaining Gap #18 — Large-data visual analytics

The Studio needs explicit scale policies.

Example:

```text
Small       → full data
Medium      → deterministic sample
Large       → aggregation/rasterization
Very large  → backend query
Streaming   → rolling/window view
```

Always expose:

```text
Fidelity
```

and sampling/aggregation notes.

---

# 44. Remaining Gap #19 — High-density rendering

Future options:

- rasterized scatter
- adaptive binning
- density aggregation
- Datashader-style integration

Useful when millions of observations would make SVG/Plotly marks impractical.

---

# 45. Remaining Gap #20 — Advanced preprocessing catalog

Potential future additions:

### Imputation

- KNN
- Iterative
- MICE
- multiple imputation
- miceforest-style
- matrix completion
- uncertainty-aware imputation
- panel/time-aware methods

### Encoding

- binary
- Base-N
- hashing
- WOE
- CatBoost
- GLMM
- James-Stein
- M-estimator
- MinHash
- GapEncoder

### Feature engineering

- datetime features
- interactions
- polynomial
- lag
- rolling
- expanding
- group/relational features

All must preserve leakage-safe fit/transform discipline.

---

# 46. Remaining Gap #21 — Reporting profiles

Recommended API:

```python
project.report(profile="executive")
project.report(profile="research")
project.report(profile="technical")
project.report(profile="audit")
project.report(profile="econometrics")
project.report(profile="ml")
```

A research report and executive report should not be identical.

---

# 47. Remaining Gap #22 — Themes and branding

Future report/Studio themes:

- logo
- author
- institution
- colors
- typography
- cover
- footer
- report metadata

Styling must remain separate from analytical semantics.

---

# 48. Remaining Gap #23 — Multilingual interface

High-value first languages:

```text
English
Arabic
French
```

Keep UI translations separate from Core logic.

---

# 49. Remaining Gap #24 — Documentation site

README is becoming too large to remain the only primary documentation surface.

Recommended:

```text
docs/
mkdocs.yml
```

Sections:

- Getting Started
- Concepts
- Scan
- Auto
- Guided
- EDA
- Visualizations
- Studio
- Sandbox
- Reporting
- Preprocessing
- Validation
- Contracts
- Privacy
- Drift
- API
- Developer Guide
- Plugin Guide
- Tutorials
- Migration Guides

---

# 50. Syntax Cookbook

Create:

```text
SYNTAX_COOKBOOK.md
```

The user should be able to find practical syntax immediately.

---

# 51. Function Catalog

Create:

```text
FUNCTION_CATALOG.md
```

For each public API:

- function/class
- signature
- purpose
- parameters
- return
- short example
- full docs
- stability

---

# 52. Documentation tests

README/docs examples should be executable wherever practical.

This is especially important now because v0.6 already contains a concrete README contradiction.

---

# 53. Capability registry recommendation

A machine-readable feature registry would reduce future contradictions.

Example conceptual model:

```python
Capability(
    id="linked_brushing",
    status="implemented",
    since="0.6.0.dev0",
    public_api=["studio"],
)
```

README tables and documentation badges could eventually be generated from this registry.

---

# 54. Accessibility — continue expanding

v0.5.1 and v0.6 established a strong baseline.

Future requirements:

- full keyboard navigation
- keyboard alternative for drag/drop
- screen-reader descriptions
- logical focus
- accessible dialogs
- accessible tooltips
- chart data-table alternatives
- non-color-only signals
- reduced-motion mode
- sufficient contrast

---

# 55. Security hardening

Continue testing:

- XSS
- unsafe HTML
- formula injection
- malicious filenames
- path traversal
- report injection
- embedded secrets
- unsafe external resources
- future plugin trust boundaries

---

# 56. Portable Studio vs Live Studio — recommended future decision

This is worth formalizing in an Architecture Decision Record.

## Portable Studio

```text
Single HTML
Precomputed specs
No server
Archivable
Shareable
Limited dynamic composition
```

## Live Studio

```text
Python-connected
Dynamic composition
Dynamic aggregation
Large-data backend queries
Workflow execution
Entity resolution
Full sandbox
```

Both should use the same:

```text
StudioState
Composition
ChartSpec
Core operations
```

This can allow SmartPrep to exceed PyGWalker-like exploration without embedding a second analytical engine in JavaScript.

---

# 57. Recommended v0.6.1 corrections

`v0.6.1` should be a small correction/hardening release, not another major feature release.

Recommended:

1. Fix README contradiction about drag-and-drop and linked brushing.
2. Remove duplicate Visual Workflow rows in README.
3. Deduplicate `CHANGELOG.md -> Planned`.
4. Add documentation/capability consistency test.
5. Add explicit facet status documentation.
6. Clarify Portable vs Live limitations if the distinction is accepted.
7. Expand renderer parity tests around future facet/series semantics.
8. Preserve all current architecture invariants.

---

# 58. Recommended v0.7 milestone

Suggested title:

> **SmartPrep v0.7 — Visual Workflow & Composition**

Primary goals:

```text
Visual Workflow Builder
+ Pipeline Canvas
+ Faceting
+ Multi-series
+ richer Visual Grammar
+ stronger Cleaning Story
```

---

# 59. Recommended v0.8 milestone

Suggested:

> **SmartPrep v0.8 — Domain-Aware Preparation**

Primary:

```text
Entity Resolution
+ Semantic Packs
+ Advanced Anomalies
+ Time-Series Studio
+ Panel Studio
```

---

# 60. Recommended v0.9 milestone

Suggested:

> **SmartPrep v0.9 — Scale & Backends**

Primary:

```text
Backend abstraction
+ Polars
+ Arrow
+ DuckDB
+ Ibis
+ Dask/Spark foundations
+ large-data visualization planner
```

---

# 61. Recommended v1.0 candidate

Before stable v1.0:

- public API freeze
- migration policy
- documentation site
- cookbook
- function catalog
- benchmark suite
- plugin architecture
- security review
- packaging matrix
- Python version matrix
- report quality review
- accessibility review
- large-data tests
- stable capability registry

---

# 62. Updated top priorities

After v0.6, the priorities have changed.

The previous list:

```text
Visual Builder
Linked Brushing
Treatment Sandbox
Smart Grid 2.0
Visual Workflow
```

is no longer correct because the first four are substantially implemented.

The new top priorities should be:

1. **Visual Workflow Builder / Pipeline Canvas**
2. **Faceting + Multi-Series + richer visual grammar**
3. **Entity Resolution**
4. **Time-Series + Panel Studio**
5. **Multi-backend architecture**

Secondary parallel priorities:

- Benchmark Suite
- Documentation Site
- Semantic Packs
- Plugin Ecosystem
- Production Observability

---

# 63. What should NOT be changed

Do not undo the following decisions:

### Do not move analytical logic into JavaScript

Keep:

```text
Python/Core = analytical truth
```

### Do not add a Sandbox commit shortcut

Keep:

```text
Preview != Apply
```

### Do not treat visual filtering as cleaning

Keep:

```text
Filter != Mutation
```

### Do not let renderers compute different statistics

Keep:

```text
EDA Result -> ChartSpec -> Renderer
```

### Do not silently guess domain repairs

Keep abstention.

### Do not merge Cleaning and Preprocessing

They solve different problems.

---

# 64. Definition of Done — Visual Workflow

The feature is complete when:

- nodes map to Core operations
- parameters are editable
- dependencies are explicit
- invalid ordering is prevented/explained
- workflow executes
- intermediate states can be inspected
- audit records match code-first execution
- Python export works
- config export works
- replay works
- workflow can be versioned

---

# 65. Definition of Done — Faceting

Complete when:

- facet field works end to end
- visual builder exposes it
- multiple renderers honor it
- layout rules exist
- high-cardinality policy exists
- linked selection works across facets
- fidelity is explicit
- serialization/replay works

---

# 66. Definition of Done — Multi-Series

Complete when:

- grouping/color series works
- legends are correct
- missing groups are handled
- aggregation semantics are explicit
- renderer parity holds
- linked brushing maps to rows
- category limits are enforced
- serialized composition reproduces the result

---

# 67. Definition of Done — Entity Resolution

Complete when:

- candidates are generated
- evidence is shown
- confidence is calibrated
- false-positive controls exist
- user can merge/keep/map
- decisions are auditable
- replay is deterministic
- canonical mappings are exportable
- original records remain recoverable

---

# 68. Definition of Done — Time-Series Studio

Complete when SmartPrep can diagnose and visualize:

- time key
- frequency
- missing periods
- duplicates
- irregularity
- gaps
- ordering
- leakage
- time-aware missingness
- time-aware preparation choices

without silently transforming the series.

---

# 69. Definition of Done — Panel Studio

Complete when SmartPrep can identify:

- entity/time structure
- duplicate entity-time
- balance
- gaps
- within/between variation
- constant-within variables
- insufficient variation
- panel completeness
- entity-specific anomalies

---

# 70. Definition of Done — Multi-backend

A backend is not complete merely because SmartPrep accepts its object.

It is complete when:

- supported operations are native
- unsupported operations are explicit
- no silent materialization
- semantics match Pandas reference behavior
- audit is backend-independent
- tests verify parity
- memory implications are surfaced

---

# 71. Final assessment

SmartPrep `v0.6.0.dev0` is the first version where the phrase:

> **Visual Data Preparation Platform**

is technically justified rather than aspirational.

It now combines:

```text
Profiling
+ Detection
+ Safe Auto Cleaning
+ Guided Cleaning
+ Preprocessing
+ Validation
+ Contracts
+ Privacy
+ Drift
+ EDA
+ Static Visualization
+ Interactive Visualization
+ Linked Analytics
+ Visual Composition
+ Smart Grid
+ Treatment Sandbox
+ Animation Foundation
+ HTML/PDF/PPTX/Notebook Publishing
+ Audit/Replay/Rollback
```

The project is no longer mainly missing ordinary cleaning functionality.

The remaining challenge is to complete the higher-order platform layers:

```text
Workflow
+ richer visual grammar
+ domain-aware intelligence
+ econometric/time structure
+ scale/backends
+ production ecosystem
```

---

# 72. Final score

## SmartPrep v0.6.0.dev0

**9.2 / 10**

Why the score increased from v0.5.1:

- Shared interaction architecture implemented.
- Visual Builder implemented.
- Linked brushing implemented.
- Cross-filtering implemented.
- Smart Grid significantly expanded.
- Treatment Sandbox implemented.
- Stable row identity solved correctly.
- 491 distributed tests pass with no failures.

Why it is not yet 10/10:

- Visual Workflow/Pipeline Canvas absent.
- Faceting/multi-series incomplete.
- Builder remains bounded by precomputed portable compositions.
- Entity Resolution absent.
- Time-Series/Panel Studio absent.
- Multi-backend absent.
- Benchmark/plugin/production layers incomplete.
- Documentation currently contains a few real contradictions.

---

# 73. Recommended immediate action

Before starting the next major feature family:

```text
v0.6.1
```

should clean the documentation/status inconsistencies and freeze the v0.6 interaction architecture.

Then development should move to:

```text
v0.7
=
Visual Workflow
+ Pipeline Canvas
+ Faceting
+ Multi-Series
+ richer composition
```

The key strategic point is:

> SmartPrep should now build upward from its strong shared Core and interaction state, not sideways by adding disconnected UI features.

That is the path most likely to preserve the architectural advantage already achieved in v0.6.
