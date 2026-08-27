# SmartPrep v0.5.0.dev0 — التقييم الشامل، النقائص المتبقية، وخطة التصحيح

## 1. الهدف من هذا التقرير

هذا التقرير يقيّم النسخة:

`smartprep-0.5.0.dev0`

مقارنةً بالرؤية الكاملة لـSmartPrep باعتبارها:

> منصة شاملة لـData Profiling + EDA + Data Cleaning + Data Preparation + Preprocessing + Validation + Static Visualization + Interactive Visualization + Animation + Studio + Reporting + Reproducibility.

التقرير يركز على:

- ما تم تنفيذه فعليًا.
- ما تم إغلاقه من نقائص `v0.4`.
- ما يزال ناقصًا.
- ما يحتاج تصحيحًا.
- ما يحتاج توسيعًا.
- الأولويات قبل النسخة التالية.

---

# 2. الخلاصة التنفيذية

`v0.5.0.dev0` تمثل تقدمًا مهمًا جدًا مقارنة بـ`v0.4`.

أهم ما أصبح موجودًا:

- Matplotlib renderer.
- Plotly renderer.
- Static + Interactive visualization.
- Stage animation / walkthrough أولي.
- HTML publishing.
- PDF publishing.
- PowerPoint publishing.
- Notebook export.
- Image export.
- Smart Data Grid أولية.
- Chart Explorer.
- EDA backend.
- Before/After comparison.
- Guided workflow.
- Audit / rollback / replay.
- Validation / contracts.
- Privacy / drift.

إذن SmartPrep لم تعد مجرد Cleaning Core.

لكنها لم تصل بعد إلى:

> Full Visual Data Preparation & Analytics Platform

كما تم تعريفها في المواصفات.

أكبر النقائص الحالية تتركز في:

1. Full PyGWalker-like visual builder.
2. Linked brushing / cross-filtering.
3. Treatment Sandbox تفاعلي.
4. Visual Workflow / Pipeline Canvas.
5. Entity Resolution.
6. Advanced Semantic Cleaning.
7. Time-Series Studio.
8. Panel Studio.
9. Multi-backend execution.
10. Advanced animated visual stories.
11. Advanced anomaly system.
12. Full documentation site.
13. Benchmark suite.
14. Plugin ecosystem.
15. Production-grade observability.

---

# 3. الاختبارات والحالة العامة

النتيجة التي تم التحقق منها:

```text
396 passed
51 skipped
```

لا توجد failures في suite الموزعة.

الـ51 skipped مرتبطة باختبارات stress fixture غير الموجودة داخل sdist.

### التقييم

هذا جيد جدًا بالنسبة لنسخة dev.

لكن يجب عدم اعتبار عدد الاختبارات وحده دليلًا على اكتمال المنصة.

---

# 4. ما أُغلق من نقائص v0.4

## 4.1 Static Renderer

تمت إضافة Matplotlib renderer.

هذا يغلق فجوة أساسية كانت موجودة في `v0.4`.

الآن يمكن إنتاج رسوم مناسبة لـ:

- PNG
- PDF
- static reporting
- publications
- presentations

---

## 4.2 Interactive Renderer

تمت إضافة Plotly renderer.

أصبح هناك:

- hover
- zoom
- pan
- box selection
- lasso selection

إذن SmartPrep أصبحت تمتلك **Interactive Visualization حقيقية**، وليس فقط SVG static داخل HTML.

---

## 4.3 Export formats

أصبح `save_chart()` يدعم:

- SVG
- PNG
- PDF
- HTML
- JSON

وهذا تقدم مهم.

---

## 4.4 Plot catalog

تم توسيع الرسومات بإضافة:

- box chart
- ECDF
- scatter
- target chart
- KPI chart
- stage chart

وتم تنفيذ Marks كانت موجودة سابقًا دون renderer مكتمل.

---

## 4.5 PDF Publishing

أصبح موجودًا.

---

## 4.6 PowerPoint Publishing

أصبح موجودًا.

هذه نقطة قيمة مضافة قوية مقارنة بأدوات profiling كثيرة.

---

## 4.7 Notebook Export

أصبح موجودًا.

---

## 4.8 Smart Data Grid

تمت إضافة Grid أولية مع:

- search
- sort
- filter
- data-quality overlays

لكنها ما تزال MVP وليست Grid نهائية.

---

## 4.9 Chart Explorer

أصبح موجودًا كواجهة للاستكشاف البصري.

لكن لا يزال يحتاج أن يصل لمستوى PyGWalker-style drag-and-drop.

---

## 4.10 Animation

تمت إضافة Stage Walkthrough مع:

- Slider
- Play

وهذا يعني أن مفهوم Animated Visualization بدأ فعليًا.

---

## 4.11 الفصل بين HTML Report وStudio

تم اتخاذ قرار صحيح:

```text
HTML Report
= archival / portable / self-contained

Studio
= richer interactive environment
```

هذا يحل تناقضًا معماريًا سابقًا.

---

# 5. التقييم حسب المحركات

## Intelligence Engine

الحالة:

**Strong**

يشمل:

- scan
- issues
- confidence
- recommendations
- profile
- EDA
- missingness structure
- associations
- before/after

### ما ينقص

- unusual-pattern engine أوسع
- root cause analysis
- learned rules
- domain-specific knowledge packs

---

## Preparation Engine

الحالة:

**Strong core**

يشمل:

- auto prepare
- guided prepare
- repairs
- preprocessing
- audit
- snapshots
- rollback

### ما ينقص

- richer treatment catalog
- entity resolution
- advanced imputation
- advanced encoding
- advanced outlier treatments
- feature engineering workbench

---

## EDA Engine

الحالة:

**Good foundation**

يشمل:

- numeric
- categorical
- datetime
- text
- mixed-type associations
- missingness
- before/after comparison

### ما ينقص

- richer multivariate EDA
- pair exploration
- target-aware EDA أوسع
- high-cardinality categorical diagnostics
- robust statistics أوسع
- distribution distance metrics
- time-series EDA
- panel EDA

---

## Visualization Engine

الحالة:

**Strong foundation, incomplete superset**

يشمل:

- SVG
- Matplotlib
- Plotly
- Static
- Interactive
- first-stage Animation

### ما ينقص

- full chart catalog
- linked views
- visual selection propagation
- cross filtering
- synchronized filters
- faceting system أوسع
- custom visual grammar
- advanced animation
- map/geospatial visual layer
- network/entity plots
- high-density rendering

---

## Studio Engine

الحالة:

**MVP+**

أصبح أكثر من مجرد report viewer.

لكن ما يزال بعيدًا عن Full Studio.

### ما ينقص

- drag & drop visual builder
- full interactive grid
- linked brushing
- treatment sandbox
- visual workflow
- pipeline canvas
- richer inspector
- live parameter controls
- custom rule builder
- entity resolution lab
- time-series lab
- panel lab
- privacy lab متقدم
- drift monitoring view

---

## Publishing Engine

الحالة:

**Good**

يشمل:

- HTML
- PDF
- PPTX
- Notebook
- Markdown/JSON
- chart image formats

### ما ينقص

- report templates
- executive/research/ml/econometrics profiles
- theme system
- branding
- editable PowerPoint chart strategy
- accessibility metadata
- full source appendix
- automated bibliography/references section
- multilingual reports

---

## Reproducibility Engine

الحالة:

**Strong**

يشمل:

- audit
- decisions
- replay
- snapshots
- rollback
- exports

### ما ينقص

- stable operation hash
- stronger dataset fingerprint
- environment lock export
- artifact manifest
- reproducible report manifest
- provenance graph visualization

---

# 6. P0 — التصحيحات الحرجة قبل توسيع الميزات

في `v0.5` لا توجد نفس أخطاء correctness الكبيرة التي ظهرت في `v0.3`.

لكن توجد نقاط يجب حسمها كـP0 معماريًا.

## P0-1 — تعريف واضح لـStudio completeness

يجب أن يكون التوثيق صريحًا:

```text
Studio MVP implemented.
Full Visual Analytics Studio remains under development.
```

لا تستخدم كلمة:

```text
Studio complete
```

إلا إذا أصبحت كل الميزات البصرية الكبرى موجودة.

---

## P0-2 — فصل واضح بين Interactive وAnimated

يجب أن يبقى:

```text
Interactive != Animated
```

Interactive:

- hover
- zoom
- selection
- filter

Animated:

- time
- stages
- transitions
- sensitivity

يمكن أن يكون chart:

```text
Interactive + Animated
```

لكن لا نخلط المصطلحين في API أو docs.

---

## P0-3 — No UI-only transformation logic

يجب اختبار أن:

```text
Studio action
```

تنتج نفس:

```text
Operation / Repair / Audit
```

التي ينتجها Python API.

أي من الضروري إضافة integration tests لـ:

```text
UI decision -> replay -> identical output
```

---

## P0-4 — ChartSpec يجب أن تبقى المصدر الوحيد للحقيقة

مع وجود:

- SVG
- Matplotlib
- Plotly
- PDF
- PPTX

خطر كبير أن يبدأ كل renderer في بناء منطق مستقل.

يجب فرض قاعدة:

```text
EDA result
→ ChartSpec
→ Renderer
```

ولا يُسمح للـrenderer بإعادة تفسير البيانات بطريقة مختلفة.

---

# 7. P1 — Full PyGWalker-like Visual Builder

هذه أكبر فجوة الآن.

Chart Explorer الحالي لا يساوي PyGWalker-like builder كاملًا.

المطلوب:

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
Animation Field
```

مع Drag & Drop.

## المطلوب

- field shelf
- drop zones
- chart recommendation
- live preview
- chart-type switching
- aggregation editor
- axis controls
- facet controls
- tooltip controls

---

# 8. P1 — Linked Brushing / Cross Filtering

هذه نقطة أساسية للتفوق.

مثال:

```text
Select 40 points in scatter
```

يجب أن:

- تحدد نفس rows في grid
- تحدث histogram
- تحدث boxplot
- تحدث KPI cards

ثم يستطيع المستخدم:

```text
Flag
Compare
Create rule
Open guided review
```

الحالي لا يقدم full linked selection system.

---

# 9. P1 — Smart Data Grid 2.0

الـGrid الحالية تحتاج توسع.

المطلوب:

- multi-column filtering
- advanced search
- column pinning
- column resize
- hide/show
- grouping
- aggregation
- pivot
- inline editing
- issue badges
- cell-level highlights
- row history
- before/after toggle
- selected-row actions
- keyboard navigation
- large-data virtualization

---

# 10. P1 — Treatment Sandbox

واحدة من أهم الميزات غير الموجودة بالشكل المطلوب.

مثال Missing:

```text
Original
Median
Group Median
KNN
Iterative
MICE
```

ويعرض:

- distribution
- mean
- variance
- quantiles
- correlation preservation
- missing count
- information loss
- runtime
- confidence

ثم المستخدم يختار.

هذا يجب أن يكون متاحًا من Guided Mode وStudio.

---

# 11. P1 — Visual Workflow Builder

ما يزال ناقصًا.

المطلوب Node Editor:

```text
Load
 ↓
Scan
 ↓
Fix Types
 ↓
Missing
 ↓
Outliers
 ↓
Validate
 ↓
Report
```

كل Node يجب أن يمثل Core operation حقيقية.

ويجب أن يدعم:

- reorder
- disable
- inspect
- duplicate
- delete
- connect dependencies
- export Python
- export YAML
- replay

---

# 12. P1 — Pipeline Canvas

مختلف قليلًا عن Workflow Builder.

Pipeline Canvas يعرض الـpipeline الحالية ونتائج التنفيذ:

- status
- elapsed time
- rows changed
- cells changed
- warnings
- score change
- dependencies

مع إمكانية فتح كل Step.

---

# 13. P1 — Advanced Animation

Stage Walkthrough بداية جيدة.

لكن الرؤية النهائية تحتاج:

## Cleaning Story

```text
Raw
→ Types
→ Missing
→ Categories
→ Outliers
→ Validation
→ Final
```

## Time animation

```text
2021 → 2022 → 2023
```

## Sensitivity animation

مثال:

```text
Winsorization threshold
0% → 5%
```

## Treatment animation

مشاهدة تحول distribution عند تغيير method.

---

# 14. P1 — Visualization catalog ما يزال ناقصًا

يجب إضافة أو تحسين:

## Distribution

- KDE
- violin
- boxen
- strip
- swarm
- rug

## Relationship

- regression plot
- joint plot
- hexbin
- 2D density

## Categorical

- count plot
- point plot
- grouped distributions
- Pareto

## Matrix

- clustered correlation
- missing matrix
- category association matrix

## Multivariate

- pair plot
- facet grid
- small multiples

---

# 15. P1 — Missingness Visualization Lab

ينقص:

- missing matrix
- heatmap
- co-missingness matrix
- pattern graph
- UpSet-like patterns
- timeline missingness
- missingness by group
- missingness by target

هذه منطقة يمكن أن تتفوق فيها على missingno بدل مجرد تقليدها.

---

# 16. P1 — Entity Resolution

ما يزال غير موجود بالشكل الكامل.

نحتاج:

- fuzzy duplicate detection
- blocking
- similarity scoring
- candidate generation
- record comparison
- merge proposal
- user review
- canonical entity mapping

مع:

```text
Record A | Record B | Similarity | Recommendation
```

---

# 17. P1 — Semantic Cleaning

ما يزال محدودًا.

المطلوب:

- currencies
- units
- percentages
- decimal comma
- formatted numbers
- phone normalization
- email normalization
- URL validation
- addresses
- countries
- cities
- postal codes
- coordinates
- locale-aware parsing

مع plugin packs.

---

# 18. P1 — Advanced Outlier / Anomaly Engine

المطلوب:

- IQR
- MAD
- robust z-score
- Isolation Forest
- LOF
- multivariate detectors
- contextual anomalies
- collective anomalies
- PyOD adapters

مع عدم حذف أي Outlier تلقائيًا لمجرد اكتشافه.

---

# 19. P1 — Time-Series Studio

ما يزال كبيرًا كفجوة.

المطلوب:

- frequency inference
- missing periods
- duplicate timestamps
- irregular spacing
- timezone consistency
- resampling diagnostics
- rolling statistics
- seasonal views
- gap visualization
- time-aware imputation
- temporal leakage guard

---

# 20. P1 — Panel Studio

المطلوب:

- entity/time keys
- duplicate entity-time
- unbalanced panel
- gaps by entity
- within/between variation
- constant-within-entity
- insufficient within variation
- panel completeness matrix

---

# 21. P1 — Multi-backend

ما تزال SmartPrep فعليًا Pandas-first.

المطلوب:

- Polars
- PyArrow
- DuckDB
- Ibis
- Dask
- PySpark

لكن يجب تنفيذ abstraction layer أولًا.

القاعدة:

```text
Semantic Operation
→ Backend Planner
→ Native Backend Operation
```

---

# 22. P1 — No Silent Fallback

عند دعم multi-backend:

ممنوع التحويل بصمت من:

```text
Spark / Polars
```

إلى:

```text
Pandas
```

إذا كان ذلك مكلفًا.

يجب إظهار:

- memory estimate
- materialization warning
- alternatives

---

# 23. P2 — Root Cause Analysis

الحالي لديه hints، لكن لا يوجد engine كامل.

المطلوب:

```text
Invalid dates: 8423

82% from:
source_file = branch_03.xlsx

Likely root cause:
date format changed upstream
```

---

# 24. P2 — Rule Learning

Decision replay ليس Rule Learning.

المطلوب:

- project rules
- organization rules
- domain rules
- promotion policy
- conflicts
- versioning
- provenance

---

# 25. P2 — Plugin Ecosystem

DetectorRegistry بداية جيدة.

لكن نحتاج:

- external plugins
- entry points
- compatibility metadata
- plugin capabilities
- optional dependencies
- backend support
- version checks

---

# 26. P2 — Advanced Drift

الموجود جيد كبداية.

ينقص:

- Wasserstein
- MMD
- classifier drift
- Cramér–von Mises
- online drift
- rolling windows
- drift history
- reference versions
- drift alerts

---

# 27. P2 — Production Observability

إذا أردنا SmartPrep production-grade:

- scheduled checks
- quality trends
- schema trends
- cleaning drift
- failure rate
- detector timing
- alert thresholds
- dataset version comparison

---

# 28. P2 — Advanced Privacy

المطلوب:

- NER
- names in free text
- addresses
- IBAN
- locale-specific IDs
- secrets/API keys
- privacy policies
- report redaction
- privacy-safe samples

---

# 29. P2 — Feature Engineering

ينقص:

- datetime features
- interactions
- polynomial
- lag
- rolling
- expanding
- relational features
- redundancy checks
- lineage

---

# 30. P2 — Advanced Imputation

الموجود ما يزال core set.

ينقص:

- KNN
- Iterative
- MICE
- multiple imputation
- miceforest-style
- matrix completion
- uncertainty reporting
- panel-aware methods

---

# 31. P2 — Encoding catalog

ينقص:

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

---

# 32. P2 — Reporting Profiles

نحتاج:

```python
project.report(profile="executive")
project.report(profile="research")
project.report(profile="technical")
project.report(profile="audit")
project.report(profile="econometrics")
project.report(profile="ml")
```

---

# 33. P2 — Themes / Branding

التقارير يجب أن تدعم:

- themes
- logo
- organization name
- author
- colors
- fonts
- cover page
- footer
- report metadata

---

# 34. P2 — Multilingual UI/Reports

يفضل دعم:

- English
- Arabic
- French

لاحقًا على الأقل.

---

# 35. P2 — Documentation Site

README قوي، لكنه غير كافٍ.

نحتاج:

```text
docs/
mkdocs.yml
```

وصفحات:

- Getting Started
- Auto
- Guided
- EDA
- Visualization
- Studio
- Reports
- Preprocessing
- Validation
- Contracts
- Privacy
- Drift
- API Reference
- Developer Guide
- Plugin Guide

---

# 36. P2 — Syntax Cookbook

نحتاج:

```text
SYNTAX_COOKBOOK.md
```

بحيث يجد المستخدم بسرعة:

```python
sp.scan(df)
sp.auto_prepare(df)
sp.studio(df)
```

وكل بقية الـfunctions.

---

# 37. P2 — Function Catalog

نحتاج:

```text
FUNCTION_CATALOG.md
```

لكل Public Function:

- signature
- purpose
- example
- documentation link

---

# 38. P2 — Documentation Tests

كل مثال في README/docs يجب أن يكون executable قدر الإمكان.

---

# 39. P2 — Benchmark Suite

الـstress baseline لا يساوي benchmark suite.

نحتاج:

```text
SmartPrepBench
```

يقيس:

- precision
- recall
- repair accuracy
- false positives
- false negatives
- information loss
- runtime
- memory
- user effort
- backend parity

---

# 40. P2 — Competitor Benchmarks

مقارنة منظمة مع:

- YData Profiling
- Sweetviz
- PyGWalker
- PyJanitor
- Pandera
- Great Expectations
- AutoClean
- Feature-engine
- Skrub

بحسب المهمة، وليس benchmark واحدًا غير عادل.

---

# 41. P2 — Large-data visualization

عند ملايين الصفوف:

```text
full data
```

ليس خيارًا دائمًا.

نحتاج planner:

```text
Small      → full
Medium     → sample
Large      → aggregate/rasterize
Streaming  → rolling window
```

مع Fidelity badge.

---

# 42. P2 — Datashader-style high density

يمكن التفكير في adapter أو strategy للـhigh-density scatter/heatmap.

---

# 43. P2 — Geospatial Visualization

إذا وجد:

- latitude
- longitude
- country
- region

يمكن إضافة:

- maps
- geography consistency views
- spatial outliers

لكن هذه ليست أولوية قبل الأساسيات.

---

# 44. P3 — Streaming / Online Preparation

مستقبلًا:

- running statistics
- incremental scaling
- online anomalies
- online drift
- category evolution
- streaming missingness

---

# 45. P3 — Project API

إذا لم يكن موجودًا بالشكل النهائي، التفكير في:

```python
project = sp.Project(df)
```

كـstateful orchestration object.

لكن يجب ألا يعيد تنفيذ logic الموجودة.

---

# 46. P3 — Dataset Card

إضافة:

```python
project.dataset_card()
```

---

# 47. P3 — Data Dictionary

إضافة:

```python
project.data_dictionary()
```

---

# 48. P3 — Stronger dataset fingerprint

إذا كان fingerprint الحالي يعتمد hash مبسط، يفضل مستقبلًا:

```text
ordered row hashes
+ schema
+ column order
+ index
→ SHA256
```

---

# 49. P3 — Snapshot scalability

Deep copies لكل snapshot ستصبح مكلفة.

نحتاج لاحقًا:

- delta snapshots
- checkpointing
- disk-backed
- memory budgeting

---

# 50. P3 — Stable operation identity

فصل:

```text
display id
```

عن:

```text
stable operation hash
```

---

# 51. P3 — Security hardening

مع Studio وHTML/PPTX/PDF يجب الاستمرار في فحص:

- XSS
- formula injection
- path traversal
- unsafe HTML
- report injection
- embedded secrets
- malicious filenames
- external resource loading

---

# 52. PowerPoint — تحسينات مطلوبة

وجود PPTX ممتاز، لكن لاحقًا نحتاج:

- presentation-oriented layouts
- editable text
- editable shapes
- charts editable when practical
- speaker notes optional
- theme system
- executive story flow

وليس فقط نقل التقرير كما هو.

---

# 53. PDF — تحسينات مطلوبة

- TOC
- page numbers
- headers/footers
- methodology appendix
- reference appendix
- issue appendix
- landscape support
- figure captions
- table continuation

---

# 54. HTML — تحسينات مطلوبة

- richer interactive tabs
- cross filtering
- downloadable tables
- before/after slider
- search
- responsive mobile improvements
- optional embedded Plotly assets
- report profile system

---

# 55. Animation — تحسينات مطلوبة

Stage Walkthrough ممتاز كبداية.

المطلوب:

- play/pause
- speed
- step labels
- transition descriptions
- synchronized chart changes
- health score animation
- issue-count animation
- distribution animation
- reduced-motion accessibility

---

# 56. Accessibility

Studio والتقارير يجب أن تراعي:

- keyboard navigation
- focus state
- screen reader labels
- non-color-only warnings
- sufficient contrast
- reduced motion
- readable tooltips

---

# 57. أهم التصحيحات المعمارية

## قاعدة 1

```text
Core != UI
```

## قاعدة 2

```text
EDA result != renderer
```

## قاعدة 3

```text
ChartSpec = source of truth
```

## قاعدة 4

```text
Interactive != Animated
```

## قاعدة 5

```text
Cleaning != Preprocessing
```

## قاعدة 6

```text
Detection confidence != Repair confidence
```

## قاعدة 7

```text
clean_df != verified_df
```

---

# 58. خريطة الطريق المقترحة للنسخة التالية

## v0.5.1.dev

- documentation cleanup
- Studio completeness wording
- renderer parity tests
- export regression tests
- accessibility basics
- chart spec consistency tests

## v0.6.0.dev

- Drag & Drop Visual Builder
- Smart Grid 2.0
- Linked brushing
- Cross-filtering
- Treatment Sandbox
- richer charts

## v0.7.0.dev

- Visual Workflow
- Pipeline Canvas
- advanced animation
- Entity Resolution

## v0.8.0.dev

- Time-Series
- Panel
- Advanced anomalies
- Semantic cleaning packs

## v0.9.0.dev

- Multi-backend
- Polars
- Arrow
- DuckDB
- Ibis
- Dask/Spark foundations

## v1.0 candidate

- full docs
- benchmark
- stable API
- plugin system
- publishing polish
- production hardening

---

# 59. التقييم النهائي

## ما تم إنجازه

SmartPrep أصبحت الآن تمتلك فعليًا:

```text
Profiling
+ EDA
+ Safe Cleaning
+ Guided Preparation
+ Preprocessing
+ Validation
+ Privacy
+ Drift
+ Static Visualization
+ Interactive Visualization
+ Early Animation
+ HTML
+ PDF
+ PowerPoint
+ Notebook
+ Studio MVP
+ Audit/Replay
```

وهذا تقدم كبير جدًا.

## ما يزال يفصلها عن الرؤية الكاملة

```text
Full Visual Builder
+ Linked Analytics
+ Treatment Sandbox
+ Visual Workflow
+ Entity Resolution
+ Time-Series/Panel
+ Multi-backend
+ Advanced Semantic Cleaning
+ Production Observability
+ Full Documentation
+ Benchmark Suite
```

---

# 60. أهم خمس أولويات الآن

إذا أردنا أعلى قيمة مضافة بأقل تشتت:

1. **Drag & Drop Visual Builder**
2. **Linked Brushing / Cross Filtering**
3. **Treatment Sandbox**
4. **Smart Data Grid 2.0**
5. **Visual Workflow / Pipeline Canvas**

هذه الخمس هي التي ستحول Studio من:

> Interactive Review Tool

إلى:

> Full Visual Data Preparation & Analytics Studio

وهي أكثر ما يميز SmartPrep عن كونها مجرد مجموعة قوية من APIs وتقارير.
