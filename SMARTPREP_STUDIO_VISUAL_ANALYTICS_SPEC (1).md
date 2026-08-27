# SmartPrep Studio — المواصفات الموحدة لمنصة التحليل والتنظيف والتحضير والتصور التفاعلي

> **وثيقة تنفيذية موجهة للتطوير**
>
> هذه الوثيقة تجمع بصورة متسقة الأفكار المتفق عليها لـSmartPrep Studio ومحركات EDA وVisualization وCleaning وData Preparation وReporting.  
> الهدف ليس إنشاء واجهة منفصلة عن مكتبة SmartPrep، بل إنشاء **منصة متعددة الواجهات تعمل كلها فوق نفس SmartPrep Core Engine**.
>
> **قاعدة معمارية غير قابلة للتفاوض:** لا توجد خوارزمية تنظيف أو preprocessing أو validation أو قرار مستقل داخل الواجهة. Python API وStudio وVisual Workflow والتقارير وReplay يجب أن تستخدم نفس العمليات ونفس النتائج ونفس Audit Trail.

---

# 1. الرؤية النهائية

SmartPrep ليست مجرد مكتبة Data Cleaning، وليست مجرد أداة Data Profiling، وليست نسخة من PyGWalker.

الرؤية هي:

**SmartPrep = Data Intelligence + Profiling + EDA + Cleaning + Preparation + Preprocessing + Validation + Visual Analytics + Interactive Studio + Reporting + Reproducibility Platform**

بحيث يستطيع المستخدم العمل بأربع طرق متكاملة:

1. **Code-first**: كتابة Python عادية.
2. **Studio-first**: واجهة تفاعلية كاملة.
3. **Visual Workflow**: بناء pipeline بالسحب والإفلات.
4. **Auto/Guided**: تشغيل تلقائي آمن أو اتخاذ قرارات موجهة.

كل الطرق تنتج نفس Operations ونفس Audit ونفس النتيجة القابلة لإعادة التشغيل.

---

# 2. المبادئ التي تمنع التناقض

## 2.1 فصل Detection عن Repair

الثقة في اكتشاف المشكلة لا تعني الثقة في علاجها.

```text
Detection
→ Detection Confidence
→ Candidate Treatments
→ Repair Confidence
→ Risk / Reversibility / Information Loss
→ Auto / Guided / Abstain
```

لا يجوز أن يكون:

```text
High detection confidence → automatic destructive repair
```

## 2.2 Safe by default

- `scan()` لا يعدل البيانات.
- `auto_prepare()` ينفذ فقط الإصلاحات الآمنة وفق سياسة SmartPrep.
- `guided_prepare()` يعرض الحالات التي امتنع Auto Mode عن حسمها.
- المشاكل الغامضة أو عالية المخاطر تنتقل إلى Guided Mode.
- لا تعديل صامت.
- الأصل لا يتغير افتراضيًا.
- كل تعديل مسجل وقابل للتفسير والـrollback.

## 2.3 Cleaning ≠ Preprocessing

Cleaning يعالج جودة البيانات.

Preprocessing يجهز البيانات لهدف تحليلي أو ML.

لذلك لا يقوم `auto_prepare()` تلقائيًا بعمل scaling/encoding لمجرد أنه يستطيع ذلك.

## 2.4 Studio ليس implementation ثانية

الواجهة يجب أن تستدعي نفس:

- `Issue`
- `TreatmentCandidate`
- `Operation`
- `RepairPlan`
- `PreparationResult`
- `GuidedSession`
- `ValidationResult`
- `DataContract`
- `AuditRecord`

## 2.5 No click without reproducibility

كل قرار في Studio يجب أن يكون قابلًا للحفظ كـ:

- Python
- YAML/JSON configuration
- Decision replay
- Pipeline
- Audit record

---

# 3. الصورة المعمارية

```text
                         SmartPrep Core
                              │
     ┌────────────────────────┼─────────────────────────┐
     │                        │                         │
 Intelligence Engine     Preparation Engine       Validation Engine
     │                        │                         │
 Profiling                 Cleaning                  Rules
 Detection                 Repair                    Contracts
 Diagnosis                 Preprocessing             Privacy
 Recommendations           Transformations           Drift
     │                        │                         │
     └────────────────────────┼─────────────────────────┘
                              │
                      Project / Result State
                              │
          ┌───────────────────┼────────────────────┐
          │                   │                    │
     Python API         SmartPrep Studio      Visual Workflow
          │                   │                    │
          └───────────────────┼────────────────────┘
                              │
              EDA + Visualization + Publishing
                              │
        HTML / PDF / PPTX / PNG / SVG / Notebook / Code
```

---

# 4. الأفكار التي نريد جمعها وتجاوزها

لا ننسخ الأدوات؛ نأخذ أفضل مبادئها ونوحدها.

## 4.1 PyGWalker-like Visual Exploration

نريد:

- drag-and-drop chart building
- اختيار X/Y
- grouping
- color
- size
- aggregation
- filtering
- faceting
- interactive exploration
- visual query
- fast chart switching

لكن SmartPrep تتجاوز ذلك بربط الرسم مباشرة بـ:

**Diagnose → Select → Explain → Clean → Transform → Validate → Audit**

## 4.2 YData Profiling-like Profiling

نريد automatic profiling شاملًا:

- schema
- physical dtype
- inferred/semantic type
- missingness
- uniqueness
- cardinality
- descriptive statistics
- quantiles
- distributions
- correlations/associations
- duplicates
- constant/near-constant
- warnings
- text patterns
- dates
- suspicious values
- PII/privacy hints
- memory footprint

لكن SmartPrep لا تكتفي بالـalerts؛ تربط كل finding بخيارات العلاج والأثر.

## 4.3 DataProfiler-like Detection

نريد:

- structured profiling
- data type detection
- statistics
- schema insight
- label/semantic extensibility
- column-level and dataset-level diagnostics

مع دمجها في نظام Issue/Confidence/Triage.

## 4.4 Sweetviz-like Automated EDA

نريد:

- report سريع وجميل
- univariate analysis
- associations
- target-aware analysis
- dataset comparison
- قبل/بعد

لكن نضيف interactive decisions وcleaning linkage.

## 4.5 D-Tale/PandasGUI-like Data Grid

نريد Grid تفاعلية:

- sort
- filter
- search
- edit
- select
- group
- aggregate
- pivot
- inspect
- export

مع overlays لجودة البيانات وAudit لكل تعديل.

## 4.6 Automated Cleaning / Data Preparation

نريد قوة الأدوات الأوتوماتيكية، لكن بدون over-cleaning.

المخرجات يجب أن تكون مثل:

```text
42 safe repairs applied
6 warnings retained
4 review recommended
2 decisions required
```

ثم:

```python
result.open_guided()
```

## 4.7 Pandera / Great Expectations-like Validation

نريد:

- explicit rules
- schema/contracts
- severity
- PASS/WARNING/ERROR/CRITICAL
- all rules evaluated
- row splitting where useful
- contract inference from reviewed data
- contract diff
- semantic breaking changes

---

# 5. طرق الاستخدام

## 5.1 الاستخدام بالكود

```python
import smartprep as sp

scan = sp.scan(df)
result = sp.auto_prepare(df)
clean_df = result.clean_df
```

مستقبلًا يمكن أن يكون هناك Project API:

```python
project = sp.Project(df)

project.scan()
project.profile()
project.eda()
project.clean()
project.preprocess()
project.validate()
project.compare()
project.report()
```

## 5.2 Studio

```python
sp.studio(df)
```

أو:

```python
result.show()
```

بحسب الـAPI النهائي.

## 5.3 Guided

```python
session = sp.guided_prepare(df)
```

أو:

```python
result.open_guided()
```

## 5.4 Visual Pipeline

المستخدم يبني:

```text
Load
 ↓
Scan
 ↓
Fix Types
 ↓
Missing
 ↓
Duplicates
 ↓
Outliers
 ↓
Validate
 ↓
Export
```

ويستطيع تصديره إلى Python/YAML.

---

# 6. SmartPrep Studio — الهيكل العام

الواجهة المقترحة:

```text
┌──────────────────────────────────────────────────────────────┐
│ SmartPrep Studio                                            │
├──────────────┬──────────────────────────────┬────────────────┤
│ Navigation   │ Main Workspace               │ Inspector      │
│              │                              │ / Assistant    │
│ Overview     │ Grid / Chart / Report        │ Evidence       │
│ Data         │ Workflow / Compare           │ Suggestions    │
│ Issues       │                              │ Decisions      │
│ Missing      │                              │ Impact         │
│ Duplicates   │                              │                │
│ Outliers     │                              │                │
│ Categories   │                              │                │
│ Dates        │                              │                │
│ Text         │                              │                │
│ EDA          │                              │                │
│ Visualize    │                              │                │
│ Prepare      │                              │                │
│ Validate     │                              │                │
│ Privacy      │                              │                │
│ Drift        │                              │                │
│ Pipeline     │                              │                │
│ Compare      │                              │                │
│ Audit        │                              │                │
│ Reports      │                              │                │
└──────────────┴──────────────────────────────┴────────────────┘
```

---

# 7. Overview Dashboard

يعرض فورًا:

- rows / columns
- memory
- inferred schema
- health score
- missingness
- duplicate counts
- type problems
- invalid dates
- range violations
- inconsistent categories
- suspicious identifiers
- privacy findings
- unresolved issues
- auto-fixable issues
- guided-review issues
- validation status

مع cards قابلة للنقر.

مثال:

```text
Data Health       71/100
Missing           393 cells
Duplicates        36 rows
Critical          3
Warnings          17
Auto-fixable      28
Needs review       8
```

---

# 8. Smart Data Grid

ليست مجرد جدول.

## 8.1 وظائف أساسية

- sorting
- filtering
- search
- multi-column filters
- column pinning
- hide/show
- resize
- grouping
- aggregation
- pivot
- selection
- row detail
- column detail

## 8.2 Data Quality overlays

ألوان/أيقونات لحالات:

- missing
- invalid
- suspicious
- outlier
- duplicate
- conflicting duplicate
- PII
- contract violation
- unusual representation
- user-waived

## 8.3 Editing

عند التعديل:

```text
Old value
New value
Reason
Operation
Timestamp
Decision source
```

يدخل في Audit.

## 8.4 Selection → action

بعد تحديد صفوف:

```text
Explain selection
Flag
Create rule
Compare
Apply treatment
Open Guided Review
Export selection
```

---

# 9. Issue Inbox

كل المشاكل في Inbox موحدة.

لكل Issue:

- category
- detector
- affected column(s)
- rows/cells affected
- evidence
- severity
- detection confidence
- repair confidence
- reversibility
- information-loss risk
- recommendation
- alternatives
- reason Auto Mode abstained
- preview
- status

الحالات:

```text
Detected
Auto-fix eligible
Applied
Needs review
Waived
Rejected
Unresolved
Failed
```

---

# 10. Guided Decision Cards

مثال:

```text
Problem
annual_revenue contains missing values

Evidence
8.4% missing
Concentrated in 3 sectors

Recommended treatment
Group median

Why
Preserves sector-specific scale better than global median

Detection confidence
100%

Repair confidence
92%

Risk
Low

Alternatives
- Keep missing
- Median
- KNN
- Iterative
- Multiple imputation

[Preview] [Compare] [Apply] [Waive]
```

لا يظهر treatment غير قابل للتنفيذ فعليًا.

---

# 11. Treatment Sandbox

قبل تطبيق علاج مهم:

```text
Original | Median | Group Median | KNN | MICE
```

نقارن:

- distribution
- mean
- median
- SD
- quantiles
- skewness
- correlations
- missing count
- downstream readiness
- information loss

وفي ML يمكن إضافة downstream score اختياريًا، بدون خلط cleaning مع model selection.

---

# 12. EDA Engine

يجب أن يعمل:

```python
sp.eda(df)
sp.auto_eda(df)
```

ومع Project:

```python
project.eda(stage="before")
project.eda(stage="after")
project.compare_eda()
```

## 12.1 Dataset Overview

- shape
- memory
- column types
- semantic types
- missingness
- duplicates
- unique ratios
- constants
- high-cardinality
- suspicious columns

## 12.2 Numeric Univariate

- count
- missing
- mean
- median
- mode where meaningful
- variance
- SD
- min/max
- quantiles
- IQR
- MAD
- skewness
- kurtosis
- zeros
- negative values
- infinities
- outlier counts

## 12.3 Categorical Univariate

- unique
- cardinality
- mode
- frequency table
- rare categories
- category imbalance
- whitespace/case variants
- Unicode variants
- suspicious near-duplicates

## 12.4 Datetime EDA

- min/max
- range
- frequency
- gaps
- invalid dates
- duplicate timestamps
- weekday/month/quarter patterns
- temporal density

## 12.5 Text EDA

- length
- empty/blank
- whitespace
- encoding/Unicode anomalies
- token/word summaries where appropriate
- repeated patterns
- URL/email/phone-like patterns
- high-frequency values

## 12.6 Bivariate

- numeric–numeric
- categorical–numeric
- categorical–categorical
- datetime–numeric
- target-aware comparisons

## 12.7 Multivariate

- correlation
- association matrix
- pairwise views
- clustered correlation
- multivariate anomaly views
- dimensionality reduction as optional exploratory tool

---

# 13. Correlation & Association Lab

لا نستخدم Pearson لكل شيء.

## Numeric–Numeric

- Pearson
- Spearman
- Kendall

## Categorical–Categorical

- contingency tables
- chi-square diagnostics
- Cramér's V

## Numeric–Categorical

- group statistics
- effect-oriented measures where appropriate
- distribution comparisons

## Mixed association matrix

SmartPrep يستطيع إنشاء matrix مناسبة للأنواع المختلطة مع توضيح metric المستخدمة لكل زوج.

Visuals:

- static heatmap
- interactive heatmap
- clustered heatmap
- click-to-open pair analysis

---

# 14. Missing Values Lab

## Diagnostics

- missing counts
- percentages
- row missingness
- column missingness
- missing patterns
- co-missingness
- missingness by group
- missingness by time
- relation with target/other variables

## Visuals

- missing bar chart
- matrix
- heatmap
- pattern/upset-style view
- dendrogram-like similarity where useful
- timeline for time data

## Treatments

Core and future:

- keep missing
- drop with safeguards
- constant
- mean
- median
- mode
- group median
- forward fill
- backward fill
- interpolation
- KNN
- Iterative
- MICE/multiple imputation
- model-based plugins

مع Treatment Sandbox قبل الإجراءات ذات الأثر الكبير.

---

# 15. Duplicate & Entity Lab

## Exact duplicates

- exact rows
- duplicate IDs
- conflicting duplicate IDs
- duplicate groups

## Near duplicates / future entity resolution

- fuzzy strings
- blocking
- similarity
- candidate pairs
- record linkage
- merge proposals

Visual:

- duplicate groups
- network/graph view
- side-by-side record comparison

---

# 16. Outlier & Anomaly Lab

## Statistical

- IQR
- MAD
- robust z-score
- quantile rules

## Model-based / optional

- Isolation Forest
- LOF
- PyOD-compatible adapters
- multivariate methods

## Contextual

- group-specific
- time-specific
- rule/domain-specific

## Visuals

- boxplot
- violin
- scatter
- QQ plot
- histogram
- ECDF
- anomaly map

لا يتم حذف outlier تلقائيًا لمجرد اكتشافه.

---

# 17. Type & Representation Lab

يجب اكتشاف:

- mixed physical types
- numeric strings
- formatted numeric strings
- decimal comma
- thousands separators
- percentages
- currency symbols
- booleans
- date strings
- impossible dates
- sentinel values
- mixed units
- mixed locale representations

ويعرض:

```text
Current representation
Inferred semantic type
Parse success
Failed examples
Suggested conversion
Risk
Preview
```

---

# 18. Category & Text Integrity Lab

- trim whitespace
- case normalization
- Unicode normalization
- confusables
- mojibake
- control characters
- spelling variants
- aliases
- transliteration variants
- rare categories
- fuzzy candidates

مثال geography:

```text
Marrakech
Marrakesh
مراكش
```

ترتبط بـcanonical entity، لا بمجرد static lookup.

---

# 19. Data Preparation / Preprocessing Studio

تبقى منفصلة مفاهيميًا عن Cleaning.

## 19.1 Imputation

- current core methods
- advanced future methods
- fit/transform discipline
- leakage warnings

## 19.2 Encoding

- one-hot
- ordinal
- frequency
- count
- safe target encoding
- future hashing/WOE/CatBoost/etc.

## 19.3 Scaling

- standard
- min-max
- robust
- max-abs
- log
- Yeo-Johnson
- quantile
- future Box-Cox/normalizer

## 19.4 Advisor

كل recommendation تعرض:

- why recommended
- rejected alternatives
- goal context
- leakage risk
- interpretability impact

Goals:

```text
general
machine_learning
econometrics
time_series
panel
```

مثلاً Econometrics لا يقترح scaling/encoding بلا داعٍ.

---

# 20. Visualization Engine — المبدأ

يجب أن تكون Visualization طبقة مستقلة يمكن استخدامها من:

- Python
- EDA
- Studio
- Guided Sandbox
- Reports
- PowerPoint

واجهة موحدة مستقبلًا:

```python
project.plot(...)
```

أو:

```python
sp.plot(...)
```

مع:

```text
mode = static
mode = interactive
mode = animated
```

**Interactive وAnimated ليسا مترادفين.**

- Interactive: المستخدم يتفاعل مع الرسم.
- Animated: الرسم يتغير عبر الزمن/المرحلة.
- يمكن للرسم أن يكون Interactive + Animated معًا.

---

# 21. Static Visualization

مستوحاة من قوة Matplotlib/Seaborn.

تستخدم خصوصًا في:

- PDF
- papers
- print
- PowerPoint
- PNG/SVG

## Plot catalog

### Distribution

- histogram
- KDE
- ECDF
- rug
- boxplot
- violin
- boxen
- strip
- swarm

### Relationship

- scatter
- regression plot
- residual-style exploratory plot
- joint plot
- hexbin
- 2D density

### Categorical

- count plot
- bar
- point
- categorical box/violin
- grouped distributions

### Matrix

- correlation heatmap
- association heatmap
- missingness heatmap

### Time

- line
- area
- rolling bands
- seasonal/faceted views

### Multivariate

- pair plot
- facet grids
- small multiples

كل plot يجب أن يملك export إلى:

- PNG
- SVG
- PDF-compatible vector/raster output

---

# 22. Interactive Visualization

مستوحاة من Plotly/PyGWalker/Vega-style exploration.

كلما كان مناسبًا:

- hover
- zoom
- pan
- box select
- lasso select
- tooltip
- legend toggle
- filter
- dropdown
- slider
- range selector
- cross-filter
- drill-down
- linked brushing
- faceting
- responsive layout

---

# 23. Animated Visualization

الحركة يجب أن تحمل معنى.

## أمثلة صحيحة

### Cleaning stages

```text
Raw
→ Type repair
→ Missing treatment
→ Duplicate resolution
→ Validation
→ Final
```

### Time

```text
2022 → 2023 → 2024 → 2025
```

### Treatment sensitivity

```text
Winsorization threshold 0% → 5%
```

### Imputation comparison

انتقال distribution بين طرق العلاج.

### Health score evolution

```text
58 → 67 → 81 → 94
```

## لا نريد

Animation لمجرد الزينة.

---

# 24. Data Cleaning Story

ميزة مميزة لـSmartPrep.

المستخدم يشاهد البيانات عبر مراحل الـpipeline.

مثال:

```text
Stage 0 — Raw
333 missing dates
36 duplicate rows
26 geography mismatches

Stage 1 — Representation fixes

Stage 2 — Missing treatment

Stage 3 — Duplicate decisions

Stage 4 — Validation

Stage 5 — Final
```

Slider:

```text
RAW ─────────●──────── FINAL
```

عند تحريكه تتغير:

- grid
- plots
- distributions
- health score
- issue counts

إلى snapshot تلك المرحلة.

---

# 25. Linked Visual Analytics

هذه نقطة تفوق رئيسية.

إذا حدد المستخدم 30 نقطة في Scatter:

نفس observations تُحدد في:

- Grid
- Histogram
- Boxplot
- other linked charts

ثم يمكن:

```text
Explain selection
Compare with rest
Flag
Create rule
Open guided decision
Export
```

---

# 26. Visual Chart Builder

واجهة شبيهة بسهولة PyGWalker، لكن مرتبطة بـSmartPrep.

Controls:

- X
- Y
- Color
- Size
- Shape
- Group
- Facet
- Filter
- Aggregation
- Sort
- Tooltip
- Animation dimension
- chart type
- static/interactive/animated mode

مع auto recommendations.

---

# 27. Visualization Advisor

المستخدم لا يجب أن يعرف دائمًا الرسم الصحيح.

مثال:

```text
Variable: income
Type: continuous
Shape: strongly right-skewed

Recommended:
1. Histogram + KDE
2. ECDF
3. Boxplot

Before/After:
ECDF overlay recommended
```

ولـ:

```text
date + sales
```

يقترح line/time plot.

ولـcategorical:

- count/bar
- Pareto-style
- category distribution

مع سبب الاقتراح.

---

# 28. Before / After Analysis

هذه وظيفة مركزية وليست report إضافيًا.

```python
result.compare()
result.compare_eda()
```

يعرض:

```text
Metric                 Before        After
Missing                ...           ...
Duplicates             ...           ...
Invalid                 ...           ...
Health score            ...           ...
```

ثم مقارنة:

- distributions
- correlations
- category counts
- summary statistics
- missing patterns
- outlier counts
- validation
- statistical preservation

Visuals:

- side-by-side
- overlay
- delta
- animated transition
- slider before/after

---

# 29. Visual Workflow Builder

Node-based editor.

Nodes مثل:

```text
Load
Scan
Profile
Fix Types
Normalize Text
Missing
Duplicates
Outliers
Encode
Scale
Validate
Privacy
Report
Export
```

كل node = Operation/step حقيقية في الـCore.

## Code generation

Visual workflow:

```text
Scan → Impute → Validate
```

يمكن تصديره إلى Python.

## Config generation

يمكن تصديره إلى YAML/JSON.

## Replay

يمكن تشغيله على dataset جديدة.

---

# 30. Pipeline Canvas

يعرض:

- step
- status
- rows affected
- cells affected
- elapsed time
- warnings
- dependencies
- before/after score

مع إمكانية فتح كل node لرؤية evidence والتفاصيل.

---

# 31. Audit Timeline

Timeline كامل:

```text
10:01 Scan
10:02 Fix whitespace
10:03 Normalize categories
10:04 Auto declined duplicate conflict
10:05 User chose keep latest
10:06 Validate
```

يدعم:

- inspect
- undo/rollback
- replay
- export
- compare snapshots

---

# 32. Validation & Contract Studio

واجهة تعرض:

- rules
- severity
- PASS/WARNING/ERROR/CRITICAL
- affected rows
- examples
- split valid/invalid
- contract fields
- contract changes
- breaking changes
- semantic breaking changes

مع contract editor بصري.

---

# 33. Privacy Studio

يعرض:

- detected PII
- direct identifiers
- quasi-identifiers
- affected cells
- re-identification risk
- proposed transformations

Actions:

- mask
- redact
- hash
- pseudonymize
- generalize
- waive with reason

مع عدم الاعتماد فقط على نسبة العمود؛ يجب دعم cell-level detection.

---

# 34. Drift Studio

يعرض:

- schema drift
- numeric drift
- categorical drift
- missingness drift
- cleaning drift
- top contributors
- reference/current comparison

Visual:

- PSI-style plots
- distribution overlays
- category shifts
- missingness deltas
- cleaning issue deltas

ولا يختزل drift في boolean.

---

# 35. Time-Series Studio — مرحلة لاحقة

- date/frequency inference
- irregular intervals
- gaps
- duplicate timestamps
- missing periods
- timezone
- temporal ordering
- resampling diagnostics
- rolling views
- leakage-aware preparation

Visuals:

- line
- gaps
- calendar/period density
- rolling statistics
- ACF/PACF when added
- structural markers

---

# 36. Panel Studio — مرحلة لاحقة

- entity/time keys
- duplicate entity-time
- balance
- gaps per entity
- within/between variation
- constant-within entity
- chronology

Visuals:

- entity trajectories
- balance matrix
- missing periods by entity
- within/between plots

---

# 37. Reporting / Publishing Engine

التقارير ليست format واحدًا.

## أنواع التقرير

- Full Data Analysis
- Data Quality
- Cleaning
- Before/After
- EDA
- Preprocessing
- Validation
- Privacy
- Drift
- Econometrics Readiness
- ML Readiness
- Executive
- Audit

---

# 38. HTML Report

يجب أن يكون أغنى format.

يدعم:

- tabs
- filters
- interactive tables
- Plotly-like charts
- tooltips
- collapsible sections
- linked views where feasible
- before/after
- animations where meaningful
- pipeline visualization
- audit timeline

ويفضل خيار self-contained HTML قدر الإمكان.

---

# 39. PDF Report

نسخة static احترافية:

- cover
- executive summary
- methodology
- dataset overview
- issues
- treatments
- EDA
- before/after
- validation
- unresolved warnings
- appendix/audit summary

الرسومات تكون عالية الجودة.

---

# 40. PowerPoint Export

```python
project.export_report("analysis.pptx")
```

لا يكون نسخًا أعمى للتقرير.

يولد عرضًا:

1. Dataset Overview
2. Data Health
3. Main Issues
4. Missing Data
5. Duplicates/Outliers
6. Cleaning Decisions
7. Before/After
8. EDA Highlights
9. Validation
10. Remaining Risks
11. Final Dataset / Next Steps

مع charts مناسبة للعرض.

---

# 41. Image Export

كل plot يمكن تصديره:

- PNG
- SVG
- high-resolution raster
- vector where supported

للبحث والنشر والعروض.

---

# 42. Notebook Export

```python
project.export_notebook("analysis.ipynb")
```

يولد Notebook منظمة:

- imports
- load
- scan
- profile
- cleaning
- EDA
- preprocessing
- validation
- comparison
- reporting

مع كود قابل للتنفيذ.

---

# 43. Python Export

```python
project.export_python("pipeline.py")
```

حتى لو تم العمل كله بالنقر.

---

# 44. YAML / JSON Pipeline Export

مثال:

```yaml
cleaning:
  strings:
    strip: true

missing:
  income:
    method: group_median
    groupby: sector

validation:
  enabled: true
```

ثم يعاد تشغيله على بيانات أخرى.

---

# 45. Automatic Mode داخل Studio

زر:

```text
Run Safe Auto Preparation
```

ثم progress حقيقي:

```text
Schema       ✓
Types        ✓
Missing      ✓
Duplicates   ✓
Semantics    ✓
Validation   ✓
100%
```

الناتج لا يدعي الكمال.

مثال:

```text
Completed with warnings

Applied: 31
Needs review: 6
Abstained: 3
Failed detectors: 0
```

---

# 46. Guided Mode داخل Studio

الـreview queue هي نفسها abstentions من Auto Mode.

لا تبدأ analysis جديدة.

تنتقل معها:

- scan
- repairs
- audit
- snapshots
- unresolved issues

كل قرار قابل للتصدير وإعادة التشغيل.

---

# 47. Auto EDA + Auto Visualization

```python
report = sp.auto_eda(df)
```

SmartPrep تختار تلقائيًا:

- useful statistics
- appropriate charts
- warnings
- associations
- missing visuals
- target analysis where supplied

لكن تسمح للمستخدم بتغيير كل شيء.

---

# 48. Interactive + Animated Treatment Sensitivity

مثال winsorization:

```text
Threshold
0% ───────●──── 5%
```

مع تحديث مباشر:

- histogram
- boxplot
- mean
- SD
- quantiles
- outlier count

مثال imputation:

Dropdown/slider بين methods، مع تحديث visual comparison.

---

# 49. Animation Technology Principle

لا يجب ربط التصميم باسم مكتبة واحدة.

يمكن تنفيذ الواجهات عبر technologies مناسبة مثل:

- Plotly-style interactive charts
- Vega/Vega-Lite-style grammar
- Bokeh/HoloViews where useful
- D3/SVG/Canvas
- p5.js-style custom animated stories عندما نحتاج animation حرة

لكن SmartPrep API لا يجب أن يكشف اعتمادًا معماريًا صلبًا على engine واحدة.

نريد abstraction layer.

---

# 50. Visualization Backend Abstraction

مستقبلًا:

```python
sp.plot(
    ...,
    renderer="static"
)
```

أو:

```python
renderer="interactive"
renderer="animated"
```

والـStudio يختار renderer المناسب.

الفكرة:

```text
Chart Specification
        │
        ├── Static Renderer
        ├── Interactive Renderer
        └── Animated Renderer
```

---

# 51. Chart Specification موحدة

يجب تمثيل الرسم داخليًا كـspec وليس ككود frontend مباشر.

مثال مفاهيمي:

```text
ChartSpec
- mark
- x
- y
- color
- size
- facet
- aggregation
- filters
- tooltip
- interaction
- animation_dimension
- title
- annotations
```

ثم renderer يحوله إلى الرسم المطلوب.

هذا يجعل HTML/PDF/PPTX أكثر اتساقًا.

---

# 52. Data Assistant داخل Studio

لو أضيف assistant ذكي مستقبلًا، يجب أن يكون grounded في SmartPrep results.

أسئلة مثل:

- لماذا اعتبرت هذه القيمة مشكلة؟
- لماذا لم تصلحها Auto Mode؟
- قارن KNN وMICE.
- ما أثر هذا العلاج؟
- ما أهم مشاكل dataset؟
- أي chart أنسب؟

ولا يسمح له بتجاوز Safety/Triage Engine بصمت.

---

# 53. ما يجب ألا يحدث

## لا نبني UI logic منفصلة

خطأ:

```text
Studio fixes missing values with its own function
Python API uses another implementation
```

## لا نجعل animation مجرد decoration.

## لا نحذف outliers تلقائيًا لمجرد اكتشافها.

## لا نعمل encoding/scaling ضمن cleaning بلا هدف.

## لا ندعي أن تقرير HTML = Studio.

## لا ندعي أن interactive = animated.

## لا ندعي أن profile = cleaning.

## لا ندعي أن clean_df = verified_df.

## لا نستخدم confidence واحدة للاكتشاف والعلاج.

---

# 54. حالات المستخدم

## مبتدئ

```python
result = sp.auto_prepare(df)
result.show()
```

## مستخدم يريد GUI

```python
sp.studio(df)
```

## مستخدم يريد EDA فقط

```python
sp.auto_eda(df)
```

## مستخدم محترف

يستخدم APIs المنفصلة ويبني pipeline.

## باحث

يستخدم:

- static publication plots
- before/after report
- econometrics-aware preprocessing
- PDF/PPTX
- reproducible notebook/code

---

# 55. ترتيب التنفيذ بدون تناقض مع AD-010

بما أن Core أصبح مستقرًا نسبيًا، التنفيذ يكون:

## Phase A — Correctness hotfixes

قبل Studio:

- target encoding leakage
- quantile-rank NaN preservation
- contract extra-column enforcement
- low-rate/cell-level privacy detection

## Phase B — EDA Model

نبني نتائج EDA كـbackend objects مستقلة عن الواجهة.

## Phase C — Visualization Specification

نبني `ChartSpec` وrenderer abstraction.

## Phase D — Static Renderer

Matplotlib/Seaborn-style output.

## Phase E — Interactive Renderer

Plotly/Vega-style output.

## Phase F — Animated Renderer

animation/time/stage transitions.

## Phase G — HTML Reporting

يعتمد على EDA + ChartSpec.

## Phase H — SmartPrep Studio

يبنى فوق الـCore وEDA وVisualization.

## Phase I — PDF/PPTX Publishing

يستخدم نفس report model وChartSpec.

## Phase J — Visual Workflow

node editor + code/config export.

## Phase K — Advanced labs

- entity resolution
- time series
- panel
- advanced anomaly
- multi-backend

هذا لا يناقض AD-010: الواجهة تأتي بعد core contracts، لكنها لا تمنع بناء EDA/Visualization models التي ستستخدمها الواجهة.

---

# 56. Definition of Done — EDA Engine

يعتبر EDA Engine مكتملًا عندما:

- يعمل من Python دون Studio.
- يعيد objects قابلة للتسلسل.
- يغطي numeric/categorical/datetime/text.
- يدعم before/after.
- يدعم associations المناسبة للأنواع.
- لا يغير البيانات.
- يمكن لـStudio وHTML/PDF استهلاك نفس النتائج.

---

# 57. Definition of Done — Visualization Engine

- static charts
- interactive charts
- animated charts
- unified ChartSpec
- selection/linking metadata
- exportable images
- before/after visual comparison
- chart advisor
- no dependency on Studio state

---

# 58. Definition of Done — Studio

- Data Grid
- Overview
- Issues
- Guided decisions
- EDA
- Visual chart builder
- Missing Lab
- Duplicate Lab
- Outlier Lab
- Type/Text/Category labs
- Preparation
- Validation
- Privacy
- Drift
- Compare
- Pipeline
- Audit
- Reports
- linked selection
- code/config export
- no duplicate cleaning implementation

---

# 59. Definition of Done — Publishing

## HTML

- interactive
- navigable
- self-contained option
- before/after
- plots/tables/audit

## PDF

- static professional
- high-quality figures

## PPTX

- presentation-oriented
- editable text/charts where practical
- not a screenshot dump

## Notebook/Python/YAML

- reproducible
- reflects actual operations

---

# 60. نقطة التفوق الأساسية

لا نريد أن يكون:

```text
Profiling tool + cleaning tool + chart tool
```

موضوعين جنب بعض.

نريد دورة واحدة:

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

هذه الدورة نفسها تعمل من Python ومن Studio.

---

# 61. مثال تجربة كاملة

```python
import smartprep as sp

project = sp.Project(df)

project.scan()
project.eda(stage="before")

result = project.auto_prepare()

if result.review_queue:
    session = result.open_guided()
    # decisions

project.eda(stage="after")
project.compare_eda()
project.validate()

project.export_report("smartprep_report.html")
project.export_report("smartprep_report.pdf")
project.export_report("smartprep_presentation.pptx")
project.export_python("pipeline.py")
project.export_notebook("analysis.ipynb")
```

وفي Studio يستطيع المستخدم تنفيذ الدورة نفسها بدون كتابة الكود.

---

# 62. مثال تجربة Visual Studio

```text
Open SmartPrep Studio
        ↓
Overview
        ↓
Run Scan
        ↓
Inspect Issues
        ↓
Open Missing Lab
        ↓
Compare treatments visually
        ↓
Apply safe decisions
        ↓
Open Visual Explorer
        ↓
Drag variables like PyGWalker
        ↓
Select suspicious observations
        ↓
Create/Review rule
        ↓
Validate
        ↓
Before/After animated story
        ↓
Export HTML + PDF + PPTX + Code
```

---

# 63. الأولويات التي يجب شرحها للمطور

1. **لا تعيد كتابة الـCore.**
2. أصلح correctness bugs أولًا.
3. ابنِ EDA كطبقة backend مستقلة.
4. ابنِ ChartSpec موحدة.
5. افصل Static / Interactive / Animated renderers.
6. اجعل Studio مستهلكًا لهذه الطبقات.
7. اجعل كل click ينتج Operation قابلة للـaudit/replay.
8. استخدم نفس Report Model لكل formats.
9. حافظ على الفصل بين cleaning وpreprocessing.
10. لا تسمح للواجهة أن تتجاوز safe-by-default policy.

---

# 64. الهدف النهائي

SmartPrep يجب أن تمنح المستخدم في مشروع واحد:

- قوة profiling التلقائي.
- جمال automated EDA.
- سهولة drag-and-drop visual exploration.
- قوة interactive data grid.
- cleaning أوتوماتيكي آمن.
- guided preparation.
- preprocessing قابل لإعادة الاستخدام.
- validation/contracts.
- privacy/drift.
- static publication graphics.
- interactive graphics.
- meaningful animations.
- before/after analysis.
- visual pipeline.
- audit/replay.
- HTML/PDF/PPTX reports.
- Notebook/Python/config export.

لكن جميعها مبنية على **نفس الحقيقة الداخلية ونفس العمليات ونفس الـAudit Trail**.

وهذا هو الشرط الذي يجعل SmartPrep منصة متكاملة بدل مجموعة features غير مترابطة.

---

# 65. قاعدة أخيرة للتطوير

عند إضافة أي feature جديدة، يجب الإجابة عن الأسئلة التالية:

1. هل لها Core representation؟
2. هل تعمل من Python؟
3. هل يمكن للـStudio استدعاؤها دون إعادة تنفيذ؟
4. هل تسجل في Audit إذا غيرت البيانات؟
5. هل يمكن Replay لها؟
6. هل يمكن تمثيل نتيجتها في report؟
7. هل يوجد static representation عند الحاجة؟
8. هل يوجد interactive representation إذا كان التفاعل مفيدًا؟
9. هل animation تضيف معنى حقيقيًا؟
10. هل تحافظ على Safe-by-default؟
11. هل تحافظ على الفصل بين Detection وRepair؟
12. هل تحافظ على الفصل بين Cleaning وPreprocessing؟

إذا كانت الإجابة لا على أي نقطة أساسية، يجب تعديل التصميم قبل دمج الـfeature.
