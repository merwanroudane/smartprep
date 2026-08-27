# Master Prompt لبناء مكتبة SmartPrep وفق الخطة المرجعية الكاملة

> **ملاحظة قبل الاستخدام:**  
> استبدل القيم الموجودة بين الأقواس `{{ ... }}` بالمعلومات الحقيقية قبل بدء التنفيذ.
>
> - GitHub Repository: `https://github.com/merwanroudane/smartprep`
> - Author / Maintainer Name: `Dr Merwan Roudane`
> - Contact Email: `merwanroudane920@gmail.com`
> - PyPI Package Name: `{{PYPI_PACKAGE_NAME}}`
> - Python Import Name: `{{IMPORT_NAME}}`
> - License: `{{LICENSE}}`
>
> يجب ألا يُذكر في README أو Documentation أو Source Code أو Metadata أو Releases أو Commits أو أي ملف عام أن المشروع تم إنشاؤه أو تطويره بواسطة Claude أو ChatGPT أو أي مساعد ذكاء اصطناعي.  
> توثيق المشروع يجب أن ينسب المشروع فقط إلى المؤلف/المطور المحدد أعلاه.

---

# 1. الهدف العام

أريد بناء مكتبة Python احترافية، حديثة، شاملة، قابلة للتوسع، تفاعلية، وموثقة توثيقًا عميقًا، متخصصة في:

- Data Profiling
- Exploratory Data Analysis
- Data Quality
- Data Validation
- Data Cleaning
- Data Preprocessing
- Missing Data Analysis
- Outlier / Anomaly Analysis
- Encoding
- Scaling
- Transformation
- Feature Engineering
- Entity Resolution
- Semantic Cleaning
- Text / Unicode Cleaning
- Date / Time Cleaning
- Data Contracts
- Schema Evolution
- Data Drift
- Data Observability
- Privacy / PII
- Data Lineage
- Reproducibility
- Interactive Data Preparation
- Automated Safe Cleaning
- Guided Human-in-the-loop Cleaning
- Before/After Analysis
- Static and Interactive Reporting
- Multi-backend Data Processing
- Streaming / Online Preprocessing
- Time-Series / Panel-Aware Preparation
- Econometrics-Aware Preparation
- Machine-Learning-Aware Preparation

المكتبة يجب ألا تكون مجرد Wrapper فوق مكتبات موجودة، بل يجب أن تتعلم من أفضل أفكار الأدوات الحالية ثم تقدم طبقات إضافية من:

**Intelligence + Recommendation + Explainability + Safety + User Control + Reproducibility + Auditability + Interactivity.**

---

# 2. المرجع المعماري الأساسي

اعتبر الملف التالي المرجع الرئيسي للتصميم:

`intelligent_data_cleaning_preprocessing_library_plan_v9_referenced.md`

يجب قراءة الخطة كاملة قبل كتابة الكود.

لا تبدأ التنفيذ مباشرة قبل استخراج:

1. المتطلبات الوظيفية.
2. المتطلبات غير الوظيفية.
3. الوحدات Modules.
4. الـ APIs الأساسية.
5. الاعتماديات.
6. المعمارية.
7. الـ backends.
8. مستويات الثقة.
9. أنواع المشاكل.
10. أنواع التقارير.
11. أوضاع التشغيل.
12. نظام الـ warnings.
13. نظام الـ audit.
14. نظام الـ lineage.
15. التوثيق المطلوب.
16. الاختبارات المطلوبة.
17. الـ benchmark requirements.

---

# 3. فلسفة المكتبة

المكتبة يجب أن تعمل وفق الدورة التالية:

```text
Load
→ Understand
→ Profile
→ Diagnose
→ Detect
→ Classify
→ Explain
→ Recommend
→ Compare
→ Ask When Needed
→ Preview
→ Apply
→ Validate
→ Measure Impact
→ Record
→ Reproduce
→ Export
→ Monitor
```

المبدأ الأساسي:

> **لا تُصلح أي شيء غير مؤكد بالقوة.**

كل مشكلة يجب أن تحصل على:

- Issue ID
- Issue category
- Severity
- Confidence
- Detection evidence
- Possible treatments
- Recommended treatment
- Risk level
- Auto-fix eligibility
- User-review requirement
- Before/after impact
- Audit record

---

# 4. أهم ثلاث واجهات للمستخدم

## 4.1 Scan Only

يجب توفير:

```python
import {{IMPORT_NAME}} as sp

scan = sp.scan(df)
```

أو:

```python
scan = sp.scan_only(df)
```

هذه الوظيفة:

- لا تعدّل البيانات.
- تفحص كل الاختبارات القابلة للتطبيق.
- تعرض Progress من 0% إلى 100%.
- تكتشف المشاكل.
- تصنفها.
- تقدم توصيات.
- تنتج تقريرًا قبل التنظيف.

مثال النتيجة:

```python
scan.issues
scan.summary
scan.health_score
scan.coverage
scan.recommendations
scan.report()
```

---

## 4.2 Automatic Safe Preparation

يجب توفير:

```python
result = sp.auto_prepare(df)
```

ويجب أن تقوم بـ:

- Full profiling.
- Full issue detection.
- Safe auto fixes only.
- Warnings.
- Escalation عندما توجد مشاكل غامضة.
- قبل/بعد EDA.
- Validation.
- Audit.
- Pipeline generation.
- Reproducibility metadata.

النواتج:

```python
result.clean_df
result.issues
result.fixed_issues
result.unresolved_issues
result.warnings
result.before_report
result.after_report
result.comparison_report
result.audit_log
result.pipeline
result.health_score_before
result.health_score_after
result.needs_guided_review
```

ويجب توفير اختصار بسيط:

```python
clean_df = sp.clean(df)
```

لكن دون إخفاء التحذيرات المهمة.

---

## 4.3 Guided Preparation

يجب توفير:

```python
result = sp.guided_prepare(df)
```

أو الانتقال من Auto Mode:

```python
auto = sp.auto_prepare(df)

if auto.needs_guided_review:
    guided = auto.open_guided()
```

يجب أن يسأل المستخدم فقط عندما:

- يوجد أكثر من علاج معقول.
- الثقة منخفضة.
- المشكلة Semantic.
- القرار Domain-specific.
- الإصلاح قد يغير التحليل الإحصائي.
- قد يحدث Data Leakage.
- يوجد Duplicate متعارض.
- التاريخ غير صالح لكن لا يمكن استنتاج البديل.
- توجد Formula محتملة غير مؤكدة.
- توجد وحدة أو عملة غير واضحة.
- توجد مشكلة غير معتادة.

الخيارات:

```text
Use recommendation
Choose another method
Compare methods
Preview
Define custom rule
Skip
Mark as accepted
Leave unresolved
```

---

# 5. نظام Progress

يجب الفصل بين:

## Scan Progress

```text
0% → 100%
```

هذا يعني نسبة الاختبارات القابلة للتطبيق التي تم تنفيذها.

مثال:

```text
Applicable checks: 183
Completed:         183
Skipped:            18
Not applicable:     12

Scan coverage:     100%
```

ولا يعني أن البيانات أصبحت صحيحة 100%.

---

## Data Health Score

مثال:

```text
Before Cleaning: 61/100
After Cleaning:  93/100
```

مع أبعاد مستقلة:

- Completeness
- Validity
- Consistency
- Uniqueness
- Integrity
- Semantic Quality
- Statistical Preservation
- ML Readiness
- Econometrics Readiness
- Time-Series Readiness

---

# 6. نظام Warnings وEscalation

الوضع الأوتوماتيكي يجب أن يعرف متى يتوقف عن الإصلاح.

الحالات النهائية:

```text
CLEAN
CLEAN_WITH_NOTES
CLEAN_WITH_WARNINGS
PARTIALLY_RESOLVED
GUIDED_REVIEW_RECOMMENDED
GUIDED_REVIEW_REQUIRED
DOMAIN_REVIEW_REQUIRED
BLOCKED
```

مستويات التنبيه:

```text
INFO
NOTICE
WARNING
HIGH_WARNING
CRITICAL_REVIEW
BLOCKING
```

تصنيف قابلية الإصلاح:

```text
SAFE_AUTO_FIX
AUTO_FIX_WITH_LOG
USER_CONFIRMATION_REQUIRED
DOMAIN_RULE_REQUIRED
AMBIGUOUS
UNRESOLVED
DO_NOT_TOUCH
```

يجب أن يكون هناك:

```python
result.needs_guided_review
result.review_queue
result.blocking_issues
result.unusual_issues
```

---

# 7. Unusual Issue Detection

أنشئ:

```python
UnusualIssueDetector
```

لاكتشاف أنماط لا تدخل بوضوح ضمن المشاكل التقليدية.

أمثلة:

- Unknown value pattern.
- Unexpected cross-column relationship.
- New unseen categorical pattern.
- Mixed units.
- Unknown currency representation.
- Possible formula violation.
- Encoding corruption.
- Structural anomaly.
- Unexpected schema mutation.
- Sudden missingness shift.
- Unexpected distribution or category explosion.

المكتبة يجب أن تقول:

```text
Unknown / unusual data-quality pattern detected.

Automatic repair was intentionally skipped.

Recommended:
Continue in Guided Mode.
```

---

# 8. مشاكل البيانات التي يجب تغطيتها

على الأقل:

## Missingness

- Explicit NA
- Empty strings
- Whitespace
- Custom missing tokens
- Sentinel missing values
- Structural missingness
- Conditional missingness
- Time-dependent missingness
- Group-dependent missingness
- Missingness pattern
- MAR/MCAR/MNAR diagnostics عندما تكون قابلة للتطبيق

## Data Types

- Wrong dtype
- Mixed dtype
- Numeric-as-string
- Dates-as-string
- Currency strings
- Percent strings
- Boolean variants
- Object columns with hidden structure
- Semantic type inference
- Probabilistic type inference

## Numeric Quality

- Invalid range
- Negative values where impossible
- Zero where impossible
- Infinite values
- NaN
- Extreme precision
- Rounding anomalies
- Sentinel values
- Scale mismatch
- Unit mismatch

## Dates

- Invalid dates
- Impossible dates
- Ambiguous dates
- Multiple date formats
- Locale ambiguity
- Timezone inconsistency
- Duplicate timestamps
- Missing periods
- Irregular frequency
- Start/end contradictions

## Text

- Leading/trailing spaces
- Multiple spaces
- Case inconsistency
- Unicode corruption
- Unicode confusables
- Mojibake
- Encoding issues
- Accents
- Typographical variants
- Invisible characters
- Control characters

## Categories

- Case variants
- Spelling variants
- Fuzzy duplicates
- High cardinality
- Rare categories
- Unknown categories
- Dirty categorical data
- Synonyms
- Locale variants

## Duplicates

- Exact duplicates
- Duplicate keys
- Conflicting duplicate IDs
- Near duplicates
- Entity duplicates
- Record linkage
- Entity resolution

## Cross-field Consistency

- Date logic
- Country-city conflicts
- Country-currency warnings
- Quantity/price/amount inconsistencies
- Status/payment contradictions
- Identifier/year contradictions
- Mathematical candidate invariants
- Business rule violations

## Outliers / Anomalies

- Univariate
- Multivariate
- Contextual
- Collective
- Time-series
- Model-based
- ML-based

## Dataset Structure

- Empty rows
- Empty columns
- Duplicate columns
- Corrupted headers
- Footer rows
- Metadata mixed with data
- Merged-cell artifacts
- Shifted rows
- Schema drift
- Schema evolution
- Column ordering changes

---

# 9. Missing Data Treatment Engine

يجب دعم:

- Drop
- Mean
- Median
- Mode
- Constant
- Group-wise imputation
- Forward fill
- Backward fill
- Interpolation
- KNNImputer
- IterativeImputer
- MissingIndicator
- MICE
- Multiple Imputation
- miceforest-style approaches
- Matrix completion approaches
- Time-aware imputation
- Panel-aware imputation

يجب توفير مقارنة:

```python
project.compare_imputation(
    column="income",
    methods=[
        "median",
        "knn",
        "iterative",
        "mice",
        "group_median"
    ]
)
```

ويتم تقييم:

- Distribution preservation
- Variance preservation
- Correlation preservation
- Bias
- Runtime
- Memory
- Leakage risk
- Downstream model effect

---

# 10. Encoding Engine

دعم:

- One Hot
- Ordinal
- Target
- Binary
- Base-N
- Hashing
- Count/Frequency
- CatBoost
- Leave-One-Out
- James-Stein
- Weight of Evidence
- GLMM
- M-estimator
- Quantile
- MinHash
- GapEncoder
- Similarity-based encoders

مع:

```python
project.encoding_advisor()
```

والاختيار يعتمد على:

- Cardinality
- Dataset size
- Target availability
- Model type
- Leakage risk
- Interpretability
- Memory
- Sparsity

---

# 11. Scaling & Transformations

دعم:

- StandardScaler
- MinMaxScaler
- RobustScaler
- MaxAbsScaler
- Normalizer
- Log
- Log1p
- Box-Cox
- Yeo-Johnson
- Quantile transforms
- Power transforms
- Winsorization
- Clipping
- Binning
- Discretization

مع Recommendation Engine.

---

# 12. Feature Engineering

دعم:

- Datetime features
- Lag features
- Rolling features
- Window features
- Expanding features
- Polynomial features
- Interaction features
- Relational feature generation
- Automated feature engineering

مع:

- Feature lineage
- Leakage guard
- Feature importance preview
- Feature count warnings
- Redundancy detection

---

# 13. Time-Series & Panel Preparation

## Time Series

- Frequency inference
- Missing periods
- Duplicate timestamps
- Irregular intervals
- Timezone
- Resampling
- Time-aware interpolation
- Lag integrity
- Temporal leakage guard
- Rolling-window validation

## Panel

- Entity-time key validation
- Duplicate entity-time rows
- Unbalanced panel
- Missing periods by entity
- Constant-within-entity variables
- Insufficient within variation
- Inconsistent identifiers
- Cross-sectional and temporal anomalies

---

# 14. Econometrics-Aware Preparation

يجب دعم وضع:

```python
project.set_goal("econometrics")
```

أو:

```python
project.set_context("panel")
project.set_context("timeseries")
```

وتغيير التوصيات وفق نوع التحليل.

يجب عدم تطبيق preprocessing الخاص بـML بشكل أعمى على البيانات المخصصة للقياس الاقتصادي.

---

# 15. ML-Aware Preparation

دعم:

```python
project.set_goal("machine_learning")
```

مع:

- Train/test leakage guard
- Target leakage detection
- Fit only on training data
- Pipeline compatibility
- sklearn Transformer API
- ColumnTransformer integration
- Imbalanced data handling
- Feature selection
- Data readiness

---

# 16. Validation

يجب دمج فلسفات:

- Pandera
- Great Expectations
- Pointblank
- Soda
- Pydantic
- Frictionless

توفير:

```python
plan = (
    project.validate()
    .column_exists("invoice_id")
    .unique("invoice_id")
    .between("rating", 1, 5)
    .custom("payment_amount <= invoice_amount")
)

result = plan.run()
```

مع:

```python
valid, invalid = result.split()
```

---

# 17. Data Contracts

توفير:

```python
project.contract()
```

ودعم:

- Column definitions
- Semantic types
- Nullability
- Ranges
- Units
- Primary keys
- Unique constraints
- Allowed values
- Relationships
- Quality expectations

مع:

- Versioning
- Backward compatibility
- Forward compatibility
- Breaking changes
- Semantic breaking changes

---

# 18. Privacy & PII

توفير:

```python
project.scan_privacy()
```

ودعم:

- Names
- Email
- Phone
- IDs
- Bank accounts
- Cards
- IP
- Location
- PII in free text

تصنيف:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
SENSITIVE
DIRECT_IDENTIFIER
QUASI_IDENTIFIER
```

إجراءات:

- Mask
- Redact
- Hash
- Tokenize
- Pseudonymize
- Generalize
- Drop

مع Preview + Audit.

---

# 19. Data Drift & Observability

دعم:

- PSI
- KS
- Chi-square
- Jensen-Shannon
- Wasserstein
- MMD
- Classifier-based drift
- Category drift
- Missingness drift
- Schema drift
- Cleaning drift
- Online drift

مع:

```python
project.compare_reference(reference_df)
```

و:

```python
project.monitor()
```

---

# 20. Data Lineage & Reproducibility

كل عملية يجب أن تسجل:

- Input dataset
- Output dataset
- Operation
- Parameters
- Timestamp
- Rows affected
- Columns affected
- Before hash
- After hash
- Reason
- Confidence
- User/auto decision

دعم:

```python
project.history()
project.diff("v2", "v5")
project.rollback("v2")
project.undo()
```

مع:

- Dataset fingerprint
- Schema fingerprint
- Environment manifest
- Package versions
- Random seeds
- Locale
- Timezone

---

# 21. Idempotence

دعم:

```python
project.test_idempotence()
```

واختبار:

```text
clean(clean(df)) == clean(df)
```

---

# 22. Multi-backend Architecture

المكتبة يجب ألا تكون مقيدة بـPandas فقط.

دعم تدريجي:

- Pandas
- Polars
- PyArrow
- DuckDB
- Dask
- PySpark
- Ibis
- SQL backends

استخدم abstraction layer مناسبة على نمط:

- Narwhals
- Ibis

التصميم:

```text
User API
   ↓
Semantic Operation IR
   ↓
Backend Planner
   ↓
Pandas / Polars / Arrow / DuckDB / Ibis / Dask / Spark
```

ممنوع Silent Fallback إلى Pandas إذا كان ذلك قد يستهلك الذاكرة بصورة خطرة.

---

# 23. Interactive Studio

يجب إنشاء واجهة جميلة وحديثة.

اقتراح:

```python
sp.studio(df)
```

الواجهة تشمل:

- Data Command Center
- Smart Data Grid
- Issue Inbox
- Column Inspector
- Missing Data Lab
- Outlier Lab
- Duplicate / Entity Resolution Lab
- Text Integrity Workbench
- Date Intelligence Workbench
- Semantic Field Workbench
- Encoding Lab
- Scaling/Transformation Lab
- Feature Engineering Workbench
- Validation Center
- Data Contract Center
- Privacy Center
- Drift Center
- Pipeline Canvas
- Audit Timeline
- Reports Center

كل Click يجب أن يكون reproducible.

أي عملية GUI يجب أن تولد:

- Operation object
- Python code
- Pipeline node
- Audit record
- Undo state

---

# 24. Visualization

دعم محركين:

## Static

- Matplotlib
- Seaborn-like outputs

## Interactive

- Plotly-style charts
- Hover
- Zoom
- Pan
- Selection
- Cross-filtering
- Linked views
- Slider
- Animation عند الحاجة

لا تستخدم Animation للزينة.

تستخدم فقط عند وجود معنى مثل:

```text
Raw
→ Type Repair
→ Missing Treatment
→ Outlier Treatment
→ Final
```

---

# 25. Large Data Visualization

إذا كانت البيانات ضخمة:

```text
Small      → full plot
Medium     → sampling
Large      → aggregation/rasterization
Streaming  → rolling window
```

يجب إظهار ملاحظة إذا كان الرسم مبنيًا على Sample.

---

# 26. Reports

يجب إنتاج تقارير قبل وبعد التنظيف.

## Pre-Cleaning Report

يشمل:

- Dataset overview
- Schema
- Semantic types
- Mixed types
- Missingness
- Duplicates
- Outliers
- Invalid values
- Invalid dates
- Ambiguous dates
- Categories
- Cross-column issues
- Candidate invariants
- Privacy
- Drift if reference exists
- Data health
- Readiness scores
- Warnings

## Post-Cleaning Report

يشمل:

- What changed
- What was fixed
- What was not fixed
- What requires review
- New health score
- Statistical preservation
- Schema changes
- Data loss
- Information loss
- Reproducibility information

## Before/After Comparison

يشمل:

- Missingness before/after
- Distribution before/after
- Correlation before/after
- Variance
- Mean
- Median
- Quantiles
- Skewness
- Kurtosis
- Category changes
- Row count
- Column count
- Outliers
- Health score
- Data preservation score

---

# 27. Report Formats

دعم:

- Interactive HTML
- PDF
- Markdown
- JSON
- YAML
- Notebook embedded
- PNG
- SVG

ثم مستقبلًا:

- DOCX
- PPTX

---

# 28. Reporting Profiles

توفير:

```python
project.report(profile="executive")
project.report(profile="technical")
project.report(profile="audit")
project.report(profile="research")
project.report(profile="ml")
project.report(profile="econometrics")
```

---

# 29. Treatment Sandbox

يجب أن يستطيع المستخدم مقارنة عدة طرق قبل التطبيق.

مثال:

```text
Missing value treatment

Median            74/100
KNN               82/100
Iterative         89/100
Group Median      92/100
Keep NA + Flag    80/100
```

واجهة:

```text
Compare
Preview
Apply
Explain
Ignore
```

---

# 30. Explainability

توفير:

```python
project.explain(issue_id)
project.explain("income")
```

ويشرح:

- لماذا اكتُشفت المشكلة؟
- لماذا أوصى بهذه الطريقة؟
- ما البدائل؟
- لماذا تم رفض طرق أخرى؟
- ما أثر العلاج المتوقع؟
- ما درجة الثقة؟

---

# 31. Repair Confidence

كل اقتراح:

```text
Recommended treatment: Group Median
Confidence: 92%
Risk: Low
Expected distortion: 1.8%
```

سياسة:

```text
>= 98%      SAFE AUTO FIX
85–98%      AUTO + LOG
60–85%      USER REVIEW
<60%        ABSTAIN
```

يجب أن تكون thresholds قابلة للتخصيص.

---

# 32. Root Cause Analysis

يجب ألا تكتفي المكتبة بإصلاح المشاكل.

مثال:

```text
8,219 / 8,423 invalid dates
come from:

source_file = branch_03.xlsx

Probable cause:
branch_03 export uses DD-MM-YY
while other sources use ISO-8601.
```

---

# 33. Rule Learning

المكتبة يمكن أن تتعلم قواعد المستخدم.

مثال:

```text
Algérie → Algeria
```

تخزن في:

- Project Rules
- Organization Rules
- Domain Rules
- Built-in Rules

لكن لا تتحول قاعدة محلية إلى Global Rule تلقائيًا.

---

# 34. Dataset Card & Data Dictionary

توفير:

```python
project.dataset_card()
project.data_dictionary()
```

ويشمل:

- Source
- Acquisition date
- Owner
- Tables
- Variables
- Types
- Semantic types
- Units
- Keys
- Missingness
- Known issues
- Cleaning history
- Privacy classification
- Intended use
- Limitations

---

# 35. Plugin Architecture

يفضل فصل المشروع إلى:

```text
{{PYPI_PACKAGE_NAME}}-core
{{PYPI_PACKAGE_NAME}}-viz
{{PYPI_PACKAGE_NAME}}-ml
{{PYPI_PACKAGE_NAME}}-timeseries
{{PYPI_PACKAGE_NAME}}-panel
{{PYPI_PACKAGE_NAME}}-privacy
{{PYPI_PACKAGE_NAME}}-text
{{PYPI_PACKAGE_NAME}}-spark
{{PYPI_PACKAGE_NAME}}-geospatial
{{PYPI_PACKAGE_NAME}}-econometrics
```

أو extras:

```bash
pip install "{{PYPI_PACKAGE_NAME}}[viz]"
pip install "{{PYPI_PACKAGE_NAME}}[privacy]"
pip install "{{PYPI_PACKAGE_NAME}}[spark]"
```

---

# 36. هيكل المستودع

اقترح بنية احترافية مثل:

```text
repository/
│
├── src/
│   └── {{IMPORT_NAME}}/
│       ├── __init__.py
│       ├── api/
│       ├── core/
│       ├── profiling/
│       ├── diagnostics/
│       ├── semantic/
│       ├── quality/
│       ├── cleaning/
│       ├── preprocessing/
│       ├── missing/
│       ├── outliers/
│       ├── encoding/
│       ├── transformations/
│       ├── validation/
│       ├── contracts/
│       ├── privacy/
│       ├── drift/
│       ├── lineage/
│       ├── recommendation/
│       ├── evaluation/
│       ├── reporting/
│       ├── visualization/
│       ├── interactive/
│       ├── pipeline/
│       ├── backends/
│       ├── timeseries/
│       ├── panel/
│       ├── econometrics/
│       ├── ml/
│       ├── plugins/
│       └── utils/
│
├── tests/
├── benchmarks/
├── examples/
├── notebooks/
├── docs/
├── datasets/
├── scripts/
├── .github/
│   └── workflows/
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CITATION.cff
├── REFERENCES.md
├── THIRD_PARTY_NOTICES.md
├── LICENSE
├── pyproject.toml
└── mkdocs.yml
```

---

# 37. README.md — شرط إلزامي

ملف README يجب أن يكون **موسوعيًا ومفيدًا للمستخدم الحقيقي**، وليس صفحة تسويقية مختصرة.

يجب أن يحتوي على:

1. اسم المشروع.
2. وصف واضح.
3. لماذا هذه المكتبة؟
4. الفلسفة.
5. أهم الميزات.
6. مقارنة مختصرة مع الأدوات الأخرى.
7. Supported backends.
8. Installation.
9. Quick Start.
10. Scan Only.
11. Automatic Cleaning.
12. Guided Cleaning.
13. Interactive Studio.
14. Reports.
15. Missing Data.
16. Data Types.
17. Categories.
18. Dates.
19. Text.
20. Duplicates.
21. Outliers.
22. Encoding.
23. Scaling.
24. Transformations.
25. Validation.
26. Data Contracts.
27. Privacy.
28. Drift.
29. Lineage.
30. Time Series.
31. Panel Data.
32. Econometrics.
33. ML.
34. Export.
35. API Overview.
36. Documentation links.
37. Examples.
38. Contributing.
39. Citation.
40. License.
41. Contact.

---

# 38. README يجب أن يوثق كل Function مهمة

لكل Function عامة يجب عرض:

## Function Name

مثال:

```python
sp.auto_prepare()
```

### Purpose

ماذا تفعل؟

### Syntax

```python
sp.auto_prepare(
    data,
    *,
    profile="balanced",
    on_warning="continue",
    on_critical="guided",
    confidence_threshold=0.98,
    generate_reports=True,
    return_pipeline=True,
)
```

### Parameters

جدول كامل:

| Parameter | Type | Default | Required | Description |
|---|---|---|---|---|

### Returns

مثال:

```python
PreparationResult
```

مع شرح جميع الخصائص.

### Basic Example

مثال قابل للتشغيل.

### Realistic Example

مثال قريب من بيانات حقيقية.

### Notes

ملاحظات الاستخدام.

### Warnings

الأخطاء أو الحالات التي تحتاج الحذر.

### See Also

الدوال المرتبطة.

---

# 39. Documentation Site

لا يكفي README.

أنشئ Documentation كاملة باستخدام:

- MkDocs Material أو
- Sphinx

أفضل MkDocs Material إذا كان مناسبًا.

البنية:

```text
docs/

index.md

getting-started/
    installation.md
    quickstart.md
    concepts.md

user-guide/
    scan.md
    auto-prepare.md
    guided-prepare.md
    studio.md

cleaning/
    missing.md
    duplicates.md
    text.md
    dates.md
    numeric.md
    categorical.md
    outliers.md

preprocessing/
    encoding.md
    scaling.md
    transformations.md
    feature-engineering.md
    imbalance.md

validation/
    schemas.md
    contracts.md

advanced/
    timeseries.md
    panel.md
    econometrics.md
    ml.md
    drift.md
    privacy.md
    lineage.md

reports/
    html.md
    pdf.md
    comparison.md

api/
    index.md
    core.md
    cleaning.md
    preprocessing.md
    validation.md
    reporting.md

examples/
    beginner.md
    research.md
    ml.md
    panel.md
    timeseries.md

reference/
    glossary.md
    configuration.md
    exceptions.md
    issue-codes.md
```

---

# 40. API Reference كامل

كل Public:

- Function
- Class
- Method
- Parameter
- Attribute
- Return object
- Exception
- Enum
- Configuration option

يجب أن يكون موثقًا.

لا توجد Public API بلا Documentation.

---

# 41. Syntax Cookbook

أنشئ ملفًا:

```text
docs/SYNTAX_COOKBOOK.md
```

أو قسمًا مكافئًا.

يجب أن يكون مثل قاموس أو Cheat Sheet.

مثال:

```markdown
# Load Data

```python
df = sp.read("data.xlsx")
```

# Scan

```python
scan = sp.scan(df)
```

# Automatic Clean

```python
result = sp.auto_prepare(df)
```

# Guided Clean

```python
result = sp.guided_prepare(df)
```

# Show Problems

```python
result.issues
```

# Export Clean Data

```python
result.clean_df.to_excel("clean.xlsx", index=False)
```
```

يجب أن يستطيع المستخدم الذي لا يعرف API أن يجد الكود المطلوب بسرعة.

---

# 42. Function Catalog

أنشئ ملفًا:

```text
docs/FUNCTION_CATALOG.md
```

يحتوي على **كل Public Function** مرتبة حسب المجال.

مثال:

```text
Loading
-------
read()
read_excel()
read_csv()

Profiling
---------
scan()
profile()
summary()

Cleaning
--------
clean()
auto_prepare()
guided_prepare()

...
```

لكل واحدة:

- Signature
- Description
- Example
- Link to full documentation

---

# 43. Searchable Documentation

يجب أن تكون Documentation قابلة للبحث.

المستخدم يجب أن يستطيع البحث عن:

```text
missing
KNN
mixed dtype
outlier
panel
encoding
```

ويصل إلى الصفحة المناسبة.

---

# 44. Examples

أنشئ أمثلة فعلية:

```text
examples/
01_basic_scan.py
02_auto_cleaning.py
03_guided_cleaning.py
04_missing_data.py
05_mixed_types.py
06_duplicate_resolution.py
07_outlier_analysis.py
08_interactive_studio.py
09_reports.py
10_ml_pipeline.py
11_timeseries.py
12_panel_data.py
13_econometrics.py
14_large_data_polars.py
15_duckdb.py
```

---

# 45. Notebooks

أنشئ Notebooks تعليمية.

كل Notebook:

- Dataset صغيرة.
- شرح نظري.
- كود.
- نتائج.
- تفسير النتائج.
- قبل/بعد.
- Export.

---

# 46. Realistic Demo Dataset

أنشئ Dataset تجريبية متعمدة المشاكل، مثل:

- Mixed types
- Missing values
- Invalid dates
- Duplicate IDs
- Conflicting duplicates
- Dirty categories
- Unicode corruption
- Wrong currencies
- Outliers
- Sentinels
- Invalid ranges
- Cross-field contradictions

واستخدمها في README والدليل والاختبارات.

---

# 47. Error Messages

رسائل الخطأ يجب أن تكون مفهومة.

سيئ:

```text
ValueError: dtype mismatch
```

أفضل:

```text
SmartPrepTypeError:
Column 'unit_price' contains mixed numeric and text representations.

Detected:
- numeric: 82.4%
- numeric strings: 15.1%
- invalid strings: 2.5%

Try:
sp.guided_prepare(df)
or
sp.convert_numeric(df, "unit_price", errors="review")
```

---

# 48. Exceptions

أنشئ Exceptions واضحة:

```python
SmartPrepError
SmartPrepTypeError
SmartPrepSchemaError
SmartPrepValidationError
SmartPrepBackendError
SmartPrepAmbiguityError
SmartPrepUnsafeRepairError
SmartPrepPrivacyError
SmartPrepContractError
```

---

# 49. Configuration

دعم Configuration:

```python
sp.configure(
    language="en",
    report_theme="light",
    confidence_threshold=0.95,
    backend="auto",
)
```

ودعم YAML:

```yaml
profile: research
backend: auto

auto_fix:
  threshold: 0.98

reports:
  html: true
  pdf: true
```

---

# 50. Internationalization

صمم النظام بحيث يمكن إضافة:

- English
- Arabic
- French

على الأقل للواجهة والتقارير مستقبلًا.

---

# 51. Testing

استخدم:

- pytest
- property-based testing
- Hypothesis حيث مناسب

الاختبارات:

- Unit
- Integration
- Regression
- Golden report
- Backend parity
- Performance
- Memory
- API
- Documentation examples

---

# 52. Property-Based Testing

أمثلة:

- rename columns لا يغير عدد الصفوف.
- fill missing لا يزيد missingness دون سبب.
- parser الناجح ينتج النوع المتوقع.
- idempotent cleaner يعطي نفس النتيجة عند التشغيل مرتين.

---

# 53. Benchmark Suite

أنشئ:

```text
SmartPrepBench
```

يشمل بيانات ذات مشاكل معروفة.

المقاييس:

- Detection precision
- Detection recall
- Repair accuracy
- False positives
- False negatives
- Information loss
- Distribution preservation
- Runtime
- Peak memory
- User effort
- Backend parity

---

# 54. المنافسون والمراجع

راجع بانتظام أفكار ومصادر:

- pandas
- Polars
- PyArrow
- DuckDB
- Dask
- PySpark
- Narwhals
- Ibis
- PyJanitor
- DataPrep
- ydata-profiling
- Sweetviz
- DataProfiler
- Skimpy
- missingno
- AutoViz
- PyGWalker
- Graphic Walker
- D-Tale
- PandasGUI
- Pandera
- Great Expectations
- Pointblank
- Soda
- Frictionless
- Pydantic
- scikit-learn
- Feature-engine
- skrub
- category_encoders
- imbalanced-learn
- miceforest
- fancyimpute
- PyOD
- Cleanlab
- RapidFuzz
- recordlinkage
- dedupe
- ftfy
- Unidecode
- dateparser
- python-dateutil
- phonenumbers
- email-validator
- Featuretools
- whylogs
- Evidently
- Deepchecks
- Alibi Detect
- River
- Presidio
- OpenLineage
- SDV
- Hypothesis
- Plotly
- Matplotlib
- Seaborn
- Altair
- HoloViews
- Datashader
- Panel / Tabulator

---

# 55. REFERENCES.md

أنشئ ملفًا موثقًا ومقسمًا حسب المجال.

لكل مرجع:

```markdown
## Pandera

- Purpose:
- Official Documentation:
- GitHub:
- PyPI:
- Relevant SmartPrep features:
- What we learn from it:
- What SmartPrep adds beyond it:
```

---

# 56. Competitive Gap Registry

أنشئ:

```text
competitive_gap_registry.yaml
```

مثال:

```yaml
project: pygwalker

observed_strengths:
  - drag_drop_exploration
  - notebook_ui

observed_gaps:
  - no_full_cleaning_decision_engine
  - limited_repair_audit

smartprep_response:
  - treatment_sandbox
  - repair_triage
  - reproducible_clicks

last_reviewed: YYYY-MM-DD
```

---

# 57. License Safety

لا تنسخ كود المنافسين إلا إذا كان الترخيص يسمح بذلك ومع الالتزام الكامل بشروطه.

الأولوية:

- تعلم الأفكار.
- إعادة التنفيذ بصورة أصلية.
- توثيق مصدر الإلهام.
- مراجعة الترخيص.

أنشئ:

```text
THIRD_PARTY_NOTICES.md
DEPENDENCY_LICENSES.json
```

---

# 58. GitHub Repository

استخدم:

`https://github.com/merwanroudane/smartprep`

المستودع يجب أن يكون مرتبًا واحترافيًا.

يجب:

- Branching واضح.
- Commit messages جيدة.
- Tags.
- Releases.
- Changelog.
- GitHub Actions.
- Testing.
- Linting.
- Type checking.
- Documentation build.
- PyPI publish workflow.
- Security checks.

---

# 59. CI/CD

GitHub Actions تشمل:

- Python versions supported.
- Windows/Linux/macOS.
- Tests.
- Ruff.
- Black أو formatter مناسب.
- mypy/pyright.
- Documentation build.
- Package build.
- Twine check.
- Optional coverage.
- Release workflow.

---

# 60. Packaging

استخدم:

```text
pyproject.toml
```

مع:

- Metadata
- Dependencies
- Optional dependencies
- Python requirement
- Classifiers
- Project URLs
- Documentation URL
- Repository URL
- Issues URL

---

# 61. Code Quality

استخدم:

- Type hints.
- Docstrings.
- Clear naming.
- Small composable functions.
- Stable public API.
- Private internal APIs.
- No duplicated logic.
- Separation of concerns.
- Dependency injection where useful.
- Protocols/interfaces for backends.

---

# 62. Docstring Standard

اختر نمطًا موحدًا:

- NumPy style أو
- Google style

كل Public Function يجب أن تحتوي:

- Summary
- Parameters
- Returns
- Raises
- Notes
- Examples
- See Also

---

# 63. Versioning

استخدم Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

مع:

```text
CHANGELOG.md
```

---

# 64. API Stability

حدد:

- Public
- Experimental
- Deprecated
- Internal

ولا تكسر API بدون Deprecation path.

---

# 65. Performance

يجب قياس:

- Runtime
- Memory
- Dataset size
- Backend

واستخدام lazy execution عند الإمكان.

---

# 66. Security

راجع:

- unsafe file loading
- arbitrary code execution
- deserialization
- path traversal
- HTML injection
- report injection
- secrets
- PII leakage

---

# 67. Logging

دعم:

```python
sp.configure(log_level="INFO")
```

مع Logs واضحة دون إغراق المستخدم.

---

# 68. Output Objects

صمم Objects واضحة مثل:

```python
ScanResult
PreparationResult
Issue
Recommendation
TreatmentCandidate
ValidationResult
ReportArtifact
Pipeline
AuditRecord
DataHealthScore
```

---

# 69. Issue Object

مثال:

```python
Issue(
    id="TYPE-001",
    column="unit_price",
    category="mixed_type",
    severity="high",
    confidence=0.99,
    auto_fixable=True,
)
```

---

# 70. PreparationResult

يجب أن يكون غنيًا:

```python
result.clean_df
result.raw_df
result.issues
result.fixed_issues
result.unresolved_issues
result.warnings
result.review_queue
result.before_report
result.after_report
result.comparison_report
result.pipeline
result.audit_log
result.metrics
result.health_score_before
result.health_score_after
```

---

# 71. Export

دعم:

```python
result.export_data("clean.xlsx")
result.export_report("report.html")
result.export_report("report.pdf")
result.export_pipeline("pipeline.py")
result.export_config("pipeline.yaml")
result.export_audit("audit.json")
```

---

# 72. Code Generation

كل عملية تفاعلية يجب أن يمكن تحويلها إلى كود.

مثال:

```python
project.export_python()
```

وينتج Pipeline قابلة للتشغيل.

---

# 73. No Silent Data Mutation

لا تعدل DataFrame الأصلية دون اختيار صريح.

Default:

```python
inplace=False
```

---

# 74. Preview Before Dangerous Operations

أي:

- Row deletion
- Column deletion
- Outlier removal
- Category merge
- Imputation عالية التأثير
- Deduplication غير قطعي

يجب أن يدعم:

```python
preview=True
```

---

# 75. Research Profile

أنشئ Profile:

```python
sp.auto_prepare(df, profile="research")
```

يكون محافظًا:

- لا يحذف outliers آليًا.
- لا يغير distribution بقوة.
- يحذر من imputation.
- يحفظ original values.
- يقدم statistical impact.
- يوفر audit كامل.
- يمنع leakage.

---

# 76. Safe Defaults

Default behavior يجب أن يكون آمنًا.

لا:

- drop rows بصمت.
- drop columns بصمت.
- replace ambiguous values.
- infer impossible corrections.
- merge entities بثقة منخفضة.
- alter target values.
- use future information.

---

# 77. Data Preservation

أضف:

```text
Data Preservation Score
Information Loss Score
Transformation Risk Score
```

---

# 78. Before/After Statistical Guardrails

قارن:

- Mean
- Median
- Variance
- Quantiles
- Correlations
- Distribution distances
- Category proportions
- Target relationship

وإذا حدث تغيير كبير:

```text
WARNING:
This transformation materially changed the distribution.
```

---

# 79. واجهة المستخدم

يجب أن يكون التصميم:

- Light.
- Modern.
- Clean.
- Professional.
- Responsive.
- واضح.
- بدون ألوان داكنة كافتراضي.
- لا يزدحم بالمعلومات.
- يسمح للمستخدم المبتدئ والمتقدم.

---

# 80. واجهة Guided Mode

يجب عرض:

```text
Problem
Evidence
Recommendation
Confidence
Alternatives
Impact
Preview
```

مع Buttons:

```text
Apply recommendation
Choose alternative
Compare
Preview
Skip
Custom rule
```

---

# 81. Accessibility

راعِ:

- Keyboard navigation
- Readable fonts
- Color contrast
- Non-color-only warnings
- Screen-reader-friendly labels قدر الإمكان

---

# 82. Documentation Quality Gate

أي Feature جديدة لا تعتبر مكتملة إلا إذا كان لها:

- Unit tests.
- Integration tests عند الحاجة.
- Docstring.
- API reference.
- User guide entry.
- Runnable example.
- Changelog entry.
- Reference/source إذا كانت مبنية على منهج معروف.
- Benchmark إذا كانت performance-sensitive.

---

# 83. README Quality Gate

README يجب أن يكون قابلًا لأن يتعلم المستخدم المكتبة منه حتى لو لم يفتح باقي التوثيق.

لكن لا تحوله إلى قائمة لا نهائية بلا تنظيم.

استخدم:

- Table of contents.
- Collapsible sections إذا مناسب.
- Short examples أولًا.
- Links إلى التفاصيل المتقدمة.

---

# 84. Code Examples

كل مثال في README وDocumentation يجب أن:

- يكون executable.
- يستخدم API حقيقية.
- يمر ضمن CI قدر الإمكان.
- لا يعتمد على functions غير موجودة.
- يتم تحديثه عند تغيير API.

---

# 85. Documentation Tests

نفذ اختبارات على أمثلة التوثيق باستخدام doctest أو pytest/documentation testing عندما يكون مناسبًا.

---

# 86. Beginner-to-Expert Documentation

قسّم الشرح إلى:

```text
Level 1 — Quick Start
Level 2 — Common Tasks
Level 3 — Full User Guide
Level 4 — Advanced Workflows
Level 5 — API Reference
Level 6 — Developer / Extension Guide
```

---

# 87. Developer Guide

أنشئ:

```text
docs/developer-guide/
```

يشمل:

- Architecture
- Adding a detector
- Adding a cleaner
- Adding a backend
- Adding a report
- Adding a visualization
- Adding a plugin
- Adding an issue type
- Adding a recommendation rule
- Testing conventions
- Documentation conventions

---

# 88. Extension API

أنشئ Plugin/Extension API يستطيع المستخدم من خلالها كتابة:

```python
@sp.detector(...)
def my_detector(...):
    ...
```

أو Interface مكافئة.

---

# 89. Custom Rules

دعم:

```python
project.add_rule(
    name="profit_non_negative",
    condition="reported_profit >= 0",
)
```

مع Python callable أيضًا.

---

# 90. Final Deliverables

يجب أن يحتوي المستودع النهائي على الأقل على:

- Working Python package.
- Public API.
- Auto mode.
- Guided mode.
- Scan mode.
- Interactive Studio.
- Reporting system.
- Tests.
- Benchmarks.
- Documentation.
- README.
- Syntax Cookbook.
- Function Catalog.
- Examples.
- Notebooks.
- Demo dataset.
- References.
- Changelog.
- CI/CD.
- Packaging.
- License.
- Citation.
- Contributor guide.
- Security policy.

---

# 91. أسلوب التنفيذ

لا تحاول بناء كل شيء دفعة واحدة بصورة غير قابلة للاختبار.

نفذ على مراحل:

## Phase 1 — Foundation

- repository
- package skeleton
- configuration
- issue model
- result model
- backend abstraction
- tests
- documentation system

## Phase 2 — Core Scan

- schema
- types
- missing
- duplicates
- numeric checks
- text checks
- dates
- categories

## Phase 3 — Auto Prepare

- safe fixes
- warnings
- audit
- reports
- clean_df

## Phase 4 — Guided Prepare

- review queue
- decisions
- preview
- alternatives
- persistence

## Phase 5 — Preprocessing

- imputation
- encoding
- scaling
- transformation

## Phase 6 — Advanced Quality

- entity resolution
- anomalies
- semantic rules
- contracts
- privacy

## Phase 7 — Interactive Studio

- data grid
- charts
- issue explorer
- treatment sandbox
- pipeline canvas

## Phase 8 — Multi-backend

- Polars
- Arrow
- DuckDB
- Ibis
- Dask/Spark later

## Phase 9 — Specialized Modes

- time series
- panel
- econometrics
- ML

## Phase 10 — Observability

- drift
- reference datasets
- monitoring
- online/streaming

---

# 92. التنفيذ يجب أن يكون Repository-first

كل مرحلة يجب أن:

1. تُنفذ في المستودع.
2. تضيف اختبارات.
3. تحدث README عند الحاجة.
4. تحدث Documentation.
5. تحدث CHANGELOG.
6. تمر CI.
7. لا تكسر الأمثلة الموجودة.

---

# 93. عند بدء العمل

قبل كتابة أي Module:

1. اقرأ الخطة المرجعية.
2. افحص المستودع الحالي.
3. لا تحذف ملفات موجودة دون سبب.
4. حدد ما الموجود وما الناقص.
5. أنشئ Implementation Roadmap.
6. ابدأ بالـCore.
7. اختبر كل مرحلة.

---

# 94. عند وجود قرار معماري

اختر الحل الذي يحقق:

1. correctness
2. safety
3. maintainability
4. reproducibility
5. extensibility
6. performance

ولا تختصر جودة التصميم من أجل إنجاز Feature سريعة.

---

# 95. القاعدة النهائية

أريد مكتبة يستطيع المستخدم المبتدئ أن يبدأ بها هكذا:

```python
import {{IMPORT_NAME}} as sp

result = sp.auto_prepare(df)

clean_df = result.clean_df
```

ويستطيع الباحث المتقدم العمل هكذا:

```python
project = sp.Project(df)

project.scan()
project.inspect()
project.compare_treatments()
project.add_rules()
project.validate()
project.prepare()
project.measure_impact()
project.export_pipeline()
```

ويستطيع المستخدم الذي يريد التحكم الكامل تشغيل:

```python
sp.studio(df)
```

ويجب أن تكون كل هذه المسارات متسقة مع بعضها، تستخدم نفس Core Engine، ولا يكون لكل واجهة منطق منفصل.

---

# 96. الهدف النهائي

الهدف ليس بناء مكتبة تحتوي أكبر عدد من Functions فقط.

الهدف هو بناء نظام يجعل Data Preparation:

- أسهل.
- أكثر أمانًا.
- أكثر تفسيرًا.
- أكثر علمية.
- أكثر تفاعلية.
- أكثر قابلية لإعادة الإنتاج.
- أكثر قابلية للتوسع.
- أقل عرضة للأخطاء الصامتة.

وتكون المكتبة:

> **A comprehensive intelligent and interactive data preparation platform for Python.**

