# SmartPrep v0.5.1.dev0 — All Review Notes, Remaining Gaps & Corrections

## Executive assessment
Current overall assessment: **8.7/10** against the complete SmartPrep vision.

SmartPrep now has a strong architecture and mature foundations for cleaning, auto/guided preparation, validation/contracts, audit/replay, EDA, static/interactive visualization, early animation, Studio MVP, and multi-format reporting. The remaining work is predominantly product expansion rather than correction of fundamental defects.

## Completed architectural corrections in v0.5.1
- Studio documentation must distinguish **MVP Studio implemented** from **Full Visual Analytics Studio**.
- `ChartSpec.interactive: bool` was replaced by `Interaction.NONE / HOVER / EXPLORE`.
- Interaction and animation are independent dimensions.
- `animation_field` remains separate.
- SVG and Plotly honor interaction semantics; Matplotlib remains static.
- Architecture invariants now protect **Core != UI**.
- Studio-exported decisions replay through the Core with equivalent frame, waivers, audit semantics, and status.
- `ChartSpec` remains the visualization source of truth.
- Renderer parity is tested.
- Charts are built from EDA results rather than independently recomputing analytical truth.
- Accessibility foundation added: chart title/description, keyboard grid, aria-sort, skip link, focus states, non-color-only issue markers, reduced-motion handling.
- Stage walkthrough improved with play/pause, speed, step buttons and live announcements.
- PDF improved with navigable contents, page numbers, headers/footers, figure captions, continuation notes and methodology appendix.
- Test/package hygiene strengthened with declared test dependencies and clean-environment checks.

## Architectural rules that must never regress
1. `Core != UI`
2. `EDA Result != Renderer`
3. `ChartSpec = visualization source of truth`
4. `Interaction != Animation`
5. `Cleaning != Preprocessing`
6. `Detection Confidence != Repair Confidence`
7. `Cleaned Data != Verified Data`
8. `Preview != Apply`
9. `Profiling != Repair`
10. No silent destructive transformation.

# P1 — Highest-priority remaining gaps

## 1. Full Drag-and-Drop Visual Builder
The current Chart Explorer is not yet a complete PyGWalker-like visual grammar.

Required controls:
- X / Y
- Color
- Size
- Shape
- Facet
- Group
- Aggregation
- Filter
- Sort
- Tooltip
- Animation field
- chart type

Required behavior:
- drag and drop
- keyboard-accessible alternative
- live preview
- chart recommendation
- aggregation editor
- axis controls
- facet controls
- filter builder
- output must be a serializable `ChartSpec`

The builder must not generate renderer-specific analytical logic.

## 2. Linked Brushing
Selecting observations in one chart should select the same observations in:
- Data Grid
- histogram
- boxplot
- other linked charts
- KPI summaries

Selection actions:
- Explain selection
- Compare with rest
- Flag
- Create rule
- Open Guided Review
- Export selection

## 3. Cross Filtering
Use one shared filter/selection state for:
- chart -> chart
- chart -> grid
- grid -> chart
- filters -> all compatible views
- time-window selection -> time-aware views

Do not build separate incompatible filtering systems.

## 4. Smart Data Grid 2.0
Still needed:
- multi-column filtering
- advanced search
- column pinning
- resizing
- hide/show
- grouping
- aggregation
- pivot
- inline editing
- issue badges
- cell-level quality overlays
- row history
- before/after toggle
- selected-row actions
- keyboard-first navigation
- large-data virtualization
- linked selection state

All data-changing edits must become auditable Core operations.

## 5. Treatment Sandbox
A signature SmartPrep feature still missing at the intended level.

Example comparison:
`Original | Median | Group Median | KNN | Iterative | MICE`

Compare:
- distributions
- mean/median
- variance/SD
- quantiles
- skewness
- correlation preservation
- missing count
- information loss
- runtime
- repair confidence
- downstream implications

Lifecycle:
`Candidate -> Preview -> Compare -> Select -> Operation -> Apply -> Validate -> Audit`

Preview must never silently apply a transformation.

## 6. Visual Workflow Builder
Target node workflow:
`Load -> Scan -> Fix Types -> Missing -> Duplicates -> Validate -> Report`

Each node must map to a real Core operation/orchestration step.

Required:
- add/reorder/disable/inspect/duplicate/delete
- dependency representation
- parameter editor
- Python export
- YAML/JSON export
- replay

## 7. Pipeline Canvas
Expose execution state:
- step
- status
- elapsed time
- rows affected
- cells affected
- warnings
- dependencies
- health-score delta
- validation result

## 8. Advanced Cleaning Story
Extend Stage Walkthrough into synchronized stage playback:
`RAW -> Representation -> Missing -> Categories -> Duplicates -> Outliers -> Validation -> FINAL`

Synchronize:
- grid
- plots
- health score
- issue counts
- audit explanation

## 9. Richer Animation
Meaningful animation cases:
- cleaning stages
- time
- winsorization/sensitivity thresholds
- imputation alternatives
- health-score evolution

Animation must communicate analytical change, not decoration.

## 10. Visualization Catalog Expansion
Distribution:
- KDE, violin, boxen, strip, swarm, rug

Relationships:
- regression, joint view, hexbin, 2D density

Categorical:
- count, point, grouped distributions, Pareto

Matrices:
- clustered correlation
- missingness matrix
- mixed/categorical association matrices

Multivariate:
- pair exploration
- facet grids
- small multiples

## 11. Missingness Lab
Needed:
- missingness bar
- matrix
- heatmap
- co-missingness
- pattern/UpSet-like view
- group missingness
- target-related missingness
- temporal missingness
- clustering where useful

## 12. Entity Resolution
Full record linkage remains missing:
- blocking
- candidate generation
- fuzzy matching
- multi-field similarity
- candidate review
- merge proposals
- canonical entities
- audit/replay

## 13. Semantic Cleaning Packs
Potential packs:
- currencies and units
- percentages
- decimal commas/thousands separators
- formatted numeric values
- phone/email/URL
- countries/cities/postal codes
- coordinates
- locale-aware dates/numbers

Prefer updatable/plugin-based knowledge rather than rigid hard-coded dictionaries.

## 14. Unicode and Multilingual Integrity
Extend:
- Unicode normalization
- confusables
- mojibake
- control/invisible characters
- transliteration variants
- Arabic/French/English aliases
- locale-aware category normalization

## 15. Advanced Outlier/Anomaly Engine
Future:
- MAD
- robust z-score
- Isolation Forest
- LOF
- multivariate methods
- contextual/collective anomalies
- group/time-specific anomalies
- optional PyOD adapters

Outlier detection must not imply automatic deletion.

## 16. Time-Series Studio
Needed:
- frequency inference
- irregular intervals
- missing periods
- duplicate timestamps
- timezone consistency
- ordering
- resampling diagnostics
- rolling statistics
- seasonal views
- gap visualization
- time-aware imputation
- temporal leakage checks
- chronological split support

Later: ACF/PACF and structural markers where appropriate.

## 17. Panel Studio
Needed:
- entity/time keys
- duplicate entity-time
- balanced/unbalanced panel
- gaps per entity
- within/between variation
- constant-within-entity variables
- insufficient within variation
- completeness matrix
- entity trajectories
- chronology diagnostics

## 18. Multi-Backend Execution
Future targets:
- Polars
- PyArrow
- DuckDB
- Ibis
- Dask
- PySpark

Recommended architecture:
`Semantic Operation -> Backend Planner -> Native Backend Operation`

Never silently materialize a large non-Pandas dataset into Pandas. Expose memory/cost warnings and alternatives.

# P2 — Important expansion gaps

## 19. Root Cause Analysis
Move from issue counting to source attribution, e.g.:
`8423 invalid dates -> 82% from branch_03.xlsx -> probable upstream format change`

## 20. Rule Learning
Replay is not learning.

Future controlled flow:
`User Decision -> Candidate Rule -> Project Rule -> Reviewed Rule -> Organization Rule`

Require scope, confidence, provenance, versioning, conflicts and review. No silent promotion.

## 21. Plugin Ecosystem
Need:
- external plugins
- entry points
- capability metadata
- compatibility/version checks
- backend compatibility
- optional dependencies
- discovery/documentation

## 22. Advanced Drift
Potential:
- Wasserstein
- MMD
- Cramer-von Mises
- classifier-based drift
- rolling/online drift
- drift history
- reference versions
- contributor attribution
- cleaning drift history

## 23. Production Observability
Future:
- scheduled checks
- quality/schema/missingness trends
- cleaning drift
- validation failure trends
- detector/pipeline runtime
- alert thresholds
- dataset-version comparison

## 24. Advanced Privacy
Extend to:
- free-text names
- addresses
- IBAN
- locale-specific IDs
- credentials/secrets/API keys
- NER-assisted PII
- privacy-safe samples
- policy-driven redaction

## 25. Feature Engineering Workbench
Future:
- datetime features
- interactions
- polynomial features
- lag/rolling/expanding
- relational/group features
- redundancy checks
- feature lineage

Keep this clearly separate from cleaning.

## 26. Advanced Imputation
Potential:
- KNN
- Iterative
- MICE
- multiple imputation
- miceforest-style
- matrix completion
- uncertainty reporting
- panel-aware/time-aware methods

## 27. Encoding Expansion
Potential:
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

Leakage-safe fit/transform discipline remains mandatory.

## 28. Reporting Profiles
Desired:
```python
project.report(profile="executive")
project.report(profile="research")
project.report(profile="technical")
project.report(profile="audit")
project.report(profile="econometrics")
project.report(profile="ml")
```

## 29. Themes and Branding
Support:
- logo
- author/organization
- colors
- typography
- covers
- footers
- metadata

Presentation styling must remain separate from analytical truth.

## 30. Multilingual UI/Reports
High-value languages:
- English
- Arabic
- French

Keep translations separate from analytical logic.

## 31. Documentation Site
Create a proper docs site with:
- Getting Started
- Core Concepts
- Scan
- Auto
- Guided
- EDA
- Visualization
- Studio
- Reporting
- Preprocessing
- Validation
- Contracts
- Privacy
- Drift
- API Reference
- Developer Guide
- Plugin Guide
- Examples
- Migration Guides

## 32. Syntax Cookbook
Create `SYNTAX_COOKBOOK.md` with practical syntax for every normal workflow.

## 33. Function Catalog
Create `FUNCTION_CATALOG.md` containing:
- function
- signature
- purpose
- return
- short example
- docs link
- stability

## 34. Documentation Tests
Executable examples should be tested wherever practical to prevent documentation drift.

## 35. Benchmark Suite
Create `SmartPrepBench`.

Measure:
- precision/recall
- repair accuracy
- false positives/negatives
- information loss
- runtime
- memory
- user effort
- backend parity
- report cost

## 36. Competitor Benchmarks
Benchmark by task against relevant families such as:
- YData Profiling
- Sweetviz
- DataProfiler
- PyGWalker
- D-Tale
- PyJanitor
- Pandera
- Great Expectations
- AutoClean-style tools
- Feature-engine
- Skrub
- missingno

Avoid one misleading universal benchmark.

## 37. Large-Data Visualization
Planner:
`Small -> full; Medium -> sample; Large -> aggregate/rasterize; Streaming -> windowed`

Always expose Fidelity metadata.

## 38. High-Density Rendering
Potential:
- rasterized scatter
- density aggregation
- Datashader-style adapter
- adaptive binning

## 39. Geospatial Layer
When geographic data exists:
- maps
- coordinate validation
- country/city consistency
- spatial outliers
- regional summaries

# P3 — Longer-term technical/product work

## 40. Streaming / Online Preparation
- incremental statistics
- incremental scaling
- category evolution
- online anomaly detection
- online missingness/drift

## 41. Dataset Card
Potential `project.dataset_card()` with provenance, schema, quality, privacy, intended use, limitations and transformations.

## 42. Data Dictionary
Potential `project.data_dictionary()` with semantic type, description, units, categories, missingness, validation and lineage.

## 43. Stronger Dataset Fingerprint
Consider stable fingerprint from:
`schema + column order + index + ordered row hashes -> SHA-256`
while accounting for large-data cost.

## 44. Snapshot Scalability
Future:
- delta snapshots
- checkpointing
- disk-backed storage
- memory budgets
- compression

## 45. Stable Operation Identity
Separate human-readable operation IDs from stable semantic operation hashes.

## 46. Security Hardening
Continue tests for:
- XSS
- unsafe HTML
- spreadsheet formula injection
- malicious filenames
- path traversal
- report injection
- exported secrets
- external-resource loading
- untrusted plugins

# Publishing improvements

## PowerPoint
Future:
- presentation-oriented layouts
- editable text/shapes
- editable charts where practical
- executive narrative
- themes
- optional speaker notes

Avoid screenshot-only decks.

## PDF
Future:
- richer TOC
- landscape sections
- advanced table pagination
- appendices/references
- issue appendix
- configurable headers/footers
- branded templates

## HTML
Future:
- richer filters
- searchable/downloadable tables
- before/after slider
- linked views
- optional richer interactive embedding
- responsive improvements
- report profiles

Keep archival HTML distinct from Full Studio.

# Accessibility remaining work
Maintain/extend:
- keyboard navigation
- logical focus
- screen-reader labels
- non-color-only statuses
- contrast
- reduced motion
- accessible tooltips/dialogs
- keyboard alternative to drag/drop
- chart data-table alternatives

# Recommended v0.6 architecture

## Shared Visual Interaction State
Before building the five main visual features, introduce a common state model:

```text
StudioState
├── Dataset Snapshot
├── Active Filters
├── Selected Rows
├── Selected Columns
├── Active ChartSpecs
├── Current Stage
├── Pending Treatment
└── Review Context
```

Grid, charts, Visual Builder, Treatment Sandbox and Cleaning Story should use the same state.

## Visual Builder
`Field Metadata -> Visual Builder -> ChartSpec -> Renderer`

## Linked Analytics
`User Selection -> Selection State -> Stable Row IDs / Filter Expression -> Grid + Charts + KPIs + Sandbox`

Do not rely only on positional DataFrame indexes after transformations.

## Treatment Sandbox
`Issue -> Candidates -> Preview Frames/Summary Deltas -> ChartSpecs -> Comparison UI -> Selected Candidate -> Core Operation`

## Workflow
`Visual Node -> Serializable Operation Specification -> Core Pipeline`

# Recommended roadmap

## v0.5.1
Architectural hardening:
- interaction model
- architecture invariants
- accessibility
- stage controls
- navigable PDF
- packaging/test hygiene

**Status: substantially completed.**

## v0.6
Visual analytics foundation:
1. Full Drag-and-Drop Visual Builder
2. Linked Brushing
3. Cross Filtering
4. Smart Grid 2.0
5. Treatment Sandbox
6. richer chart catalog

## v0.7
Workflow:
- Visual Workflow Builder
- Pipeline Canvas
- advanced Cleaning Story
- Entity Resolution foundation

## v0.8
Domain-aware preparation:
- Time-Series Studio
- Panel Studio
- semantic packs
- advanced anomaly engine

## v0.9
Scale:
- backend abstraction
- Polars
- Arrow
- DuckDB
- Ibis
- Dask/Spark foundations

## v1.0 candidate
Product hardening:
- stable public API
- full docs
- cookbook
- function catalog
- benchmark suite
- plugin ecosystem
- publishing polish
- security hardening
- migration documentation

# Top five immediate priorities
1. **Full Drag-and-Drop Visual Builder**
2. **Linked Brushing + Cross Filtering**
3. **Treatment Sandbox**
4. **Smart Data Grid 2.0**
5. **Visual Workflow / Pipeline Canvas**

These should be designed together around shared interaction state.

# Definition of Done — Visual Builder
- drag/drop and keyboard alternative
- fields/aggregations/filters/facets configurable
- live preview
- explainable recommendations
- produces `ChartSpec`
- multi-renderer compatible
- serializable/replayable

# Definition of Done — Linked Analytics
- chart selection updates grid
- grid selection updates charts
- filters propagate
- charts synchronize
- selection survives compatible view changes
- selected rows can become rule/review/export
- stable row identity

# Definition of Done — Treatment Sandbox
- multiple feasible treatments previewable
- preview does not apply
- statistical and visual consequences shown
- information loss/risk shown
- rationale shown
- apply/waive supported
- final choice becomes Core operation
- audit/replay reproduces result

# Definition of Done — Smart Grid 2.0
- scalable
- sort/filter/search
- quality overlays
- row/cell selection
- linked selection
- auditable editing
- before/after inspection
- grouping/pivot where feasible
- accessibility compliant

# Definition of Done — Visual Workflow
- nodes map to Core operations
- explicit dependencies
- valid reorder rules
- parameter editing
- executable pipeline
- inspectable results
- Python/config export
- replay
- audit equivalent to code-first execution

# Final assessment
SmartPrep `v0.5.1.dev0` is a strong architectural/correctness foundation. The main challenge is no longer adding ordinary cleaning functions; it is creating one coherent visual analytical experience over the existing Core.

The intended lifecycle remains:

```text
PROFILE
  ↓
DETECT
  ↓
EXPLAIN
  ↓
VISUALIZE
  ↓
RECOMMEND
  ↓
PREVIEW
  ↓
DECIDE
  ↓
APPLY
  ↓
VALIDATE
  ↓
COMPARE
  ↓
REPORT
  ↓
REPLAY
```

The same analytical truth must work through:
- Python API
- Studio
- Visual Builder
- Workflow Canvas
- Reports

without duplicated implementation.

## Final recommendation
Make **SmartPrep v0.6 — Full Visual Analytics Foundation** the next milestone:

```text
Shared Interaction State
+ Visual Builder
+ Linked Analytics
+ Smart Grid 2.0
+ Treatment Sandbox
+ Workflow Foundation
```

After that foundation is stable, Entity Resolution, Time-Series, Panel, Multi-backend, advanced semantics, plugins, benchmarks and production monitoring can be layered on coherently.
