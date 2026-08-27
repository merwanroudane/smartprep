# SmartPrep v0.1.0.dev0 — مراجعة شاملة للنقائص والفجوات

**الحزمة المراجعة:** `smartprep-0.1.0.dev0.tar.gz`  
**تاريخ المراجعة:** 2026-08-26  
**المستودع:** https://github.com/merwanroudane/smartprep  
**المؤلف:** Dr Merwan Roudane  
**البريد:** merwanroudane920@gmail.com

---

## 1. الخلاصة التنفيذية

النسخة الحالية **ليست مكتبة SmartPrep الكاملة بعد**؛ هي نواة تشخيصية جيدة ومنضبطة تمثل مرحلة مبكرة من الخطة. أفضل ما فيها حاليًا هو الفصل الصحيح بين `detection_confidence` و`repair_confidence`، سياسة الامتناع عن الإصلاح عند الغموض، نموذج `Issue`/`TreatmentCandidate`، سجل القرارات المعمارية، واختبارات الضغط الواقعية.

لكن الجزء الأكبر من الرؤية الأصلية ما زال غير منفذ: **الإصلاح الفعلي، Auto Mode، Guided Mode، التقارير، EDA قبل/بعد، الواجهة التفاعلية، preprocessing، validation/contracts، privacy، drift، lineage، multi-backend، time-series/panel/econometrics/ML، والتوثيق الموسوعي الكامل للـAPI.**

### الحكم الحالي

- **جودة النواة الحالية:** جيدة جدًا بالنسبة لـ `dev0`.
- **الالتزام بفلسفة Safe-by-default:** قوي.
- **جاهزية النشر كنسخة تشخيص تجريبية:** قريبة، بعد إصلاح بعض نقاط التغليف والاختبارات والتوثيق.
- **جاهزية الادعاء بأنها منصة Cleaning/Preprocessing شاملة:** لا؛ ما زال ذلك هدف roadmap.
- **أكبر فجوة وظيفية:** لا توجد حتى الآن أي طبقة Repair/Preparation حقيقية.

---

## 2. ما تم التحقق منه فعليًا

تم فك الحزمة وفحص:

- `pyproject.toml`
- `README.md`
- `REFERENCES.md`
- `_ARCHITECTURE_DECISIONS.md`
- `_STRESS_TEST_BASELINE.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CITATION.cff`
- كامل `src/smartprep/`
- كامل `tests/`

### نتيجة الاختبارات

عند تشغيل الحزمة كما وصلت، بدون ملف stress fixture:

```text
30 passed, 51 skipped
```

سبب الـ51 skipped أن `data_project.xlsx` غير موجود داخل الـsdist، رغم أن معظم اختبارات القبول تعتمد عليه.

بعد وضع ملف الاختبار الحقيقي الموافق للـbaseline داخل جذر المشروع:

```text
81 passed
```

وهذا يؤكد أن الـdetector baseline الحالي يعمل على الـfixture المستهدف.

### ملاحظة أدوات الجودة

لم تكن `ruff` و`mypy` و`build` مثبتة في بيئة المراجعة، لذلك لم يتم اعتماد نتيجة lint/type/build نهائية. هذه ليست بالضرورة مشكلة في الحزمة، لكنها تعني أن CI يجب أن يكون المرجع الحاسم لهذه الفحوص.

---

# 3. النقائص الحرجة — P0

هذه النقاط يجب حسمها قبل اعتبار النسخة أساسًا مستقرًا للمرحلة التالية.

## P0-1 — اختبارات القبول الرئيسية لا تعمل من الـsdist كما هو موزع

`tests/conftest.py` يبحث عن:

```text
data_project.xlsx
```

لكن `pyproject.toml` يستبعد الملف عمدًا من الـsdist. النتيجة أن **51 من 81 اختبارًا يتم Skip لها** عند اختبار الحزمة الموزعة.

### لماذا هذه مشكلة؟

README يقول إن هناك 81 اختبارًا وإن baseline الحقيقي عقد regression، لكن مستخدم/مطور يبني من الـsdist لن يشغل هذا العقد فعليًا.

### المطلوب

اختر واحدًا من الحلول:

1. إضافة fixture مصغرة/مجهولة الهوية داخل `tests/data/` يمكن توزيعها قانونيًا.
2. توليد fixture اصطناعية deterministic تعيد نفس edge cases.
3. فصل اختبارات stress الحقيقية بعلامة `@pytest.mark.stress` ووضعها في CI خاص يحمّل fixture من مصدر آمن.
4. الأفضل: **اختبارات unit/acceptance صغيرة موزعة + fixture الحقيقية في CI private/controlled**.

ويجب ألا يظهر `81 tests` للمستخدم إذا كانت 51 منها غير قابلة للتنفيذ في artifact المنشور دون توضيح.

---

## P0-2 — لا توجد طبقة Repair رغم أن المشروع هو Data Preparation

المطبق حاليًا:

```python
sp.scan(df)
```

غير المطبق:

```python
sp.auto_prepare(df)
sp.guided_prepare(df)
sp.clean(df)
sp.studio(df)
```

وهذا مذكور بصدق في README، لكنه أكبر نقص بالنسبة للخطة الأصلية.

### المطلوب للمرحلة التالية

بناء Core repair architecture قبل أي واجهة:

- `Operation`
- `RepairAction`
- `RepairPlan`
- `PreparationResult`
- snapshot/diff
- audit record
- undo/rollback
- repair executor
- post-repair validation
- idempotence checks

---

## P0-3 — `auto_prepare()` يجب ألا يكون مجرد loop على `auto_fixable`

الفلسفة الحالية جيدة، لكن التنفيذ المستقبلي يحتاج منع خطأ معماري شائع: تطبيق الإصلاحات واحدًا تلو الآخر دون إعادة تقييم dependency graph.

يجب أن توجد مراحل:

```text
scan
→ build issue dependency graph
→ choose safe operations
→ preview
→ execute transaction
→ rescan affected scopes
→ validate
→ measure impact
→ commit/rollback
```

مثال: تحويل `unit_price` من string إلى numeric قد يغيّر نتائج range/outlier/formula detectors؛ لذلك يجب إعادة الفحص بعد إصلاح النوع.

---

## P0-4 — لا يوجد `PreparationResult`

الخطة تتطلب كائنًا غنيًا مثل:

```python
result.raw_df
result.clean_df
result.verified_df
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

الحالي هو `ScanResult` فقط.

يجب تصميم `PreparationResult` قبل كتابة Auto/Guided حتى لا تتشتت API.

---

## P0-5 — لا يوجد Audit/Lineage فعلي

النموذج الحالي يحتفظ بـEvidence، لكنه لا يسجل عمليات تغيير لأن التغيير غير موجود أصلًا.

المطلوب لكل عملية مستقبلية:

- operation id
- issue id(s)
- timestamp
- source rule
- before value/hash
- after value/hash
- affected rows/columns
- parameters
- confidence
- decision source: auto/user/domain rule
- reason
- reversibility
- parent operation
- dataset version

بدون هذا لن يتحقق وعد "auditable" بعد بدء الإصلاح.

---

# 4. فجوات عالية الأولوية — P1

## P1-1 — Data Health Score غير منفذ

الخطة تفرق بين:

```text
Scan Coverage
```

و:

```text
Data Health Score
```

الحالي ينفذ coverage فقط.

المطلوب محرك Health Score متعدد الأبعاد:

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

مع أوزان قابلة للتخصيص، وشرح لماذا تغيرت الدرجة.

---

## P1-2 — Progress 0→100% غير منفذ كواجهة تقدم

`coverage` يحسب النسبة بعد التنفيذ، لكن لا توجد:

- progress callback
- event stream
- tqdm integration
- notebook progress
- Studio progress
- detector timing

المطلوب API مثل:

```python
sp.scan(df, progress=True)
```

أو event hooks قابلة للربط بأي frontend.

---

## P1-3 — مفهوم Applicable / Skipped / Failed يحتاج اكتمالًا

`CheckOutcome` يدعم `completed/skipped/failed`، لكن registry الحالي يشغل كل detector ويعتبر عدم وجود findings = completed. لا توجد طبقة واضحة تسأل detector مسبقًا: هل هو applicable؟

المطلوب:

```python
detector.applicability(frame, context)
```

تعيد مثلًا:

```text
APPLICABLE
NOT_APPLICABLE
SKIPPED_MISSING_CONTEXT
SKIPPED_MISSING_DEPENDENCY
```

وهذا ضروري لكي يكون "100% coverage" ذا معنى علمي.

---

## P1-4 — فشل Detector يتم ابتلاعه بالكامل

في `scan()`:

```python
except Exception as exc:
    ... status="failed"
    continue
```

هذا جيد للـresilience، لكنه يحتاج policy واضحة لأن المستخدم قد يحصل على coverage ناقصة دون ملاحظة قوية.

المطلوب:

- `strict=False/True`
- warning واضح
- failed detector count في `summary()`
- completion state يتأثر بالفشل
- optional raise في research/regulated profile
- structured exception provenance

---

## P1-5 — لا يوجد UnusualIssueDetector فعلي

`IssueCategory.UNUSUAL_PATTERN` موجود في enum، لكن لا يوجد detector عام للأنماط غير المألوفة كما طلبت الخطة.

المطلوب لاحقًا محرك ensemble يجمع:

- schema novelty
- frequency shifts
- pattern novelty
- cross-field residual anomalies
- rare representations
- unexpected category explosion
- unexpected parsing failure clusters

ويصعّد إلى Guided بدل الإصلاح.

---

## P1-6 — لا توجد EDA حقيقية قبل/بعد

الحالي detectors، وليس EDA system.

ينقص:

- descriptive statistics
- distributions
- associations/correlations
- mixed-type associations
- target-aware EDA
- missingness visualization
- cardinality
- skew/kurtosis
- ECDF/KDE/histograms
- categorical plots
- pair relationships
- time plots
- panel diagnostics
- pre/post comparison

---

## P1-7 — لا توجد منظومة Reporting

الخطة تتطلب:

- Interactive HTML
- PDF
- Markdown
- JSON
- YAML
- Notebook embedded
- PNG/SVG

وملفات:

- Pre-Cleaning Report
- Post-Cleaning Report
- Before/After Comparison
- Executive
- Technical
- Audit
- Research
- ML readiness
- Econometrics readiness

لا يوجد منها شيء حاليًا.

---

## P1-8 — Guided Mode غير موجود

هذه ميزة جوهرية في هوية SmartPrep.

ينقص:

- review queue
- issue ordering/dependencies
- treatment alternatives
- recommendation score
- compare methods
- preview
- user decision persistence
- accept/waive/skip/custom rule
- resume session
- only unresolved mode

---

## P1-9 — لا توجد Repair Preview / Transaction / Undo

أي عملية خطرة مستقبلًا يجب أن تمر عبر:

```text
Preview → Apply → Validate → Commit
```

مع:

```python
project.undo()
project.rollback(version)
project.diff(v1, v2)
```

لا توجد هذه البنية حاليًا.

---

# 5. فجوات Cleaning وSemantic Cleaning

الـ14 detectors الحالية تغطي fixture جيدًا، لكنها ليست coverage شاملة للمشاكل التي وضعتها الخطة.

## غير منفذ أو ناقص بوضوح

- hidden missing tokens: `N/A`, `?`, `-`, `unknown`, custom sentinels النصية
- whitespace-only cells كـmissing configurable
- boolean variants
- percentages stored as strings
- currencies with symbols
- decimal comma / locale numbers
- units داخل القيم
- unit conversion
- URL validation/cleaning
- email validation/cleaning
- phone normalization
- postal address parsing
- IDs/checksums المتخصصة
- free-text normalization
- mojibake via ftfy-style logic
- control/invisible characters بشكل أوسع
- transliteration policies
- near duplicate records beyond duplicate identifier
- probabilistic entity resolution
- record linkage across tables
- composite-column splitting
- header/footer contamination
- shifted rows
- duplicate column names
- empty rows/columns
- schema evolution
- nested/semi-structured data

---

# 6. فجوات Missing Data

الحالي يشخّص missingness semantic في حالات محددة، وهذا ممتاز، لكن لا توجد طبقة treatment.

ينقص:

- Simple imputation
- group-wise imputation
- KNN
- IterativeImputer
- MICE / Multiple Imputation
- tree-based imputation
- matrix completion
- interpolation
- forward/backward fill
- time-aware imputation
- panel-aware imputation
- missing indicators
- imputation comparison sandbox
- statistical distortion evaluation
- uncertainty from multiple imputation
- missingness mechanism diagnostics الأوسع (MCAR/MAR/MNAR بحذر)

---

# 7. فجوات Outlier / Anomaly Detection

الحالي يملك range + sentinel، لكنه لا يملك منظومة outlier كاملة.

ينقص:

- IQR
- MAD/robust z-score
- classical z-score
- quantile methods
- Isolation Forest
- LOF
- One-Class methods
- PyOD integration/adapter
- multivariate anomaly detection
- contextual anomalies
- collective anomalies
- time-series anomalies
- treatment advisor
- explicit rare-valid vs erroneous distinction beyond sentinel examples

والأهم: **لا يجب إضافة `remove_outliers()` كتصرف افتراضي.**

---

# 8. فجوات Preprocessing

لا توجد حاليًا طبقة preprocessing فعلية.

## Encoding

ينقص:

- OneHot
- Ordinal
- Target
- CatBoost
- WOE
- Hashing
- Binary/BaseN
- Frequency/Count
- Leave-One-Out
- GLMM
- M-estimator
- MinHash / dirty-string encoders
- Encoding Advisor
- leakage-safe cross-fitting

## Scaling / Transformations

ينقص:

- StandardScaler
- MinMaxScaler
- RobustScaler
- MaxAbsScaler
- Normalizer
- log/log1p
- Box-Cox
- Yeo-Johnson
- quantile transform
- winsorization/clipping
- binning/discretization

## Feature Engineering

ينقص:

- datetime features
- lags
- rolling/expanding
- interactions
- polynomial
- relational feature generation
- feature lineage
- feature leakage guard
- redundancy checks

---

# 9. Validation / Contracts

Enums وExceptions تشير إلى هذه الطبقات، لكن التنفيذ غير موجود.

ينقص:

- schema objects
- column constraints
- lazy validation
- validation plan
- `valid, invalid = result.split()`
- user rules
- cross-column constraints
- data contract serialization
- YAML/JSON contract
- contract versioning
- schema evolution classification
- backward/forward compatibility
- breaking/semantic breaking changes
- Pandera/GX/Pointblank-style interoperability

---

# 10. Privacy / PII

`SmartPrepPrivacyError` موجود، لكن لا يوجد Privacy Engine.

ينقص:

- PII detection
- direct identifiers
- quasi-identifiers
- free-text PII
- masking
- redaction
- hashing
- tokenization
- pseudonymization
- generalization
- privacy-aware report sampling
- prevention of sensitive values in logs/errors
- privacy tests

هذه النقطة مهمة لأن `SECURITY.md` يعد بعدم تسريب sensitive values مستقبلًا؛ يجب أن تتحول إلى اختبارات قبل إطلاق reporting.

---

# 11. Drift / Observability / Streaming

غير منفذ بالكامل:

- reference dataset comparison
- PSI
- KS
- Chi-square
- JS divergence
- Wasserstein
- MMD
- classifier drift
- category drift
- missingness drift
- schema drift
- cleaning drift
- online drift
- incremental profiles
- streaming preprocessing
- `learn_one/update(batch)` style APIs

---

# 12. Multi-backend

الحزمة تعتمد مباشرة على:

```text
pandas
numpy
```

ولا توجد abstraction فعلية لـ:

- Polars
- Arrow
- DuckDB
- Ibis
- Narwhals
- Dask
- Spark
- SQL

ينقص:

- Semantic Operation IR
- backend protocol
- capability matrix
- backend planner
- no-silent-fallback enforcement
- backend parity tests
- schema round-trip tests

---

# 13. Time Series / Panel / Econometrics / ML

غير موجودة بعد.

## Time Series

- frequency inference
- gaps
- duplicate timestamps
- irregular intervals
- timezone handling
- resampling
- temporal leakage guard
- time-aware transformations

## Panel

- entity-time key
- duplicate entity-time
- unbalanced panel
- gaps per entity
- within variation
- constant-within-entity variables

## Econometrics

- research-safe defaults
- no blind scaling/encoding
- inferential preservation metrics
- panel/time-series context
- econometric readiness report

## ML

- sklearn Transformer API
- fit/transform separation
- ColumnTransformer integration
- target leakage
- train/test leakage
- imbalance handling
- ML readiness

---

# 14. Interactive Studio / UX

غير موجود بالكامل.

ينقص:

- Smart Data Grid
- Issue Inbox
- Column Inspector
- Missing Data Lab
- Outlier Lab
- Entity Resolution Workbench
- Date Intelligence Workbench
- Text Integrity Workbench
- Semantic Field Workbench
- Encoding/Scaling labs
- Treatment Sandbox
- Pipeline Canvas
- Audit Timeline
- linked selections
- before/after toggle
- code generation per click
- undo/redo
- accessibility
- i18n Arabic/French/English

يجب تأجيل الـfrontend حتى يستقر Core، كما تقرر في AD-010.

---

# 15. Visualization

لا يوجد Visualization layer.

ينقص:

- Matplotlib static engine
- Seaborn-style statistical plots
- Plotly interactive engine
- linked brushing
- hover/zoom/pan
- animation عند وجود معنى
- large-data sampling/aggregation/rasterization
- explicit sample disclosure
- export PNG/SVG

---

# 16. Documentation — نقاط القوة والنقائص

## نقاط قوة

README الحالي جيد جدًا في شرح **الفلسفة الحالية** ولا يدّعي أن features غير المنفذة موجودة. هذه نقطة ممتازة.

`REFERENCES.md` قوي كبداية ويربط prior art بما يضيفه SmartPrep.

`_ARCHITECTURE_DECISIONS.md` من أفضل أجزاء المشروع لأنه يحسم التعارضات المهمة.

## النقائص

الخطة النهائية طلبت Documentation موسوعية، بينما الحزمة لا تحتوي أصلًا على مجلد `docs/`.

ينقص:

- MkDocs/Sphinx site
- `mkdocs.yml`
- Getting Started
- full User Guide
- `SYNTAX_COOKBOOK.md`
- `FUNCTION_CATALOG.md`
- API reference مولد من docstrings
- issue-code reference
- configuration reference
- exception reference
- examples directory
- notebooks
- developer guide
- plugin author guide
- backend author guide
- runnable documentation tests
- search

### README نفسه

README ممتاز لـv0.1 diagnosis، لكنه **ليس بعد README الموسوعي المطلوب للمكتبة النهائية** لأنه لا يمكنه توثيق functions غير الموجودة. يجب توسيعه تدريجيًا مع كل API جديدة، لا كتابة أمثلة وهمية مسبقًا.

---

# 17. API Documentation gaps

Public API الحالية صغيرة ومفهومة، لكن:

- `ScanResult.get()` يرمي `StopIteration` إذا لم يجد ID؛ الأفضل exception واضحة أو `None` variant.
- لا يوجد filtering by severity/confidence/column بصورة غنية.
- لا يوجد serialization لـIssue/ScanResult إلى dict/JSON.
- لا يوجد stable issue-code registry موثق.
- لا يوجد schema/version field في serialized results.
- لا يوجد API lifecycle status (`experimental/stable/deprecated`).
- لا يوجد deprecation framework.

---

# 18. Detector Plugin Architecture — موجودة جزئيًا فقط

`DetectorRegistry` بداية جيدة، لكنها داخلية/بسيطة.

ينقص:

- public decorator موثق للمستخدم
- entry points (`importlib.metadata.entry_points`) لاكتشاف plugins الخارجية
- detector metadata
- required columns/context
- applicability method
- version compatibility
- detector dependencies
- ordering/dependency graph
- priority
- cost estimate
- backend support metadata
- thread/process safety metadata

---

# 19. Reference Data / Geography

Entity graph فكرة جيدة، لكن المرجع الحالي embedded داخل package وسيصبح محدودًا عالميًا.

المطلوب:

- versioned domain/reference packs
- ISO source provenance
- update mechanism
- locale/language packs
- aliases/transliterations أوسع
- ambiguity handling (`Paris` etc.)
- country subdivisions
- offline/online policy
- user-supplied reference packs
- tests against unknown entities

ولا ينبغي أن تتحول مكتبة SmartPrep نفسها إلى مستودع ضخم لكل مدن العالم؛ الأفضل plugin/data-pack architecture.

---

# 20. Security gaps

`SECURITY.md` جيد من ناحية المبادئ، لكن التنفيذ الحالي لا يختبر معظمها.

قبل إضافة IO/HTML/reporting يجب إضافة tests لـ:

- HTML/script escaping
- formula injection في CSV/Excel exports
- path traversal
- zip bombs / oversized compressed inputs
- unsafe pickle avoidance
- malicious XML where relevant
- sensitive sample redaction
- log redaction
- exception redaction
- dependency vulnerability scanning
- supply-chain checks

ملاحظة: استبعاد DoS من `SECURITY.md` مفهوم، لكن يجب رغم ذلك وجود resource limits لحماية المستخدم من accidental OOM.

---

# 21. Packaging gaps

## جيد حاليًا

- `pyproject.toml`
- Hatchling
- Apache-2.0
- typed package (`py.typed`)
- project URLs
- optional `excel`

## ينقص

- Documentation URL
- changelog URL
- fuller classifiers
- explicit supported OS if tested
- optional extras المخطط لها (`viz`, `ml`, `privacy`, `polars`, `duckdb`, `spark`, `all`)
- lock/constraints strategy للتطوير
- wheel/sdist build validation in CI
- installation smoke test from built wheel
- import smoke test
- PyPI name/release automation confirmation
- dependency license generation (`DEPENDENCY_LICENSES.json`)
- `THIRD_PARTY_NOTICES.md` منفصل إذا توسعت dependencies

---

# 22. CI/CD gaps

لا توجد `.github/workflows/` داخل الـsdist المراجع. قد تكون موجودة في GitHub وغير موزعة؛ يجب التحقق من المستودع نفسه قبل الحكم النهائي.

المطلوب في repo:

- pytest matrix Python 3.10–3.12 وربما 3.13 بعد الدعم
- Windows/Linux/macOS
- ruff check + format
- mypy/pyright
- coverage
- build wheel/sdist
- install built wheel and test
- docs build
- dependency/security scan
- release workflow
- PyPI trusted publishing
- benchmark job منفصل

---

# 23. Test-suite gaps

81 tests على fixture واحدة بداية قوية، لكنها ليست كافية لمكتبة عامة.

ينقص:

- synthetic property tests
- Hypothesis
- fuzz parsing tests
- locale tests
- empty dataframe
- one-row dataframe
- duplicate column names
- MultiIndex
- nullable pandas dtypes
- categorical dtype
- Arrow-backed dtypes
- timezone-aware datetime
- huge integers/decimals
- Unicode scripts أوسع
- malformed objects
- custom indices (الـEvidence حاليًا يخزن positional rows كـints)
- detector failure behavior
- plugin registry collisions
- concurrency
- performance regression
- memory regression
- serialization compatibility
- backward API compatibility
- mutation attempts by malicious/broken detector

### ملاحظة مهمة حول indices

الكود يستخدم في عدة مواضع `np.flatnonzero` ويخزن `affected_rows` كأرقام موضعية. يجب تحديد هل هذه **positions** أم **index labels**. في DataFrame ذات index غير 0..n-1 قد يلتبس على المستخدم. الأفضل تخزين الاثنين أو استخدام RowReference واضح.

---

# 24. Performance gaps

`scan()` يعمل detector-by-detector على pandas، وبعض detectors قد تعيد parsing لنفس العمود أكثر من مرة.

ينقص:

- shared profiling cache
- parsed-column cache
- semantic type cache
- execution planner
- detector timing
- memory estimates
- sampling policy
- approximate algorithms
- parallel execution حيث آمن
- lazy backends

قبل توسيع detectors، يجب منع تكرار O(n) parsing لكل detector دون cache.

---

# 25. Data Dictionary integration

الـfixture يحتوي `data_dictionary`، لكن الاختبارات تقرأ `raw_data` فقط، و`RuleSource.DATA_DICTIONARY` موجود دون ingestion فعلي.

هذه فجوة مهمة.

المطلوب:

```python
project = sp.Project(df, data_dictionary=...)
```

أو contract ingestion يحول dictionary إلى:

- descriptions
- semantic types
- ranges
- units
- keys
- nullable rules
- domain rules

ثم يقارن inferred schema بالمعلن.

---

# 26. Rule Source Provenance غير مستغل بالكامل

`RuleSource` ممتاز، لكن detectors الحالية تعتمد غالبًا hard-coded/default rules.

يجب مستقبلًا أن يحمل كل rule:

- source id
- source version
- source URI/reference
- author/provider
- confidence/trust level
- effective date

خصوصًا domain/reference packs.

---

# 27. CompletionState موجود لكنه غير مستخدم

`CompletionState` enum موجود، لكن لا يوجد Auto Result ليحسب الحالة النهائية.

يجب تعريف algorithm رسمي يحدد متى تكون النتيجة:

- CLEAN
- CLEAN_WITH_NOTES
- CLEAN_WITH_WARNINGS
- PARTIALLY_RESOLVED
- GUIDED_REVIEW_RECOMMENDED
- GUIDED_REVIEW_REQUIRED
- DOMAIN_REVIEW_REQUIRED
- BLOCKED

مع tests مستقلة لكل حالة.

---

# 28. `verified_df` غير موجود

AD-004 يعرّف semantics جيدة جدًا لـ`verified_df`، لكن لا يوجد object يطبقها.

المطلوب:

```python
result.finalize()
result.verified_df
```

مع waiver model موثق ومؤرشف.

---

# 29. Idempotence غير منفذ

الخطة طلبت:

```python
project.test_idempotence()
```

ويجب أن يصبح جزءًا من repair engine واختبارات العمليات:

```text
clean(clean(df)) == clean(df)
```

خصوصًا normalization/category/text operations.

---

# 30. Root Cause Analysis غير منفذ

الحالي يكتشف format conflict، لكنه لا يوجد محرك عام يربط المشاكل بمصدر مشترك مثل:

```text
source_file / branch / system / period / batch
```

ينقص:

- issue clustering
- source attribution
- common-cause ranking
- upstream-change hints
- root-cause report

---

# 31. Rule Learning / Knowledge Base غير منفذ

ينقص:

- Project Rules
- Organization Rules
- Domain Rules
- Built-in Rules
- promotion policy
- conflict resolution
- versioning
- audit

---

# 32. Benchmark Suite غير موجود فعليًا

الـstress fixture هو acceptance baseline، لكنه ليس `SmartPrepBench` المقارن.

ينقص benchmark يقيس:

- precision
- recall
- repair accuracy
- false positives
- false negatives
- information loss
- distribution preservation
- runtime
- peak memory
- user effort

ومقارنة عادلة مع الأدوات المرجعية حيث يمكن.

---

# 33. References — قوية لكن تحتاج تحويلًا إلى سجل قابل للصيانة

`REFERENCES.md` جيد جدًا، لكن الخطة كانت تطلب أيضًا:

```text
competitive_gap_registry.yaml
DEPENDENCY_LICENSES.json
THIRD_PARTY_NOTICES.md
```

كما يفضل لكل مرجع إضافة:

- last reviewed date
- version reviewed
- license
- feature mapping
- implementation status in SmartPrep
- tests/acceptance criteria المرتبطة

حتى لا تصبح المراجع قائمة ثابتة قديمة.

---

# 34. Documentation vs implementation consistency

ميزة قوية: README يصرح صراحة بما هو غير منفذ.

لكن توجد نقطة يجب مراقبتها: `_ARCHITECTURE_DECISIONS.md` يصف APIs مستقبلية (`auto_prepare`, `verified_df`, `clean(detailed=True)`) بتفصيل يشبه specification. يجب الحفاظ على فصل واضح بين:

```text
Implemented API
Planned API
Frozen design contract
```

حتى لا يقرأ المستخدم ملفًا داخليًا ويظن أن API موجودة.

---

# 35. اقتراح هيكل المرحلة القادمة

لا تبدأ بالـStudio الآن. الترتيب المقترح:

## Phase A — Core repair foundation

1. `Operation`
2. `RepairPlan`
3. `AuditRecord`
4. `DatasetSnapshot`
5. `PreparationResult`
6. transaction/rollback
7. dependency graph
8. post-operation scoped rescan

## Phase B — Safe Auto

1. mechanical whitespace/case normalization
2. safe numeric parsing
3. safe date format normalization فقط عندما غير ملتبس
4. safe no-op structural missingness handling
5. warnings/escalation
6. completion states
7. before/after metrics

## Phase C — Guided

1. review queue
2. treatment comparison
3. preview
4. user decisions
5. waivers
6. custom rules
7. resume/replay

## Phase D — Reports

1. Markdown/JSON أولًا
2. HTML interactive
3. PDF
4. pre/post comparison

## Phase E — Preprocessing

missing → encoding → scaling → transforms → feature engineering

## Phase F — Validation/Contracts

## Phase G — Interactive Studio

بعد استقرار الـCore.

---

# 36. Definition of Done المقترحة لـv0.1 alpha

قبل تسمية النسخة `0.1.0` غير dev، أوصي بالحد الأدنى التالي:

- [ ] كل 81 acceptance tests تعمل في CI ولا تعتمد على fixture مفقودة.
- [ ] ruff/mypy/build يمرون في CI.
- [ ] wheel + sdist smoke tested.
- [ ] `sp.scan()` API موثقة بالكامل.
- [ ] detector applicability model واضح.
- [ ] failed detector يظهر بوضوح للمستخدم.
- [ ] issue serialization JSON موجود.
- [ ] row references لا تلتبس بين position وindex label.
- [ ] README لا يحتوي أرقام tests غير قابلة لإعادة الإنتاج من artifact.
- [ ] docs بسيطة على الأقل لـScan API وdetectors وissue model.
- [ ] GitHub Actions منشورة.
- [ ] release process واضح.

إذا كان `0.1.0` المقصود به **Diagnosis-only alpha**، لا يلزم انتظار Auto/Guided. أما إذا كان المقصود أول إصدار يمثل فكرة SmartPrep الأساسية، فيجب إضافة Auto + Guided + Audit قبل رفع صفة dev.

---

# 37. Definition of Done المقترحة لـv0.2

- [ ] `auto_prepare()`
- [ ] `clean()` alias
- [ ] `PreparationResult`
- [ ] audit trail
- [ ] warnings/escalation
- [ ] completion states
- [ ] undo/rollback
- [ ] idempotence
- [ ] before/after metrics
- [ ] Markdown/JSON reports

---

# 38. Definition of Done المقترحة لـv0.3

- [ ] `guided_prepare()`
- [ ] review queue
- [ ] treatment sandbox
- [ ] preview/compare
- [ ] custom rules
- [ ] waiver/finalize/verified_df
- [ ] HTML reports

---

# 39. أهم 15 مهمة تالية بالترتيب

1. إصلاح توزيع/تشغيل stress-test fixture.
2. تعريف `RowReference` واضح بدل int مبهم.
3. إضافة detector applicability protocol.
4. إضافة strict/failure policy لـ`scan()`.
5. تصميم `Operation` و`RepairPlan`.
6. تصميم `PreparationResult`.
7. بناء Audit/Snapshot/Transaction layer.
8. تنفيذ أول مجموعة SAFE_AUTO_FIX فقط.
9. إعادة الفحص بعد الإصلاح حسب dependency graph.
10. حساب CompletionState.
11. إضافة Data Health Score.
12. إضافة Markdown/JSON before-after reports.
13. بناء Guided Review Queue.
14. إضافة serialization/config/rule persistence.
15. بعد استقرار ذلك، بدء Interactive Studio.

---

# 40. التقييم النهائي

SmartPrep الحالية **نواة جيدة وليست prototype عشوائيًا**. توجد قرارات معمارية صحيحة واختبارات safety مهمة، وهذا أفضل من البدء بواجهة ضخمة ثم محاولة إصلاح المنطق لاحقًا.

أقوى أجزاء النسخة الحالية:

1. فصل detection confidence عن repair confidence.
2. demotion-only safety policy.
3. عدم اختراع علاج عند الغموض.
4. negative acceptance tests.
5. semantic missingness.
6. conflicting duplicates كفئة مستقلة.
7. date ambiguity separation.
8. architecture decisions record.
9. references/prior-art discipline.
10. README صادق بشأن حالة التنفيذ.

أكبر النقائص:

1. لا يوجد Repair Engine.
2. لا يوجد Auto/Guided.
3. لا يوجد Audit/Lineage للتغييرات.
4. لا توجد Reports/EDA قبل وبعد.
5. لا يوجد Preprocessing.
6. لا توجد Validation/Contracts/Privacy/Drift.
7. لا يوجد Multi-backend.
8. لا يوجد Studio.
9. التوثيق الكامل المطلوب غير موجود بعد.
10. stress tests الرئيسية تُتخطى من الـsdist بسبب غياب fixture.

**الخلاصة:** حافظ على هذه النواة، ولا تعِد كتابتها. ابنِ فوقها طبقة العمليات والإصلاح أولًا. أهم شيء الآن هو تحويل SmartPrep من **Detector Suite ذكية** إلى **Preparation Engine آمنة وقابلة لإعادة الإنتاج**؛ بعدها تصبح بقية أجزاء الخطة — التقارير، Guided Mode، Studio، preprocessing والـbackends — امتدادات طبيعية فوق Core واحد مستقر.
