# SmartPrep v0.3.0.dev0 — مراجعة تحقق شاملة وفجوات ما قبل المرحلة التالية

## 1. الخلاصة التنفيذية

تمت مراجعة الحزمة:

`smartprep-0.3.0.dev0.tar.gz`

مراجعة فعلية للبنية، الكود، الاختبارات، الـREADME، الـArchitecture Decisions، طبقات Guided Mode وPreprocessing وValidation/Contracts وPrivacy وDrift وReporting وAudit/Snapshots.

### النتيجة العامة

النسخة `v0.3.0.dev0` تقدمت بصورة كبيرة جدًا مقارنة بـ`v0.1.0.dev0`.

النواة الحالية قوية ومتماسكة، ولا أوصي بإعادة بنائها.

الطبقات التالية أصبحت موجودة فعلًا:

- `scan()`
- `auto_prepare()`
- `guided_prepare()`
- `clean()`
- triage / repair eligibility
- audit trail
- snapshots / rollback
- completion states
- `verified_df`
- waivers
- health score الأساسي
- preprocessing fit/transform
- preprocessing advisor
- validation plans
- data contracts
- privacy scanner + basic transformations
- drift + cleaning drift
- Markdown/JSON reporting

لكن عبارة:

> “every layer from the review's gap list is now built, except the studio”

ليست دقيقة بعد.

ما يزال هناك عدد من الطبقات الكبيرة غير منفذة أو منفذة جزئيًا، وبعضها مذكور صراحة في README نفسه:

- Interactive Studio
- HTML/PDF reports
- Visualization / EDA engine
- Entity Resolution / Record Linkage
- Multi-backend execution
- Time-series diagnostics
- Panel diagnostics
- Advanced anomaly detection
- Full semantic cleaning
- Root-cause engine
- Rule learning / knowledge base
- Full benchmark suite
- Full documentation site

بالإضافة إلى ذلك، كشفت المراجعة أربع نقاط تقنية جديدة مهمة يجب إصلاحها.

---

# 2. ما تم التحقق منه فعليًا

## 2.1 البنية

عدد وحدات Python داخل `src/smartprep`:

```text
40 modules
```

عدد أسطر Python في `src + tests`:

```text
12,028 lines
```

إذن الرقم المذكور في تقرير التطوير صحيح تمامًا.

عدد الاختبارات المجمعة:

```text
306 tests
```

---

# 3. نتيجة الاختبارات

تم تشغيل:

```bash
PYTHONPATH=src python -m pytest -q
```

والنتيجة:

```text
255 passed
51 skipped
```

سبب الـ51 skipped:

ملف:

```text
data_project.xlsx
```

غير موزع داخل الـsdist.

الاختبارات نفسها توضح أنها تعمل فقط عندما يكون stress workbook موجودًا في repository development environment.

إذن ادعاء:

```text
255 passed, 51 skipped
```

صحيح.

لكن لم أستطع التحقق من ادعاء:

> “driving all ten capabilities end-to-end from the wheel”

من الـwheel نفسه، لأن الملف المرفق هنا هو **sdist tar.gz** وليس wheel.

---

# 4. ما تم إغلاقه من تقرير v0.1 السابق

## مغلق بالكامل أو بدرجة قوية

### Repair layer

تم إنشاء:

- `Operation`
- `RepairPlan`
- repair actions
- `RepairExecutor`
- dependency-aware execution
- audit linkage

### `PreparationResult`

موجود ويحتوي على:

- `raw_df`
- `clean_df`
- `before_scan`
- `after_scan`
- `audit`
- `plan`
- snapshots
- environment
- waivers
- status
- health before/after
- fixed/unresolved issues
- review queue
- `verified_df`

### Audit / rollback

موجود فعليًا.

### Completion state

مستخدم الآن، وليس مجرد Enum غير مستغل.

### Guided Mode

موجود فعليًا، ويعمل فوق نفس scan/repair engine.

### Decision replay

موجود:

```python
export_decisions()
```

ثم replay.

### Validation

موجود.

### Contracts

موجود.

### Privacy

موجود كطبقة أولية.

### Drift

موجود كطبقة أولية.

### Preprocessing

موجود فعليًا مع fit/transform discipline.

### Progress / Applicability

تحسن بصورة كبيرة:

```python
sp.scan(df, progress=True)
```

أو callback.

كما توجد:

- applicable
- skipped
- not applicable
- failed
- detector timing

### Strict detector failure mode

موجود:

```python
sp.scan(df, strict=True)
```

### Scan serialization

موجود:

- `to_dict`
- `to_json`

### Issue filtering

موجود:

```python
scan.find(...)
```

### `ScanResult.get()`

أصبح يعطي `KeyError` واضحًا بدل `StopIteration`.

---

# 5. النقائص الحرجة الجديدة — P0

## P0-1 — Target Encoding ليس Leave-One-Out كما تصفه الوثائق

هذه أهم مشكلة اكتشفتها في المراجعة.

الكود يقول:

```text
Leave-one-out target encoding with a smoothed prior.
```

والـAPI تقول إن implementation تستخدم leave-one-out.

لكن التنفيذ الحالي يبني mapping واحدة لكل category:

```python
mapping[level] =
    (sum(target_in_category) + prior * smoothing)
    / (n + smoothing)
```

ثم تستخدم mapping نفسها لكل صف داخل الفئة.

هذا ليس Leave-One-Out على مستوى الصف.

أي أن target الخاص بالصف يدخل في إحصائية الفئة التي يُشفّر بها الصف نفسه أثناء `fit_transform()`.

### لماذا هذا مهم؟

هذه **target leakage** حقيقية، خصوصًا عندما:

- الفئات قليلة التكرار
- high cardinality
- بعض الفئات تظهر مرة أو مرتين

### مثال تحقق

لبيانات:

```text
cat = a,b,c,d
y   = 0,0,1,1
```

تعلمت المكتبة:

```text
a -> 0.4545
b -> 0.4545
c -> 0.5455
d -> 0.5455
```

أي أن target لكل صف يؤثر مباشرة في encoding الخاص به.

### المطلوب

أحد ثلاثة حلول:

1. تنفيذ Leave-One-Out فعليًا في training transform.
2. الأفضل: Cross-Fitted Target Encoding.
3. أو تغيير الوصف بوضوح والاحتفاظ بـsmoothed mean encoding فقط، مع عدم وصفه LOO.

### التوصية

اعتماد:

```text
cross_fitted_target
```

كخيار افتراضي للـML workflows.

---

## P0-2 — `quantile_rank` يحول Missing Value إلى 1.0

عند تطبيق:

```python
Preprocessor().scale("x", method="quantile_rank")
```

على:

```text
1
2
NaN
4
```

النتيجة الحالية:

```text
0.0
0.333...
1.0    <- NaN
0.666...
```

أي أن Missing Value يتحول بصمت إلى أعلى quantile.

هذا خطأ semantic خطير.

كل scalers الأخرى في الاختبار حافظت على NaN.

### المطلوب

الـtransform يجب أن يحافظ على missing mask:

```python
mask = values.isna()
...
result[mask] = np.nan
```

وإضافة regression test مباشر.

---

## P0-3 — `DataContract.allow_extra_columns=False` غير مُطبق

الـDataContract الافتراضي يحتوي:

```python
allow_extra_columns = False
```

لكن:

```python
contract.validate(new_df)
```

لا يتحقق من وجود أعمدة زائدة.

اختبرت:

```text
contract inferred from:
a

new dataset:
a, b
```

والنتيجة:

```text
PASS
```

حتى مع:

```text
allow_extra_columns=False
```

### المطلوب

إضافة structural contract rule:

```text
unexpected_columns
```

وإذا كان:

```python
allow_extra_columns=False
```

يجب أن تفشل validation عند وجود أعمدة غير معرفة في العقد.

---

## P0-4 — Privacy Scanner يمكن أن يفوّت PII حقيقي بسبب `min_match_rate=0.5`

الـPrivacyScanner يعمل افتراضيًا بـ:

```python
min_match_rate=0.5
```

أي أن 50% من القيم غير المفقودة يجب أن تطابق pattern حتى يُصنف العمود.

اختبرت عمودًا اسمه:

```text
notes
```

وفيه 10 قيم، واحدة منها:

```text
a@b.com
```

والـscanner أعاد:

```text
no findings
```

هذا غير مناسب كـPrivacy Scanner.

وجود PII في 10% أو حتى 1% من free-text column ما يزال PII.

### المطلوب

فصل مفهومين:

```text
column classification
```

عن:

```text
cell-level PII findings
```

يمكن أن يكون:

```python
PrivacyScanner(
    column_classification_threshold=0.5,
    cell_detection_threshold=1
)
```

لكن لا ينبغي تجاهل PII فقط لأنه لا يمثل نصف العمود.

---

# 6. فجوات عالية الأولوية — P1

## P1-1 — Data Health Score ما يزال جزئيًا بالنسبة للخطة

الحالي يحتوي خمسة أبعاد أساسية:

- completeness
- validity
- consistency
- uniqueness
- semantic_quality

لكن الخطة المرجعية كانت تتطلب أيضًا:

- Integrity
- Statistical Preservation
- ML Readiness
- Econometrics Readiness
- Time-Series Readiness

إذن قول README:

```text
Data health score — Implemented
```

صحيح بالنسبة للـCore Score، لكنه ليس الـsuperset النهائي.

### المطلوب

فصل:

```text
Data Health
Analysis Readiness
Transformation Preservation
```

بدل خلطها كلها في رقم واحد.

---

## P1-2 — UnusualIssueDetector ما يزال غير موجود

يوجد enum:

```python
IssueCategory.UNUSUAL_PATTERN
```

لكن لا يوجد detector عام يستخدمه.

الخطة كانت تريد detection لـ:

- representation novelty
- schema novelty
- category explosion
- unusual parse failure clusters
- strange cross-column residuals
- unexpected structure

هذه نقطة مهمة جدًا للـAuto → Guided escalation.

---

## P1-3 — Reporting ما يزال Report Tables أكثر منه EDA System

الحالي يدعم:

- Markdown report
- JSON serialization

وهذا تقدم ممتاز.

لكن لا توجد EDA فعلية قبل/بعد:

- histograms
- KDE / ECDF
- boxplots
- missingness plots
- correlations
- mixed associations
- categorical distributions
- target-aware EDA
- pre/post statistical plots
- interactive charts

ولا توجد:

- HTML
- PDF
- PNG
- SVG
- notebook-rich reports

إذن Reporting **Partial** وليس مكتمل وفق الخطة الكاملة.

---

## P1-4 — لا توجد Visualization Layer

حتى الآن لا يوجد:

- Matplotlib engine
- Seaborn-style engine
- Plotly engine
- linked views
- animation
- large-data visualization planner

هذه طبقة مستقلة عن Studio ويجب بناؤها قبل/معه.

---

## P1-5 — لا توجد Entity Resolution / Record Linkage

ما يزال غير موجود:

- near-duplicate rows
- fuzzy entity matching
- blocking
- scoring
- merge proposals
- cross-table linkage
- human review of candidate pairs

وجود geographic entity graph ليس Entity Resolution Engine.

---

## P1-6 — Multi-backend ما يزال غير منفذ

الـpackage core ما يزال:

```text
pandas + numpy
```

لا توجد backend abstraction فعلية لـ:

- Polars
- Arrow
- DuckDB
- Ibis
- Dask
- Spark

والـextras:

```toml
polars = []
duckdb = []
spark = []
```

هي placeholders فقط حاليًا.

---

## P1-7 — Time-Series diagnostics غير موجودة

يوجد:

```text
goal="time_series"
```

في preprocessing advisor.

لكن هذا ليس Time-Series Preparation Engine.

ما يزال ينقص:

- frequency inference
- missing periods
- duplicate timestamps
- irregular intervals
- timezone consistency
- temporal gaps
- chronological validation
- resampling
- rolling diagnostics
- forecasting-safe transformations

---

## P1-8 — Panel diagnostics غير موجودة

ينقص:

- entity-time keys
- duplicate entity-time
- balance/unbalance
- gaps per entity
- within/between variation
- constant-within-entity columns
- insufficient within variation
- entity chronology

---

## P1-9 — Econometrics mode ما يزال Advisor-level فقط

ميزة:

```python
goal="econometrics"
```

تمنع scaling/encoding recommendations.

هذا جيد، لكنه لا يساوي Econometrics Preparation Layer كاملة.

ينقص:

- inference preservation
- panel awareness
- time-series awareness
- transformation impact on estimands
- econometric readiness report
- research-safe imputation policies
- coefficient interpretation warnings

---

# 7. Preprocessing — ما تم وما يزال ناقصًا

## Imputation

الموجود:

- mean
- median
- mode
- constant
- group_median
- forward_fill
- backward_fill
- interpolate

ممتاز كـCore.

لكن ينقص من الخطة:

- KNN
- Iterative
- MICE
- Multiple Imputation
- miceforest-style
- matrix completion
- uncertainty propagation
- panel-aware imputation
- treatment comparison sandbox

---

## Encoding

الموجود:

- one_hot
- ordinal
- frequency
- count
- target

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
- dirty-string similarity encoding

ومشكلة الـtarget encoding الحالية يجب إصلاحها قبل توسيع encoders.

---

## Scaling

الموجود:

- standard
- minmax
- robust
- maxabs
- log1p
- Yeo-Johnson
- quantile rank

جيد جدًا كبداية.

ينقص:

- Normalizer
- Box-Cox
- explicit clipping
- winsorization
- binning/discretization

---

## Feature Engineering

غير موجود كطبقة حقيقية بعد.

ينقص:

- datetime features
- interactions
- polynomial features
- lags
- rolling
- expanding
- relational features
- feature lineage
- redundancy checks

---

# 8. Privacy — جيدة كبداية، لكنها ليست الطبقة النهائية

نقاط القوة:

- Luhn validation للبطاقات
- E.164 digit limit للهواتف
- name hints
- direct/quasi identifiers
- re-identification risk
- masking
- redaction
- hashing
- pseudonymisation
- generalisation
- explicit false-negative caveat

لكن ينقص:

- cell-level mixed PII detection
- PII داخل free text
- NER
- locale-specific IDs
- IBAN checksum validation
- stronger phone parsing عبر country context
- secrets / API keys
- addresses
- names داخل النص
- date-of-birth semantics
- structured privacy policies
- safe report sampling / redaction

---

# 9. Drift — طبقة حقيقية ولكنها ليست الـsuperset

الموجود:

- PSI
- KS statistic
- Jensen-Shannon
- mean shift
- categorical drift
- unseen/lost categories
- missingness drift
- schema added/removed
- contributor attribution
- cleaning drift

ينقص من الخطة:

- Wasserstein
- Chi-square
- Cramér-von Mises
- MMD
- classifier-based drift
- online drift
- drift windows
- statistical significance / uncertainty
- reference version management
- drift monitoring history

---

# 10. Contracts — نقاط جيدة وفجوات

الموجود:

- infer
- nullable
- unique
- numeric min/max
- allowed categories
- primary key proposal
- validation compilation
- diff
- breaking / semantic breaking
- JSON
- YAML output

ينقص أو يحتاج إصلاح:

1. `allow_extra_columns` enforcement — **bug**
2. YAML parser / `from_yaml`
3. relationships / foreign keys
4. units inference
5. semantic types
6. descriptions / owners
7. contract provenance
8. schema migration suggestions
9. explicit forward/backward compatibility policy docs
10. Open Data Contract / Frictionless interoperability

---

# 11. Interactive Studio — ما يزال أكبر فجوة UX

غير موجود بعد، وهذا يتوافق مع AD-010.

لكن لبنائه ينبغي أولًا تثبيت:

```text
GuidedSession
PreparationResult
Issue
TreatmentCandidate
Audit
Report models
```

وهذا أصبح موجودًا الآن، لذلك الوقت أصبح مناسبًا لبدء الـStudio بعد إصلاح P0s.

المكونات المقترحة:

- Smart Data Grid
- Issue Inbox
- Question/Decision cards
- Column Inspector
- Treatment Sandbox
- Before/After preview
- Missing Lab
- Outlier Lab
- Entity Resolution Lab
- Text Integrity Lab
- Date Intelligence Lab
- Pipeline Canvas
- Audit Timeline
- Reports Center

---

# 12. Documentation ما تزال أقل من الخطة النهائية

README ممتاز بالنسبة لما هو منفذ، وهي نقطة قوة واضحة.

لكن لا يوجد:

```text
docs/
mkdocs.yml
SYNTAX_COOKBOOK.md
FUNCTION_CATALOG.md
examples/
notebooks/
developer guide
plugin author guide
```

الخطة كانت تشترط أن يستطيع المستخدم تعلم كل Function بسهولة من Documentation كاملة.

README الحالي قوي، لكنه ليس بديلًا عن Documentation Site.

---

# 13. Packaging — جيد ولكن يوجد تناقض يجب حسمه

`pyproject.toml` يقول:

```toml
license = "Apache-2.0"
```

والحزمة تحتوي:

```text
LICENSE
NOTICE
```

إذن عمليًا الترخيص تم اختياره.

لكن `_ARCHITECTURE_DECISIONS.md` يقول:

```text
license still open
{{LICENSE}} = OPEN
```

هذا تناقض documentation/metadata.

### المطلوب

إما:

- تثبيت Apache-2.0 رسميًا وتحديث AD-011 إلى Implemented

أو:

- إزالة Apache metadata مؤقتًا

لا يفضل إبقاء الاثنين مختلفين.

---

# 14. Packaging — Stress tests داخل sdist بدون fixture

الـsdist يوزع:

```text
tests/test_baseline_detection.py
tests/test_false_positives.py
```

لكن لا يوزع:

```text
data_project.xlsx
```

فتصبح 51 tests skipped دائمًا داخل sdist.

هذا ليس خطأ تشغيل للحزمة، لكنه قرار packaging غير نظيف.

### الخيارات

#### خيار A

لا توزع stress tests في sdist.

#### خيار B

حوّل stress fixture إلى synthetic/generated fixture يمكن إعادة إنشائها.

#### خيار C

وزع fixture إذا كان الترخيص والحجم مقبولين.

أفضل خيار طويل المدى:

```text
synthetic deterministic stress fixture
```

مع إبقاء real workbook في development repository فقط.

---

# 15. CI/CD — تحسن كبير

موجود الآن:

- Windows
- Linux
- macOS
- Python 3.10/3.11/3.12
- pytest
- ruff check
- ruff format
- mypy
- package build
- twine check
- artifact upload

هذا ممتاز.

ما يزال ينقص:

- coverage gate
- install-and-smoke-test built wheel
- docs build
- security/dependency scan
- benchmark regression job
- release / trusted publishing workflow
- Python 3.13 عند إعلان الدعم

---

# 16. Reproducibility — قوية ولكن يمكن تحسين fingerprint

`DatasetFingerprint` يستخدم حاليًا تقريبًا:

```python
hash_pandas_object(...).sum()
```

ثم يهش الـsum.

هذا سريع، لكنه أضعف من hashing كامل byte sequence.

جمع hashes:

- يقلل المعلومات
- أكثر عرضة للتصادم
- لا يمثل ترتيب الصفوف بأقوى شكل ممكن

### الأفضل

استخدام hash متسلسل لكل row hash bytes:

```text
SHA256(
    schema
    + ordered row hashes
    + index
    + column order
)
```

أو streaming digest.

خصوصًا إذا كان fingerprint سيستخدم كدليل Audit/Reproducibility.

---

# 17. Snapshot strategy لن تتوسع للبيانات الكبيرة

`DatasetSnapshot` يحمل:

```python
frame.copy(deep=True)
```

لكل snapshot.

هذا ممتاز لضمان rollback في datasets الصغيرة والمتوسطة.

لكنه قد يصبح مكلفًا جدًا مع:

- ملايين الصفوف
- عشرات العمليات

قبل multi-backend / large data يجب إضافة:

- copy-on-write strategy
- delta snapshots
- checkpoint policy
- disk-backed snapshots
- snapshot limit
- memory estimate

---

# 18. Audit IDs ليست deterministic عبر process lifetime

`AuditRecord.next_id()` يستخدم global counter:

```text
OP-00001
OP-00002
...
```

هذا جيد للقراءة، لكنه يعني أن IDs تعتمد على ما تم تنفيذه سابقًا في process نفسه.

إذا كانت الـIDs ستستخدم في reproducibility comparisons، الأفضل فصل:

```text
display sequence id
```

عن:

```text
stable operation identity/hash
```

---

# 19. Root Cause Analysis ما يزال جزئيًا جدًا

توجد بعض `root_cause_hint` داخل detectors، وهذا جيد.

لكن لا يوجد engine يجمع findings ويقول مثلًا:

```text
82% of invalid dates originate from source=branch_03
```

ينقص:

- issue clustering
- source attribution
- common-cause ranking
- upstream change graph
- root-cause report

---

# 20. Rule Learning / Knowledge Base غير موجود

ما يزال ينقص:

- Project Rules
- Organization Rules
- Domain Rules
- learned decisions
- promotion policy
- conflict handling
- rule versioning
- provenance

Decision replay موجود، لكنه ليس Rule Learning.

---

# 21. Detector Plugin Architecture ما تزال داخلية

يوجد:

```python
DetectorRegistry
register
```

وهذه بداية جيدة.

لكن لا توجد ecosystem plugin architecture حقيقية:

- entry points
- external package discovery
- compatibility metadata
- detector version
- backend support
- dependencies
- cost
- thread-safety
- semantic capabilities

---

# 22. Semantic Cleaning ما تزال محدودة

الـ14 detectors ممتازة للـfixture، لكنها لا تغطي بعد:

- decimal comma
- currency symbols
- percentages-as-text
- units
- unit conversion
- URLs
- phone normalization
- email normalization
- postal addresses
- composite fields
- nested data
- locale-aware parsing
- full mojibake fixing
- control characters أوسع
- multilingual category reconciliation

---

# 23. Outlier / anomaly system ما يزال محدودًا

الموجود أساسًا:

- range violations
- sentinel candidates
- accounting plausibility

ينقص:

- IQR
- MAD
- robust z-score
- multivariate outliers
- Isolation Forest
- LOF
- contextual anomalies
- collective anomalies
- time-series anomalies
- PyOD adapters
- anomaly treatment sandbox

---

# 24. Benchmark Suite ما يزال غير موجود كمنتج

الـstress fixture هو:

```text
acceptance baseline
```

وليس:

```text
SmartPrepBench
```

ما يزال مطلوبًا قياس:

- precision
- recall
- false positives
- false negatives
- repair accuracy
- runtime
- peak memory
- information loss
- distribution preservation
- user effort

ومقارنة مع أدوات منافسة.

---

# 25. لا يوجد Project object بعد

الخطة الكبيرة اقترحت workflow مثل:

```python
project = sp.Project(df)

project.scan()
project.validate()
project.report()
project.history()
...
```

الحالي يعتمد APIs منفصلة ونتائج dataclasses.

هذا ليس خطأ، بل قرار تصميم يجب حسمه قبل v1.

إذا كان Studio سيحتاج state طويلة المدى، وجود:

```python
Project
```

قد يكون مفيدًا جدًا كـsession/domain object.

---

# 26. واجهة IO / Loading غير موجودة

الخطة اقترحت:

```python
sp.read(...)
```

الحالي يتوقع DataFrame جاهزة.

ينقص مستقبلًا:

- CSV
- Excel
- Parquet
- Arrow
- SQL
- DuckDB
- Polars
- encoding detection
- delimiter inference
- sheet selection
- import diagnostics

يمكن تأجيل هذا إذا كان المبدأ:

```text
SmartPrep receives DataFrames, not files
```

لكن يجب حسمه كقرار معماري.

---

# 27. أهم ما أوصي به قبل Studio

لا أبدأ الـfrontend مباشرة قبل هذه الإصلاحات الأربعة:

## 1. إصلاح Target Encoding

Cross-fitting أو LOO حقيقي.

## 2. إصلاح quantile_rank missing semantics

NaN يبقى NaN.

## 3. فرض `allow_extra_columns`

حتى DataContract تعني ما تقول.

## 4. إصلاح Privacy low-rate PII detection

cell-level scan منفصل عن column classification.

بعدها يمكن بدء Studio بثقة أكبر.

---

# 28. ترتيب التنفيذ المقترح من الآن

## Phase 0 — Hotfix v0.3.0.dev1

- target encoding leakage correctness
- quantile_rank NaN preservation
- allow_extra_columns enforcement
- privacy mixed-cell detection
- tests لكل bug
- AD-011 license consistency

## Phase 1 — Reporting / EDA

- profile statistics
- pre/post EDA
- Matplotlib static charts
- Plotly interactive charts
- HTML report
- PDF report
- comparison dashboard

## Phase 2 — Studio

- smart grid
- issue inbox
- guided question cards
- preview
- treatment comparison
- audit timeline
- reports view

## Phase 3 — Entity & semantic cleaning

- RapidFuzz-style category reconciliation
- near duplicates
- record linkage
- units/currency/percentage parsing
- phone/email/address plugins

## Phase 4 — Time Series / Panel

- timestamp/frequency diagnostics
- gaps
- temporal leakage
- entity-time integrity
- panel readiness

## Phase 5 — Multi-backend

- backend protocol
- Narwhals/Ibis evaluation
- Polars
- Arrow
- DuckDB
- no-silent-fallback

## Phase 6 — Observability / benchmark

- advanced drift metrics
- monitoring history
- SmartPrepBench
- performance baselines

---

# 29. التقييم الحالي

## Architecture

**قوية جدًا بالنسبة لنسخة dev مبكرة.**

أفضل القرارات:

- detection confidence != repair confidence
- safe by default
- explicit auto/guided modes
- no silent mutation
- refusal is audited
- guided mode reuses the same engine
- decision replay
- `verified_df` semantics

## Testing

الـsynthetic/core suite جيدة جدًا:

```text
255 passed
```

والstress tests مصممة جيدًا عندما يتوفر workbook.

لكن لا تزال تحتاج property/fuzz/performance/backend tests لاحقًا.

## Documentation

README ممتاز وصادق بدرجة كبيرة.

لكن يوجد تناقض license في AD-011، ولا توجد Documentation Site كاملة بعد.

## Feature completeness

Core architecture:
**قريب من الاستقرار.**

Full SmartPrep plan:
**ما زال بعيدًا عن الاكتمال، وهذا طبيعي جدًا في v0.3.dev.**

---

# 30. الحكم النهائي

لا أنصح بإعادة كتابة SmartPrep.

ولا أنصح بالقفز الآن إلى إضافة عشرات detectors جديدة.

الأولوية القصوى هي:

```text
Correctness of existing semantics
→ richer EDA/reporting
→ Studio
→ semantic/entity layers
→ time-series/panel
→ multi-backend
```

أهم شيء الآن هو أن الـCore أصبح موجودًا بما يكفي ليكون أساسًا حقيقيًا للمنتج.

لكن قبل بناء واجهة رسومية فوقه، يجب إصلاح الأربع مشاكل P0 التي كشفتها هذه المراجعة، لأنها تقع في:

- leakage safety
- missing-value semantics
- contract enforcement
- privacy false negatives

وهذه بالضبط من المناطق التي تريد SmartPrep أن تتميز فيها عن الأدوات التقليدية.
