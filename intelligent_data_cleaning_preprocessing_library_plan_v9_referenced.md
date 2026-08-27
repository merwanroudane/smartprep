# خطة شاملة لبناء مكتبة Python ذكية وتفاعلية للتنظيف والمعالجة المسبقة للبيانات

> **الهدف:** تصميم مكتبة حديثة تتجاوز فكرة “تنظيف البيانات آليًا” إلى منصة متكاملة لفهم جودة البيانات، تشخيص المشكلات، اقتراح ومعاينة ومقارنة الحلول، تنفيذ Cleaning وPreprocessing، قياس أثر القرارات، توثيقها، وإعادة إنتاجها؛ مع واجهة تفاعلية مدمجة تضاهي أدوات مثل PyGWalker وD-Tale ولكن تكون موجهة أساسًا إلى Data Preparation لا إلى الاستكشاف البصري فقط.
>
> **حالة المراجعة:** الخطة مبنية على مراجعة اتجاهات ووثائق الأدوات الحالية حتى أغسطس 2026، ومنها YData Profiling، PyGWalker، D-Tale، PyJanitor، DataPrep.Clean، Pandera، Great Expectations، Soda، Scikit-learn، Feature-engine، Cleanlab Datalab وغيرها.

---

## 1. الرؤية الكبرى للمكتبة

المكتبة المقترحة لا ينبغي أن تكون نسخة أخرى من مكتبة تحتوي على مجموعة دوال من نوع:

```python
fill_missing()
remove_duplicates()
encode_categories()
scale_features()
```

لأن هذه الوظائف أصبحت Commodity ومتوافرة في عشرات الأدوات.

الرؤية الأقوى هي بناء **Intelligent Data Preparation Platform** تعمل وفق دورة متكاملة:

**Understand → Profile → Diagnose → Explain → Recommend → Compare → Preview → Apply → Validate → Measure Impact → Track → Reproduce → Monitor**

أي أن المكتبة لا تسأل فقط: “كيف ننظف هذه البيانات؟” بل تجيب أيضًا عن:

- ما المشكلة فعلًا؟
- ما درجة خطورتها؟
- هل تحتاج إصلاحًا أصلًا؟
- ما الحلول الممكنة؟
- ما الحل الأنسب لهذا النوع من البيانات وهذا الهدف التحليلي؟
- ما أثر كل حل على التوزيع والارتباطات والنتائج اللاحقة؟
- ما مقدار الثقة في التوصية؟
- ما الذي تغيّر بالضبط؟
- هل يمكن التراجع عنه؟
- هل يمكن تحويل كل التفاعلات إلى Pipeline قابلة لإعادة التنفيذ؟

وهذه هي الهوية التي يمكن أن تجعل المشروع مختلفًا فعلًا.

---

# 2. الاسم المفاهيمي للمشروع

يمكن التفكير مؤقتًا في أسماء من نوع:

- `DataSage`
- `SmartPrep`
- `DataMedic`
- `CleanPilot`
- `PrepIntel`
- `DataClinic`
- `DataDoctor`
- `PrepWise`
- `DataForge`
- `CleanMind`

لكن الاسم النهائي يجب اختياره بعد فحص PyPI وGitHub والعلامات التجارية.

في هذه الوثيقة سأستخدم الاسم المؤقت:

```text
SmartPrep
```

---

# 3. المشكلة في الأدوات الحالية

السوق الحالي قوي لكنه **مجزأ**.

## 3.1 YData Profiling

قوي في:

- Automated profiling.
- Univariate statistics.
- Missing data visualization.
- Correlations and interactions.
- Alerts عن high cardinality والduplicates والzeros والconstants وغيرها.
- دعم tabular وtime-series وبعض أنواع النصوص والصور.

لكن فلسفته الأساسية هي **التشخيص والتقرير**. الوثائق نفسها تؤكد أن التنبيه لا يعني بالضرورة وجود مشكلة فعلية وأن الحكم النهائي يحتاج معرفة المجال.

### ما الذي نأخذه منه؟

- سرعة الحصول على صورة أولية شاملة.
- نظام alerts.
- التقارير الغنية.
- فصل profiling عن القرار النهائي.

### ما الذي نتجاوزه؟

نحوّل التنبيه إلى سلسلة كاملة:

```text
Alert
→ Evidence
→ Severity
→ Root cause hypothesis
→ Candidate treatments
→ Recommendation
→ Impact simulation
→ Apply / Reject
```

---

## 3.2 PyGWalker

القيمة الكبرى فيه هي تجربة الاستخدام التفاعلية للاستكشاف وعرض البيانات، خصوصًا فكرة تحويل DataFrame إلى مساحة تحليل بصري مباشرة، مع دعم بيئات وأطر بيانات متعددة بدرجات مختلفة.

### ما الذي نأخذه؟

- التفاعل داخل notebook.
- Drag-and-drop philosophy.
- سهولة الاستخدام للباحث غير المبرمج.
- التفاعل المستمر مع DataFrame.
- إمكانية الانتقال بين code وUI.

### ما الذي يجب أن نتجاوزه؟

بدل أن يكون مركز الواجهة:

```text
Build visualization
```

يكون مركزها:

```text
Understand → Repair → Compare → Approve
```

أي أن الواجهة تصبح **Data Preparation Studio** لا مجرد Visualization Studio.

---

## 3.3 D-Tale

D-Tale يجمع Flask backend مع React frontend ويقدم عارضًا غنيًا لـPandas مع filtering، sorting، editing، column analysis، charts، replacements وغيرها، ويعمل أيضًا داخل Jupyter وبعض البيئات المستضافة.

### ما الذي نأخذه؟

- Data grid قوي.
- Column menus.
- عمليات مباشرة من الواجهة.
- القدرة على تعديل البيانات وليس فقط عرضها.
- Architecture منفصلة frontend/backend.

### ما الذي نتجاوزه؟

كل تعديل في SmartPrep يجب أن يكون:

- قابلًا للمعاينة قبل التطبيق.
- موثق السبب.
- مرتبطًا باقتراح أو قرار.
- قابلًا للتراجع.
- له Before/After impact.
- يمكن تصديره إلى كود.

---

## 3.4 PyJanitor

قوته الأساسية في API نظيفة قائمة على method chaining، مع وظائف عملية للتنظيف وإعادة تشكيل البيانات.

مثال الفلسفة:

```python
df.clean_names().remove_empty()
```

### ما الذي نأخذه؟

- أسماء أفعال واضحة.
- Chaining.
- العمليات الصغيرة القابلة للتركيب.
- عدم إخفاء ما يجري عن المستخدم.

### ما الذي نتجاوزه؟

إضافة طبقة intelligence فوق العمليات:

```python
project.recommend().preview().apply()
```

بدل أن يكون المستخدم هو الذي يعرف منذ البداية العملية المناسبة.

---

## 3.5 DataPrep.Clean

DataPrep.Clean مهم لأنه يقدم cleaning متخصصًا بحسب semantic/domain type، مثل:

- country names.
- dates.
- email.
- geocoordinates.
- IP addresses.
- phone numbers.
- URLs.
- text.
- ISBN.
- وغير ذلك.

كما يقدم `clean_ml` لمسار preprocessing تقليدي للـML.

### ما الذي نأخذه؟

فكرة أن التنظيف يجب ألا يعتمد فقط على dtype، بل على **المعنى الدلالي**.

### ما الذي نتجاوزه؟

بدل أن يحدد المستخدم يدويًا أن العمود Email أو Country، تقوم المكتبة بـ:

```text
Semantic inference
+ confidence score
+ validation
+ recommended canonical representation
```

---

## 3.6 Pandera

Pandera أصبحت إطارًا قويًا للتحقق من صحة DataFrames، مع schemas وchecks وlazy validation ودعم عدة backends تشمل pandas وPolars وIbis وPySpark وغيرها، ومع اتجاه حديث إلى backend موحد قائم على Narwhals.

### ما الذي نأخذه؟

- Schema-first validation.
- Runtime guarantees.
- Lazy validation.
- Multi-backend architecture.
- Schema serialization.

### ما الذي نتجاوزه؟

SmartPrep يمكن أن **يستنتج schema أولية** ثم يجعلها تفاعلية:

```text
Observed schema
Expected schema
Violations
Suggested corrections
Data contract export
```

---

## 3.7 Great Expectations وSoda

هذه الأدوات تضع Data Quality داخل سياق الإنتاج، checks، expectations، checkpoints، data contracts وCI/CD.

### ما الذي نأخذه؟

- Data contracts.
- Quality gates.
- Production validation.
- Versioned expectations.
- Pass/fail rules.

### ما الذي نتجاوزه؟

أن تنشأ القواعد تلقائيًا من الاستكشاف والتنظيف:

```text
Data profiling
→ inferred expectations
→ human review
→ contract
→ pipeline gate
```

أي أن العمل exploratory يتحول طبيعيًا إلى production contract.

---

## 3.8 Scikit-learn

Scikit-learn يضع معيارًا مهمًا جدًا:

```python
fit()
transform()
fit_transform()
```

ويوفر `Pipeline` و`ColumnTransformer` لتكوين preprocessing قابل لإعادة الاستخدام والـcross-validation.

### القيمة التي يجب تبنيها

كل transformation تعلم parameters من البيانات يجب أن تلتزم بـfit/transform semantics لتجنب leakage.

---

## 3.9 Feature-engine

Feature-engine تغطي مساحة كبيرة من preprocessing والfeature engineering:

- missing imputation.
- categorical encoding.
- discretization.
- outlier handling.
- mathematical transformations.
- scaling.
- datetime features.
- text features.
- time-series features.
- selection.
- sklearn compatibility.

### ما الذي نأخذه؟

- اتساع الوظائف.
- Sklearn compatibility.
- الاحتفاظ بأسماء المتغيرات بصورة مفهومة.

### ما الذي نتجاوزه؟

إضافة recommendation/benchmarking layer لاختيار transformer بدل أن يختاره المستخدم يدويًا دائمًا.

---

## 3.10 Cleanlab Datalab

Cleanlab يضيف بُعدًا مهمًا: جودة البيانات لا تعني missing/outliers فقط. يمكن أن تشمل:

- label issues.
- outliers.
- near duplicates.
- drift.
- other ML-centric dataset issues.

### ما الذي نأخذه؟

مفهوم أن مشكلة البيانات قد لا تكون syntactic، بل قد تكون **تعليمية/إشرافية/نموذجية**.

### ما الذي نتجاوزه؟

دمج هذا النوع من الفحص مع cleaning التقليدي في نفس Data Health model.

---

# 4. القيمة المضافة المركزية للمكتبة

أقترح أن تركز SmartPrep على 12 قيم مضافة رئيسية.

## 4.1 Intelligent Diagnosis وليس Profiling فقط

كل مشكلة تحمل:

```text
Issue
Type
Severity
Confidence
Evidence
Affected rows
Affected columns
Possible causes
Candidate treatments
Recommended treatment
Risk of treatment
```

مثال:

```text
Issue: Missing values
Column: annual_revenue
Severity: High
Confidence: 0.96
Pattern: strongly associated with sector
Possible mechanism: MAR-like pattern
Recommended treatment: groupwise median / iterative imputation
Deletion risk: High
```

---

## 4.2 Treatment Recommendation Engine

هذا يجب أن يكون قلب المنتج.

المحرك لا يكتفي بوجود عدة algorithms، بل يقوم بترتيبها.

مثلاً:

```text
Candidate                     Score
-----------------------------------
Median imputation             71
KNN                           82
Iterative                     89
Groupwise median              93
Drop rows                     34
```

والـScore لا يكون سحريًا؛ يجب أن يفكك إلى أبعاد:

```text
Distribution preservation
Correlation preservation
Downstream performance
Bias risk
Variance distortion
Runtime
Memory cost
Interpretability
Leakage risk
```

---

## 4.3 Explainable Cleaning

كل توصية يجب أن تملك `why()`.

```python
project.explain(issue_id="MISS_014")
```

الناتج:

```text
Recommended GroupMedianImputer because:
- missingness differs strongly by sector;
- revenue is right-skewed;
- global mean creates 8.2% variance reduction;
- median preserves rank structure better;
- sample size is sufficient within major sectors.
```

هذه يمكن تسميتها:

**Explainable Data Cleaning (XDC)**.

---

## 4.4 Counterfactual Treatment Comparison

بدل أن نجرب حلًا واحدًا، يمكن إنشاء branches افتراضية:

```text
Raw
├── median
├── KNN
├── iterative
└── groupwise median
```

ثم قياس الفرق.

هذه فكرة قوية جدًا لأنها تحول cleaning إلى **قرار قابل للمقارنة** بدل rule of thumb.

---

## 4.5 Before/After Impact Engine

أي معالجة يجب أن ينتج عنها تقرير أثر.

### على مستوى المتغير

- mean.
- median.
- variance.
- standard deviation.
- skewness.
- kurtosis.
- quantiles.
- number of unique values.
- missing rate.

### على مستوى العلاقات

- Pearson/Spearman correlations.
- mutual information.
- covariance.
- categorical associations.

### على مستوى البيانات ككل

- row count.
- dimensionality.
- sparsity.
- duplicate rate.
- memory usage.

### على مستوى المهمة اللاحقة

اختياريًا:

- CV score.
- calibration.
- coefficient stability.
- feature importance stability.
- forecast error.

---

## 4.6 Human-in-the-Loop

ثلاثة أنماط تشغيل:

```python
project.run(mode="audit")
project.run(mode="recommend")
project.run(mode="auto")
```

### audit

لا تغيير.

### recommend

توصيات + preview.

### auto

تنفيذ القرارات التي تتجاوز confidence threshold فقط.

مثلاً:

```python
project.run(mode="auto", min_confidence=0.97)
```

أما القرارات غير الواضحة فتبقى:

```text
Human review required
```

---

## 4.7 Semantic Type Intelligence

بدل الاعتماد على:

```text
int64
float64
object
```

يجب استنتاج:

- identifier.
- categorical nominal.
- categorical ordinal.
- count.
- percentage.
- monetary.
- currency.
- email.
- phone.
- country.
- region.
- city.
- postal code.
- URL.
- IP.
- latitude.
- longitude.
- datetime.
- duration.
- age.
- year.
- rating.
- boolean.
- free text.
- target.
- panel identifier.
- time index.

مع احتمالات:

```text
annual_revenue
monetary       0.94
continuous     0.05
identifier     0.01
```

---

## 4.8 Context-Aware Preparation

نفس البيانات لا تنظف بنفس الطريقة لكل هدف.

واجهة الهدف:

```python
project.set_goal("eda")
project.set_goal("econometrics")
project.set_goal("machine_learning")
project.set_goal("deep_learning")
project.set_goal("time_series")
project.set_goal("panel_data")
project.set_goal("causal_inference")
```

كل Context يغير rules والتوصيات.

### مثال

One-hot encoding قد يكون منطقيًا لنموذج ML معين لكنه ليس “تنظيفًا” مطلوبًا لتقرير وصفي.

Scaling ضروري لبعض الخوارزميات وغير مهم للأشجار.

Interpolation في time series يجب أن يراعي الزمن ولا يعامل البيانات كـcross-section.

---

## 4.9 Reversible Cleaning + Version Graph

المكتبة يجب أن تتصرف مثل Git للبيانات.

```python
project.history()
project.undo()
project.redo()
project.checkout("v3")
project.diff("v2", "v5")
```

والأفضل هو **branching**:

```python
project.branch("knn-imputation")
project.branch("mice-imputation")
```

ثم المقارنة.

---

## 4.10 Full Audit Trail

كل تغيير يسجل:

```text
operation_id
operator
parameters
columns
rows affected
values changed
reason
recommendation score
confidence
user approval
before fingerprint
after fingerprint
timestamp
software version
```

وهذا مهم للبحث العلمي، التمويل، الإدارة، التنظيم، والحوكمة.

---

## 4.11 Reproducibility by Construction

كل ما يحدث في UI يجب تحويله إلى pipeline.

```python
project.export_python("pipeline.py")
project.export_yaml("pipeline.yaml")
project.export_sklearn()
project.export_report("report.html")
project.export_contract("contract.yaml")
```

وبذلك لا تصبح الواجهة التفاعلية “نقرة لا يمكن إعادة إنتاجها”.

---

## 4.12 Multi-backend from the Beginning

لا تربط المشروع بـPandas داخليًا.

التصميم المقترح:

```text
Public API
   ↓
Data Abstraction Layer
   ↓
Narwhals / Arrow-like abstraction
   ↓
Pandas | Polars | Ibis | Arrow | DuckDB
```

ثم لاحقًا:

```text
Dask | Spark | Ray
```

---

# 5. الجزء التفاعلي: SmartPrep Studio

هذا الجزء يجب ألا يكون إضافة جانبية؛ بل **منتجًا أساسيًا**.

يمكن تشغيله:

```python
project.studio()
```

أو:

```python
smartprep.launch(df)
```

ويعمل داخل:

- Jupyter Notebook.
- JupyterLab.
- Google Colab قدر الإمكان.
- VS Code notebooks.
- standalone browser.
- لاحقًا Streamlit component أو server mode.

---

# 6. تصميم الواجهة التفاعلية

## 6.1 الصفحة الرئيسية: Data Health Dashboard

تعرض:

```text
Rows
Columns
Memory
Duplicate rate
Missing rate
Invalid rate
Potential anomalies
Schema violations
High-cardinality features
Data Health Score
Preparation Readiness
```

مع تقسيم:

```text
Critical
Warning
Review
Informational
```

---

## 6.2 Data Grid

شبكة بيانات افتراضية سريعة مع:

- sorting.
- filtering.
- search.
- freeze columns.
- hide/show.
- dtype badge.
- semantic type badge.
- missing markers.
- anomaly highlighting.
- rule violation highlighting.
- row quality score.

النقطة المضافة المهمة:

**لا تلوّن الخلايا فقط، بل تشرح لماذا علّمتها كمشكلة.**

---

## 6.3 Column Inspector

عند النقر على أي عمود:

### Identity

- technical dtype.
- semantic dtype.
- inferred role.
- confidence.

### Statistics

- summary stats.
- quantiles.
- cardinality.
- missingness.

### Quality

- invalid values.
- anomalies.
- inconsistent formats.
- rare categories.

### Relationships

- strongest associations.
- potential leakage.
- target relationship.

### Recommended actions

كل action معها:

```text
Why
Confidence
Expected effect
Risk
Preview
Apply
```

---

## 6.4 Missing Data Lab

بدل heatmap فقط، يحتوي على:

- matrix.
- bar plot.
- pattern table.
- co-missingness network.
- missingness by group.
- missingness vs target.
- time-ordered missingness.
- candidate mechanism diagnostics.

ثم Treatment Lab:

```text
Delete
Constant
Mean
Median
Mode
Group-wise
KNN
Iterative/MICE-like
Model-based
Interpolation
Forward fill
Backward fill
Seasonal/time-aware
```

كل طريقة لها Preview وImpact Score.

---

## 6.5 Duplicate & Entity Resolution Lab

ثلاث طبقات:

### Exact duplicates

مطابقة كاملة.

### Key duplicates

تكرار مفاتيح محددة.

### Near duplicates

مثلاً:

```text
Mohamed Benali
Mohamed Ben Ali
M. Benali
```

مع fuzzy matching، phonetic matching، token similarity، وblocking.

يمكن إضافة workflow:

```text
Potential duplicate cluster
→ side-by-side comparison
→ merge rule
→ canonical record
```

هذه إضافة قوية جدًا إلى مكتبة cleaning عامة.

---

## 6.6 Outlier & Anomaly Lab

يجب عدم اختزال outlier إلى IQR فقط.

### Univariate

- IQR.
- MAD.
- z-score.
- robust z.
- percentile rules.

### Multivariate

- Isolation Forest.
- LOF.
- distance-based.
- robust covariance.

### Contextual

- per-group anomaly.
- time-series anomaly.

واجهة المقارنة:

```text
Method       Flagged    Stability    Runtime
IQR          43         0.82         Low
MAD          39         0.91         Low
IForest      51         0.87         Medium
LOF          47         0.84         Medium
```

ثم Treatment:

- keep.
- flag only.
- cap.
- winsorize.
- transform.
- remove.
- replace/model.

---

## 6.7 Categorical Data Lab

- normalization.
- case/whitespace.
- rare levels.
- inconsistent spelling.
- fuzzy clustering.
- hierarchical categories.
- unknown/new categories.
- high cardinality.

Preprocessing options:

- one-hot.
- ordinal.
- frequency.
- target/mean encoding مع leakage-safe workflow.
- hashing.
- similarity encoding.
- rare-category grouping.

---

## 6.8 Numeric Transformation Lab

- scaling.
- standardization.
- robust scaling.
- min-max.
- max-abs.
- power transforms.
- Box-Cox.
- Yeo-Johnson.
- log/log1p.
- quantile transformation.
- discretization.

مع مقارنة distribution before/after.

---

## 6.9 Date & Time Lab

- parse detection.
- mixed date formats.
- timezone consistency.
- invalid dates.
- missing periods.
- duplicated timestamps.
- irregular frequency.
- date-part extraction.
- cyclical encoding.

---

## 6.10 Text Cleaning Lab

ليس NLP كاملًا، لكن cleaning غني:

- Unicode normalization.
- whitespace.
- HTML.
- URLs.
- punctuation.
- emojis optional.
- casing.
- transliteration optional.
- language detection.
- encoding problems/mojibake.
- repeated characters.

مع مبدأ: لا تطبق lowercasing أو stopword removal تلقائيًا من دون معرفة الهدف.

---

## 6.11 Data Rules Lab

واجهة بدون كود لإنشاء قواعد مثل:

```text
age >= 0
payment <= invoice_amount
end_date >= start_date
country == "DZ" → currency in {"DZD", ...}
status == "paid" → payment_amount > 0
```

ثم تحويلها إلى:

- SmartPrep rules.
- Pandera schema.
- Great Expectations-style expectation.
- Soda-like contract where feasible.

---

## 6.12 Pipeline Builder

واجهة DAG مرئية:

```text
Raw
 ↓
Normalize names
 ↓
Type repair
 ↓
Deduplicate
 ↓
Missing treatment
 ↓
Outlier treatment
 ↓
Encoding
 ↓
Scaling
 ↓
Validation
```

كل node يعرض:

- inputs.
- outputs.
- runtime.
- row/column changes.
- warnings.
- learned parameters.

يمكن سحب العقد وإعادة ترتيبها إذا كانت dependencies تسمح.

---

## 6.13 Before/After Compare

Split screen:

```text
BEFORE | AFTER
```

ومقارنة:

- rows.
- columns.
- cells modified.
- missing.
- distribution.
- correlations.
- memory.
- downstream score.

---

## 6.14 History & Undo

Timeline:

```text
v0 Load data
v1 Clean names
v2 Type fixes
v3 Remove exact duplicates
v4 Groupwise imputation
v5 Rare category grouping
```

مع:

```text
Undo
Redo
Branch
Compare
Restore
```

---

# 7. ميزة يمكن أن تجعل الواجهة أفضل من PyGWalker لهذه المهمة

PyGWalker ممتاز عندما يكون السؤال: “ماذا يوجد في البيانات وكيف أستكشفه بصريًا؟”

SmartPrep Studio يجب أن يكون أفضل عندما يكون السؤال:

> **“ما الخطأ في البيانات، ماذا أفعل حياله، ولماذا، وما أثر القرار؟”**

وبالتالي التفوق ليس في عدد الرسوم، بل في **القرار التفاعلي القابل لإعادة الإنتاج**.

---

# 8. Data Health Model

يمكن إنشاء درجات متعددة بدل Score واحدة مضللة.

```text
Completeness            91
Validity                86
Consistency             74
Uniqueness              95
Schema conformity       82
Semantic conformity     79
Temporal integrity      88
ML label quality        67
```

ثم Readiness Scores:

```text
EDA readiness           96
Reporting readiness     90
Econometrics readiness  81
ML readiness            78
Time-series readiness   72
Production readiness    64
```

يجب أن تكون المعادلات:

- documented.
- configurable.
- decomposable.
- never presented as absolute truth.

---

# 9. Data Quality Taxonomy داخل المكتبة

يجب بناء taxonomy رسمية للمشكلات.

## A. Structural issues

- missing columns.
- unexpected columns.
- duplicate columns.
- wrong names.
- wrong order where relevant.

## B. Type issues

- technical dtype mismatch.
- semantic type mismatch.
- mixed types.
- parse errors.

## C. Missingness

- explicit nulls.
- disguised nulls مثل `?`, `NA`, `-999`.
- structural missingness.
- temporal gaps.

## D. Duplication

- row duplicates.
- key duplicates.
- near duplicates.
- entity duplicates.

## E. Validity

- range violations.
- regex violations.
- domain violations.
- impossible values.

## F. Consistency

- cross-column rules.
- unit inconsistency.
- currency inconsistency.
- mixed categories.

## G. Distribution issues

- extreme skew.
- zero inflation.
- constant/near constant.
- rare categories.
- anomalous tails.

## H. Outliers/anomalies

- univariate.
- multivariate.
- contextual.
- temporal.

## I. Relationship issues

- multicollinearity.
- leakage.
- duplicate information.
- deterministic relations.

## J. Label issues

- likely label errors.
- ambiguous examples.
- class imbalance.
- duplicate contradictory labels.

## K. Temporal issues

- duplicate timestamps.
- gaps.
- irregular frequency.
- future leakage.
- unsorted time.

## L. Panel-data issues

- duplicate entity-time keys.
- gaps by entity.
- unbalanced panel.
- time-invariant variables.
- inconsistent entity identifiers.

---

# 10. Econometrics-aware Preparation

هذه يمكن أن تصبح ميزة تنافسية نادرة.

## 10.1 Panel Data Doctor

```python
project.set_context(
    "panel",
    entity="country",
    time="year"
)
```

يفحص:

- uniqueness of entity-time key.
- balanced/unbalanced structure.
- missing periods per entity.
- duplicate time records.
- insufficient within variation.
- invariant features.
- inconsistent units across countries/entities.
- extreme gaps.

## 10.2 Time Series Doctor

```python
project.set_context("time_series", time="date")
```

يفحص:

- frequency.
- missing timestamps.
- gaps.
- duplicate timestamps.
- irregular spacing.
- interpolation danger.
- structural jumps as potential data error vs genuine break.

## 10.3 Econometric leakage/transform warnings

مثلاً:

- عدم عمل standardization بلا داعٍ على تقرير وصفي.
- تحذير عند عمل imputation باستخدام معلومات مستقبلية.
- تحذير من encoding يمس تفسير معاملات النموذج.
- فصل cleaning الضروري عن transformation التحليلي.

---

# 11. Missing Data Intelligence

المكتبة يمكن أن تصبح قوية جدًا إذا كان missingness module علميًا.

## Detection

- standard NA.
- sentinels.
- blank strings.
- impossible placeholders.

## Pattern analysis

- by column.
- by row.
- co-missingness.
- by subgroup.
- by target.
- by time.

## Treatment ranking

القرار يراعي:

- variable type.
- missing rate.
- pattern.
- sample size.
- distribution.
- relationship with other variables.
- analysis context.
- train/test split.
- time ordering.

## Validation after imputation

- distribution shift.
- variance shrinkage.
- correlation distortion.
- model performance stability.

---

# 12. Leakage Guard

ميزة أساسية يجب تصميمها من البداية.

المكتبة تمنع أو تحذر من:

- fitting imputers على كامل dataset قبل split.
- target encoding بدون out-of-fold strategy.
- scaling train + test معًا.
- time-series transformations تستخدم المستقبل.
- feature selection على كامل البيانات.

واجهة مثل:

```text
Leakage Risk: HIGH
Reason: median was learned from train + test combined.
Suggested fix: fit transformer on training partition only.
```

---

# 13. Cleaning vs Preprocessing Separation

المكتبة يجب أن تميز مفاهيميًا بين:

## Cleaning

إصلاح جودة البيانات نفسها.

مثل:

- duplicates.
- invalid entries.
- inconsistent formats.
- wrong types.
- impossible values.

## Preprocessing

تحويل البيانات لتناسب تحليلًا أو نموذجًا.

مثل:

- scaling.
- encoding.
- transformation.
- feature creation.

### لماذا هذا مهم؟

حتى لا تخلط المكتبة بين:

```text
“هذه القيمة خاطئة”
```

و:

```text
“هذه القيمة صحيحة، لكن النموذج يحتاج تمثيلًا مختلفًا لها”.
```

---

# 14. Architecture المقترحة

```text
smartprep/
│
├── core/
│   ├── project.py
│   ├── dataset.py
│   ├── config.py
│   └── registry.py
│
├── backends/
│   ├── pandas.py
│   ├── polars.py
│   ├── arrow.py
│   ├── ibis.py
│   └── duckdb.py
│
├── profiling/
│   ├── univariate.py
│   ├── bivariate.py
│   ├── missingness.py
│   └── associations.py
│
├── semantic/
│   ├── inference.py
│   ├── validators.py
│   └── ontology.py
│
├── diagnostics/
│   ├── missing.py
│   ├── duplicates.py
│   ├── outliers.py
│   ├── anomalies.py
│   ├── consistency.py
│   ├── leakage.py
│   ├── labels.py
│   └── temporal.py
│
├── cleaning/
│   ├── names.py
│   ├── strings.py
│   ├── types.py
│   ├── missing.py
│   ├── duplicates.py
│   ├── categorical.py
│   ├── datetime.py
│   └── outliers.py
│
├── preprocessing/
│   ├── encoding.py
│   ├── scaling.py
│   ├── transforms.py
│   ├── discretization.py
│   ├── feature_creation.py
│   └── selection.py
│
├── recommend/
│   ├── engine.py
│   ├── rules.py
│   ├── ranking.py
│   └── confidence.py
│
├── evaluation/
│   ├── distribution.py
│   ├── relationships.py
│   ├── downstream.py
│   └── distortion.py
│
├── validation/
│   ├── schema.py
│   ├── rules.py
│   └── contracts.py
│
├── pipeline/
│   ├── node.py
│   ├── graph.py
│   ├── planner.py
│   ├── optimizer.py
│   └── executor.py
│
├── history/
│   ├── versions.py
│   ├── diff.py
│   └── lineage.py
│
├── contexts/
│   ├── ml.py
│   ├── econometrics.py
│   ├── panel.py
│   ├── timeseries.py
│   └── causal.py
│
├── studio/
│   ├── server/
│   └── frontend/
│
├── export/
│   ├── python.py
│   ├── sklearn.py
│   ├── yaml.py
│   ├── html.py
│   └── contracts.py
│
└── cli/
```

---

# 15. Internal Representation: لا تجعل DataFrame هي قلب المشروع

ينبغي وجود object أعلى من DataFrame:

```python
project = SmartProject(df)
```

يحمل:

```text
raw dataset
current dataset
schema
semantic metadata
issues
recommendations
pipeline graph
history
quality scores
context
splits
artifacts
```

هذه النقطة مهمة جدًا لتجنب أن تتحول المكتبة إلى collection of functions.

---

# 16. API المقترحة

## البداية

```python
import smartprep as sp

project = sp.Project(df)
```

## فحص

```python
project.scan()
```

## تقرير

```python
project.report()
```

## المشكلات

```python
project.issues()
```

## التوصيات

```python
project.recommend()
```

## مقارنة الحلول

```python
project.compare(
    issue="missing",
    column="income",
    methods=["median", "knn", "iterative"]
)
```

## التنفيذ

```python
project.apply("REC_018")
```

## الأثر

```python
project.impact()
```

## التاريخ

```python
project.history()
```

## الواجهة

```python
project.studio()
```

## التصدير

```python
project.export_pipeline("cleaning.py")
project.export_report("report.html")
```

---

# 17. Recommendation Engine: التصميم الداخلي

لا تبدأ بـLLM.

ابدأ بمحرك deterministic/heuristic واضح ثم أضف ML/AI لاحقًا.

## المرحلة الأولى

Rules + scoring.

مثال:

```text
IF numeric
AND missing_rate < 0.05
AND strong_skew
THEN median_score += 20
```

## المرحلة الثانية

Simulation-based ranking.

يجرب المرشح على نسخة/عينة ويحسب distortion.

## المرحلة الثالثة

Downstream-aware ranking.

يربط قرار preprocessing بهدف ML/econometrics.

## المرحلة الرابعة

Meta-learning.

تتعلم المكتبة من datasets سابقة ما الطرق التي كانت أنسب.

---

# 18. AI/LLM Layer

الـLLM مفيد لكن يجب ألا يكون execution engine.

Architecture:

```text
User language
    ↓
LLM Planner
    ↓
Structured SmartPrep Plan
    ↓
Policy/Validation layer
    ↓
Deterministic operators
    ↓
Preview
    ↓
User approval / auto-policy
```

أمثلة:

```python
project.ask("جهز البيانات لتحليل panel regression")
```

أو:

```python
project.ask("لماذا لم تحذف الصفوف المفقودة؟")
```

الـLLM يشرح ويقترح، لكن جميع العمليات يجب أن تمر عبر operator registry موثوق.

---

# 19. Privacy & Security

إذا أضيف LLM خارجي:

- default local/no-upload mode.
- لا ترسل raw data تلقائيًا.
- metadata-only prompting افتراضيًا.
- PII detection.
- secrets masking.
- configurable redaction.
- audit of external calls.

---

# 20. Performance Architecture

## Small data

Pandas.

## Medium/large in-memory

Polars/Arrow.

## Analytical pushdown

DuckDB/Ibis.

## Out-of-core/distributed لاحقًا

Dask/Spark.

## Strategy

كل diagnostic يعلن capabilities:

```text
supports_lazy
supports_streaming
requires_full_data
supports_sampling
supports_gpu
```

---

# 21. Lazy Planning + Optimizer

المستخدم يطلب pipeline، لكن التنفيذ لا يبدأ مباشرة.

المخطط:

```text
User requested plan
→ dependency graph
→ optimize order
→ estimate cost
→ execute
```

مثال:

إزالة duplicates قبل خوارزمية anomaly مكلفة قد يوفر وقتًا كبيرًا.

لكن يجب منع إعادة ترتيب عمليات تغيّر semantics.

---

# 22. Cost Estimator

قبل العمليات المكلفة:

```text
Rows: 18,000,000
Operation: KNN Imputation
Estimated memory: High
Estimated time class: Very high
Suggested alternatives:
- sampled parameter estimation
- iterative model-based method
- groupwise median
```

لا حاجة لتقديم وقت دقيق إذا لم يكن التقدير موثوقًا؛ يكفي cost class.

---

# 23. Sampling Intelligence

للتقارير السريعة على البيانات الكبيرة:

- random sample.
- stratified sample.
- time-aware sample.
- rare-category-preserving sample.
- anomaly-preserving sample.

ثم يجب تمييز النتائج:

```text
Exact
Estimated
Sample-based
```

حتى لا يعتقد المستخدم أن كل metric محسوبة على كامل البيانات.

---

# 24. Data Contracts & Quality Gates

بعد الانتهاء من التنظيف:

```python
contract = project.infer_contract()
```

مثلاً:

```yaml
columns:
  quantity:
    type: integer
    min: 0
  status:
    allowed: [paid, pending, cancelled]
  invoice_amount:
    nullable: false
```

ثم:

```python
project.validate(new_df, contract=contract)
```

ويمكن استخدامه في CI/CD.

---

# 25. Drift & Continuous Data Quality

حتى لو كان الإصدار الأول focused on preparation، صمم metadata ليستوعب لاحقًا:

- schema drift.
- category drift.
- missingness drift.
- distribution drift.
- outlier-rate drift.
- quality score drift.

وهكذا تصبح pipeline قابلة للنقل من notebook إلى production monitoring.

---

# 26. Interactive Visualizations الضرورية

لا تحاول إعادة بناء Tableau.

أضف فقط الرسوم التي تساعد قرار cleaning:

- histogram/density.
- boxplot.
- ECDF.
- missing matrix.
- missingness heatmap.
- correlation/association matrix.
- category frequency.
- before/after overlays.
- QQ plots where useful.
- time-gap plot.
- anomaly scatter.
- duplicate clusters.
- pipeline DAG.
- quality score radar/bar.

---

# 27. Notebook UX

يجب أن يعمل المثال الأول بأقل كود:

```python
import smartprep as sp

p = sp.scan(df)
p
```

في Jupyter يمكن أن يكون للobject HTML representation غني.

ثم:

```python
p.studio()
```

يفتح الواجهة الكاملة.

---

# 28. Google Colab يجب أن يكون Target من الإصدار الأول

بسبب انتشار Colab بين الباحثين والطلاب:

- لا تعتمد على فتح localhost browser فقط.
- وفر iframe-compatible mode.
- وفر static HTML report fallback.
- وفر notebook widgets fallback إذا تعذر full app.
- تجنب إعدادات معقدة من نوع tunnels كمسار أساسي.

---

# 29. Export Everywhere

النتيجة النهائية لا تكون DataFrame فقط.

```text
cleaned dataset
pipeline.py
pipeline.yaml
quality_report.html
changes.csv
issues.csv
schema.json
data_contract.yaml
before_after_report.html
```

---

# 30. Plugin System

هذه نقطة مهمة جدًا لتصبح المكتبة Ecosystem.

API:

```python
@sp.register_detector("benford")
def benford_detector(...):
    ...
```

```python
@sp.register_cleaner("custom_currency")
def custom_currency(...):
    ...
```

```python
@sp.register_context("medical")
def medical_context(...):
    ...
```

وبالتالي يمكن للمجتمع إضافة:

- finance.
- economics.
- healthcare.
- survey cleaning.
- geospatial.
- NLP.

---

# 31. Survey Data Module

قيمة إضافية مهمة للباحثين:

- Likert validation.
- reverse-coded item detection assistance.
- impossible questionnaire codes.
- missing response patterns.
- straight-lining indicators.
- duplicate respondents.
- response time anomalies إذا توفرت.
- multi-select normalization.

---

# 32. Finance/Economics Data Module

- currency/unit normalization.
- percent vs decimal ambiguity.
- accounting identity checks.
- negative values where impossible.
- date/frequency integrity.
- panel key validation.
- Benford diagnostic كأداة فحص لا كحكم احتيال.

---

# 33. Schema Evolution

عند دخول Dataset جديدة:

```text
Expected schema v4
Observed schema v5
```

يعرض:

```text
+ new column: region_code
- missing column: legacy_id
~ tax_pct: float → string
~ status: 4 → 6 categories
```

ثم قرار:

```text
Accept schema evolution
Reject batch
Quarantine
Adapt pipeline
```

---

# 34. Quarantine بدل الحذف

ميزة مهمة جدًا.

بدل:

```python
df = df.drop(...)
```

يصبح:

```text
main dataset
quarantined rows
reasons
```

مثلاً:

```python
clean, quarantine = project.apply(..., policy="quarantine")
```

وهذا أفضل للحوكمة والتدقيق.

---

# 35. Cell-level Lineage

في الإصدار المتقدم يمكن معرفة:

```text
Cell B128
Original: "1,200 DZD"
Parsed: 1200.0
Unit: DZD
Operator: parse_currency
Rule: currency_parser_v2
```

هذه ميزة قوية في البيانات الحساسة والتنظيف المعقد.

---

# 36. Confidence Calibration

الثقة يجب ألا تكون رقمًا شكليًا.

تحتاج:

- calibration benchmarks.
- labeled dirty-data datasets.
- synthetic corruption tests.
- human review feedback.

الهدف:

```text
95% confidence
```

يكون له معنى إحصائي معقول قدر الإمكان.

---

# 37. Synthetic Corruption Benchmark

لبناء سمعة علمية للمكتبة، أنشئ benchmark framework يفسد بيانات نظيفة عمدًا:

- inject missingness.
- swap types.
- spelling noise.
- duplicate rows.
- near duplicates.
- category corruption.
- numeric outliers.
- date corruption.
- label noise.

ثم تقيس:

```text
Detection precision
Detection recall
Repair accuracy
Distribution distortion
Runtime
Memory
```

---

# 38. Benchmark ضد المنافسين

يجب أن تكون المقارنة عادلة ومقسمة حسب المهمة.

## Profiling

مقارنة مع YData Profiling وغيرها.

## Cleaning API

مع PyJanitor/DataPrep.Clean.

## Validation

مع Pandera/GX/Soda.

## Preprocessing

مع sklearn/Feature-engine.

## Interactive

مع PyGWalker/D-Tale.

ولا تدّعِ “أفضل من الجميع” على كل المقاييس؛ الهدف أن تكون **أفضل تجربة متكاملة**.

---

# 39. Matrix المقارنة المستهدفة

| Capability | YData | PyGWalker | D-Tale | PyJanitor | Pandera | Feature-engine | SmartPrep Target |
|---|---:|---:|---:|---:|---:|---:|---:|
| Profiling | قوي | متوسط | متوسط | ضعيف | محدود | محدود | قوي جدًا |
| Interactive UI | تقرير | قوي جدًا | قوي | لا | لا | لا | قوي جدًا |
| Cleaning actions | محدود | محدود/ثانوي | متوسط | قوي | validation | transformations | قوي جدًا |
| Preprocessing | محدود | محدود | محدود | جزئي | لا | قوي جدًا | قوي جدًا |
| Recommendation engine | محدود | لا | لا | لا | لا | لا | **أساسي** |
| Explain decisions | alerts | لا | لا | لا | errors | docs | **أساسي** |
| Treatment comparison | لا | لا | لا | لا | لا | لا | **أساسي** |
| Before/after impact | محدود | visualization | محدود | لا | validation | لا | **أساسي** |
| Undo/version graph | لا | state | محدود | لا | لا | لا | **أساسي** |
| Data contracts | لا | لا | لا | لا | schema | لا | نعم |
| Multi-backend | محدود | موجود جزئيًا | pandas-centric | pandas/بعض polars | قوي | pandas/sklearn | قوي |
| Econometrics context | لا | لا | لا | لا | لا | لا | **ميزة خاصة** |
| Leakage guard | لا | لا | لا | لا | لا | pipeline dependent | **أساسي** |
| Export UI→pipeline | جزئي | بعض الإمكانات | بعض الإمكانات | code already | schema | code | **كامل** |

> الجدول يمثل **الهدف التصميمي** للمشروع وليس ادعاءً بأن جميع الأعمدة تعكس كل ميزة ممكنة في كل إصدار من الأدوات المنافسة.

---

# 40. MVP الصحيح

أكبر خطأ هو محاولة بناء كل شيء في v0.1.

## الإصدار 0.1 — Core Intelligence

ابنِ:

1. Project object.
2. Pandas backend.
3. basic profiling.
4. semantic inference الأساسية.
5. issue model.
6. missingness diagnostics.
7. duplicates.
8. type problems.
9. simple outliers.
10. rule engine.
11. recommendations.
12. preview.
13. apply.
14. history/undo.
15. before-after report.
16. export Python pipeline.

هذه هي النواة التي تثبت الفكرة.

---

# 41. الإصدار 0.2 — Interactive Studio

- virtualized data grid.
- health dashboard.
- column inspector.
- issue inbox.
- missing lab.
- duplicates lab.
- outlier lab.
- pipeline timeline.
- before/after compare.
- notebook integration.

---

# 42. الإصدار 0.3 — Preprocessing Intelligence

- encoding.
- scaling.
- transformations.
- discretization.
- feature creation.
- sklearn export.
- leakage guard.
- target-aware recommendations.

---

# 43. الإصدار 0.4 — Multi-backend

- Polars.
- Arrow.
- DuckDB/Ibis.
- Narwhals abstraction إن كان مناسبًا معماريًا.
- lazy execution.
- sampling/cost estimation.

---

# 44. الإصدار 0.5 — Domain Intelligence

- time-series.
- panel data.
- econometrics.
- survey data.
- finance.

---

# 45. الإصدار 0.6 — Production Quality

- data contracts.
- CI validation.
- schema evolution.
- drift snapshots.
- quality gates.
- lineage export.

---

# 46. الإصدار 0.7 — AI Assistant

- natural-language planner.
- explainability assistant.
- interactive “ask your data quality” interface.
- metadata-first prompting.
- policy-controlled execution.

---

# 47. Frontend Technology Options

## الخيار A: React + Python backend

الأقوى لمنتج طويل الأجل.

مزايا:

- data grid ممتاز.
- DAG builder.
- responsive UI.
- إمكانية component architecture كبيرة.

عيب:

- فريق/جهد frontend أكبر.

## الخيار B: AnyWidget/Jupyter widgets + React

مناسب لتجربة notebook أصلية.

## الخيار C: Panel/Plotly/Dash

أسرع MVP لكنه قد يقيّد تجربة UI المتقدمة.

### الاقتراح

ابدأ UI صغيرة بـPython-friendly stack، لكن صمم protocol يفصل frontend عن core حتى يمكن الانتقال إلى React كامل لاحقًا.

---

# 48. API Stability

من أول يوم:

- semantic versioning.
- deprecation policy.
- stable core public API.
- experimental namespace.

مثلاً:

```python
smartprep.experimental.ai
```

بدل كسر core كل إصدار.

---

# 49. Testing Strategy

## Unit tests

لكل operator.

## Property-based tests

مفيدة جدًا في parsers وschemas.

## Golden datasets

Dirty datasets مع expected repairs.

## Regression tests

لمنع تغير النتائج دون قصد.

## Backend parity tests

نفس العملية على Pandas/Polars ينبغي أن تعطي semantic result متقاربًا.

## UI e2e tests

workflow كامل:

```text
load → diagnose → preview → apply → undo → export
```

---

# 50. Documentation Strategy

المكتبة لن تنجح بوظائف كثيرة فقط.

يجب وجود:

- Quickstart.
- concepts.
- cleaning vs preprocessing.
- issue taxonomy.
- recommendation methodology.
- algorithms.
- API reference.
- UI guide.
- cookbook.
- econometrics examples.
- ML examples.
- Colab examples.
- benchmarks.

---

# 51. Explainability Documentation

لكل detector/repairer صفحة:

```text
What it detects
Assumptions
When it works
When not to use it
Parameters
Computational complexity
Potential side effects
How recommendation score is computed
References
```

هذه ستعطي المكتبة طابعًا علميًا قويًا.

---

# 52. عدم استخدام كلمة Auto بطريقة مضللة

لا تقل:

```text
Automatically makes your data correct.
```

الأفضل:

```text
Automates diagnosis and low-risk repairs while keeping ambiguous decisions reviewable and reproducible.
```

لأن “الصحيح” يعتمد غالبًا على domain knowledge.

---

# 53. فلسفة المنتج

أقترح خمس مبادئ رسمية:

## Principle 1 — Never mutate silently

لا تغيير غير موثق.

## Principle 2 — Diagnose before repair

لا معالجة قبل فهم المشكلة.

## Principle 3 — Preserve evidence

احتفظ بالأصل والتاريخ.

## Principle 4 — Prefer explainable recommendations

التوصية لها سبب ودرجة ثقة.

## Principle 5 — Reproducibility over clicks

أي UI action يتحول إلى pipeline.

---

# 54. Killer Features التي أنصح بإبرازها

إذا أردنا 10 خصائص تسويقية/تقنية فريدة نسبيًا:

1. **Treatment Recommendation Engine**.
2. **Counterfactual Cleaning Lab**.
3. **Before/After Statistical Distortion Analysis**.
4. **Explainable Cleaning Decisions**.
5. **Human-in-the-loop Auto Mode**.
6. **Data Preparation Studio**.
7. **Reversible Version Graph**.
8. **Context-aware ML/Econometrics/Time-Series preparation**.
9. **Leakage Guard**.
10. **UI-to-Reproducible-Pipeline export**.

---

# 55. الخصائص التي يمكن أن تصنع ورقة بحثية

المشروع يمكن ألا يكون Software فقط، بل بحثًا علميًا.

أفكار قابلة للنشر:

- Automated Treatment Selection for Data Cleaning.
- Statistical Distortion Metrics for Data Repair.
- Explainable Data Cleaning Recommendation Systems.
- Context-aware Data Preparation for Econometrics and ML.
- Meta-learning for preprocessing selection.
- Counterfactual evaluation of imputation/outlier strategies.

---

# 56. Data Preservation Score

يمكن تطوير metric مركب لكن يجب أن يكون decomposable.

مثلاً:

```text
Marginal distribution preservation
Relationship preservation
Rank preservation
Variance preservation
Target relationship preservation
```

ثم:

```text
Preservation Score = weighted aggregation
```

والأوزان تعتمد على context.

هذا يحتاج بحثًا وليس مجرد formula اعتباطية.

---

# 57. Decision Cards

في الواجهة كل recommendation تظهر بطاقة موحدة:

```text
Issue
Suggested action
Why
Confidence
Affected data
Expected benefit
Potential harm
Alternatives
Preview
Compare
Apply
Dismiss
```

هذه يمكن أن تصبح signature UX للمكتبة.

---

# 58. Issue Inbox

بدل صفحة ضخمة من warnings:

```text
Critical (3)
High (7)
Medium (18)
Low (29)
Info (14)
```

يمكن الفرز حسب:

- severity.
- confidence.
- column.
- issue type.
- impact.
- cost.

---

# 59. Smart Defaults مع Policy Profiles

```python
project.use_policy("research_conservative")
project.use_policy("ml_fast")
project.use_policy("production_strict")
```

### research_conservative

قليل من التعديلات التلقائية، حفظ أكبر للأصل.

### ml_fast

preprocessing سريع مع leakage protection.

### production_strict

schema/contract enforcement قوي.

---

# 60. Localized UI

ميزة إضافية للمستخدمين غير الناطقين بالإنجليزية:

- English first.
- Arabic localization مبكرًا.
- French لاحقًا.

لكن identifiers/code يبقون إنجليزيين.

هذه يمكن أن توسع قاعدة المستخدمين في التعليم والبحث.

---

# 61. ماذا لا نبني في البداية؟

لا نبنِ:

- BI dashboard شامل.
- AutoML كامل.
- database ETL platform كامل.
- notebook replacement.
- data catalog enterprise.
- full NLP cleaning suite.
- Spark engine خاص بنا.

نربطها أو نؤجلها.

---

# 62. Build vs Integrate

قاعدة مهمة:

## Build

- issue model.
- recommendation engine.
- impact engine.
- history/versioning.
- studio workflows.
- context intelligence.

## Reuse/Integrate

- pandas/polars operations.
- sklearn transformers.
- statistical tests.
- plotting libraries.
- Arrow interchange.

بهذا تُصرف الجهود على الابتكار الحقيقي.

---

# 63. License Strategy

قبل تثبيت dependencies أو نسخ أي code:

- راجع تراخيص كل مشروع.
- لا تنسخ implementation لمجرد أنه open source.
- استلهم concepts وأعد التنفيذ إذا لزم.
- احتفظ attribution عند استخدام code/derivatives حسب الترخيص.

يمكن أن تكون النواة Apache-2.0 أو BSD-3-Clause أو MIT بحسب أهداف المشروع، لكن القرار يحتاج دراسة ecosystem/commercial strategy.

---

# 64. Telemetry

افتراضيًا:

```text
No telemetry without explicit opt-in.
```

خصوصًا لأن المكتبة تتعامل مع بيانات قد تكون حساسة.

---

# 65. Roadmap تنفيذ عملي لمدة مراحل

## المرحلة 1 — Research & Specification

- freeze terminology.
- define issue taxonomy.
- define operator interface.
- define project state model.
- define recommendation object.
- define audit schema.
- competitor benchmark datasets.

## المرحلة 2 — Core Engine

- Project.
- Data adapter.
- issue registry.
- operators.
- history.
- preview.

## المرحلة 3 — Diagnostics

- types.
- missing.
- duplicates.
- categorical quality.
- outliers.
- cross-column rules.

## المرحلة 4 — Recommendation

- rule-based ranking.
- treatment simulator.
- impact metrics.

## المرحلة 5 — Studio MVP

- grid.
- dashboard.
- issue inbox.
- decision cards.
- before/after.

## المرحلة 6 — Preprocessing

- sklearn compatible transformer layer.
- leakage protection.
- export.

## المرحلة 7 — Multi-backend

- Polars.
- Arrow/Narwhals-like abstraction.
- DuckDB/Ibis.

## المرحلة 8 — Scientific contexts

- time series.
- panel/econometrics.
- survey.

## المرحلة 9 — Production

- contracts.
- CI.
- schema evolution.
- drift snapshots.

## المرحلة 10 — AI layer

- language planner.
- explanations.
- recommendation augmentation.

---

# 66. أول Prototype يجب أن يثبت 4 أشياء فقط

أول Demo قوي لا يحتاج 100 وظيفة.

خذ dataset فيها:

- mixed types.
- missing values.
- duplicates.
- inconsistent categories.
- outliers.

ثم اجعل المستخدم يشاهد:

1. `scan()` يكتشف المشكلات.
2. `recommend()` يقترح حلولًا مع أسباب.
3. Studio يقارن حلين أو ثلاثة قبل التطبيق.
4. `export_pipeline()` يولد كودًا قابلًا لإعادة الإنتاج.

إذا نجحت هذه القصة، ففكرة المنتج مثبتة.

---

# 67. مثال تجربة مستخدم نهائية

```python
import smartprep as sp
import pandas as pd

df = pd.read_excel("data.xlsx")

p = sp.Project(df)
p.scan()
p.studio()
```

داخل Studio يرى:

```text
23 issues detected
5 high priority
```

ينقر على:

```text
annual_revenue — 8.4% missing
```

فيظهر:

```text
Suggested:
1. Group median     92/100
2. Iterative        88/100
3. KNN              82/100
4. Global median    71/100
5. Drop rows        31/100
```

ينقر Compare فيرى الأثر.

ثم Apply.

ثم:

```python
p.export_pipeline("prep_pipeline.py")
p.export_report("data_quality_report.html")
```

هذه هي القصة التي يجب أن يبنى عليها المنتج.

---

# 68. معيار النجاح الحقيقي

المكتبة ليست ناجحة لأنها تحتوي 300 function.

تنجح إذا استطاع مستخدم أن يجيب بسرعة وبثقة عن:

```text
ما مشاكل بياناتي؟
أيها مهم؟
ماذا أفعل؟
لماذا؟
ما البدائل؟
ماذا سيحدث لو طبقت الحل؟
هل يمكن الرجوع؟
هل أستطيع إعادة العملية غدًا على بيانات جديدة؟
```

---

# 69. الخلاصة الاستراتيجية

أفضل اتجاه ليس بناء “مكتبة تنظيف أكبر”.

بل بناء **نظام قرار للتحضير الذكي للبيانات**.

المعادلة المقترحة:

```text
YData-style profiling
+ PyGWalker/D-Tale-style interactivity
+ PyJanitor/DataPrep-style cleaning
+ Pandera/GX/Soda-style validation and contracts
+ sklearn/Feature-engine-style preprocessing pipelines
+ Cleanlab-style ML data auditing
+
Recommendation Intelligence
+ Explainability
+ Counterfactual Comparison
+ Impact Measurement
+ Versioning/Undo
+ Context Awareness
+ Leakage Protection
+ Econometrics/Panel/Time-series intelligence
```

الناتج ليس wrapper لهذه المكتبات، بل architecture جديدة تستخدم أفضل الأفكار الموجودة ثم تضيف طبقة لم تعالجها معظم الأدوات بصورة متكاملة:

> **تشخيص المشكلة واختيار المعالجة المناسبة وقياس أثر القرار وتوثيقه وإعادة إنتاجه داخل تجربة تفاعلية واحدة.**

وهذه، في رأيي، هي أقوى قيمة مضافة يمكن أن تجعل المشروع جديرًا بأن يصبح مكتبة معروفة بدل أن يكون مجرد بديل آخر لأدوات cleaning التقليدية.

---

# 70. تدقيق التغطية التنافسية: هل أخذنا فعلًا "أفضل فكرة من كل بستان"؟

هذا القسم هو **تدقيق إلزامي** للخطة السابقة. الهدف ليس مجرد ذكر أسماء المكتبات المنافسة، بل تحويل أفضل أفكارها إلى **متطلبات Product Requirements صريحة** داخل المكتبة الجديدة.

> المبدأ: أي قدرة مهمة أثبتت فائدتها في مكتبة معروفة يجب أن يكون لها أحد ثلاثة أوضاع لدينا: **Parity** (ندعمها على الأقل)، **Better** (ندعمها بصورة أفضل)، أو **Replace** (نقدم بديلًا أكثر ذكاءً يجعل الشكل القديم غير ضروري).

ولا يمكن علميًا الادعاء بمراجعة "كل مكتبات Python الموجودة" حرفيًا لأن PyPI وGitHub منظومة مفتوحة تتغير باستمرار. لذلك يعتمد المشروع معيارًا أقوى وقابلًا للتحديث:

1. تغطية كل **الفئات الوظيفية** الأساسية في Data Preparation.
2. مراجعة أشهر وأقوى الأدوات التمثيلية في كل فئة.
3. استخراج كل **Feature Pattern** مهم، لا مجرد اسم المكتبة.
4. بناء **Competitor Feature Registry** داخل وثائق المشروع وتحديثه دوريًا.
5. عدم اعتبار أي ميزة "مكتملة" حتى نحدد كيف نتفوق عليها في UX أو الذكاء أو الأداء أو التفسير أو قابلية إعادة الإنتاج.

---

## 70.1 خريطة الفئات التي يجب أن تغطيها المكتبة

ينبغي أن تتعامل المكتبة الجديدة مع Data Preparation كمنظومة واحدة تشمل:

- Data ingestion and format detection
- Data profiling
- Data summarization
- Interactive EDA
- Data quality alerts
- Missing-data diagnostics
- Missing-data visualization
- Missing-value imputation
- Duplicate detection
- Near-duplicate/entity resolution
- Type inference
- Semantic type inference
- Data validation
- Schema management
- Data contracts
- Data cleaning
- String cleaning
- Datetime cleaning
- Category normalization
- Outlier detection
- Anomaly detection
- Scaling and normalization
- Distribution transformations
- Categorical encoding
- High-cardinality encoding
- Text/string encoding
- Class-imbalance handling
- Feature engineering
- Feature selection
- Leakage protection
- Pipeline construction
- Pipeline comparison
- Train/test-aware preprocessing
- Dataset comparison
- Drift detection
- Continuous data-quality monitoring
- Privacy/PII detection
- Versioning and lineage
- Interactive editing
- Code generation
- Report generation
- Multi-backend execution
- Large-data execution
- Domain-aware preparation
- Explainability
- Recommendation intelligence
- Impact evaluation

إذا بقيت واحدة من هذه الفئات خارج التصميم، فالمكتبة ليست بعد Superset حقيقيًا لأدوات Data Preparation الحديثة.

---

# 71. Feature Inheritance Matrix — ماذا نأخذ من المكتبات الحالية وكيف نتفوق عليها؟

## 71.1 YData Profiling

### أفكار يجب أن نرثها

- تقرير شامل بضغطة واحدة.
- Univariate profiling لكل عمود.
- descriptive statistics.
- histograms/distributions.
- missing-value analysis.
- duplicate preview.
- correlations متعددة المقاييس.
- interactions بين المتغيرات.
- automatic data-quality alerts.
- high-cardinality warnings.
- constant/zero column warnings.
- time-series profiling.
- إمكانية minimal mode للبيانات الكبيرة.
- Configuration-driven profiling.
- HTML export.

### كيف نتفوق؟

بدل أن يكون Alert نهاية العملية، يصبح بداية Decision Workflow:

```text
Alert
→ evidence
→ severity
→ likely cause
→ treatment candidates
→ expected impact
→ preview
→ compare alternatives
→ apply
→ validate
→ audit trail
```

ويضاف:

- explainable severity score.
- confidence score.
- domain-aware interpretation.
- recommended treatment.
- counterfactual comparison.
- automatic pipeline generation.
- before/after distribution preservation.
- interactive issue resolution.

---

## 71.2 Sweetviz

Sweetviz يقدم عدة أفكار ممتازة يجب ألا تضيع من المشروع.

### أفكار يجب أن نرثها

- beautiful self-contained HTML report.
- high-density visual summaries.
- Target Analysis.
- Dataset-to-dataset comparison.
- Train-vs-test comparison.
- Subpopulation comparison داخل نفس Dataset.
- type inference مع manual override.
- feature-by-feature detail view.
- mixed-type associations.
- numerical-numerical association.
- categorical-categorical association.
- categorical-numerical association.
- highlighting relationship with the target.
- notebook embedding.
- report layout customization.

### كيف نتفوق؟

نضيف مفهوم:

## Smart Comparison Lab

ليس فقط:

```text
Dataset A vs Dataset B
```

بل:

```text
Raw vs Cleaned
Train vs Validation vs Test
Before vs After Imputation
Before vs After Encoding
Group A vs Group B
Time Window A vs Time Window B
Version 4 vs Version 7
```

ويعرض لكل اختلاف:

- statistical significance.
- effect size.
- distribution divergence.
- category changes.
- missingness change.
- correlation change.
- target relationship change.
- downstream model effect.

### قيمة إضافية

Sweetviz ممتاز في **الرؤية**؛ المكتبة الجديدة يجب أن تجعل المقارنة **Actionable**.

---

## 71.3 PyGWalker

### أفكار يجب أن نرثها

- interactive data exploration.
- drag-and-drop visual analytics.
- notebook-first experience.
- visual chart construction.
- filtering.
- visual exploration without كتابة كود طويل.
- integration مع dataframe engines الحديثة.
- interactive table experience.
- state-to-code / reproducibility mindset.

### كيف نتفوق في مجال Data Preparation؟

لا نحاول فقط صنع chart builder أكبر. نبني:

## Interactive Preparation Canvas

المستخدم يستطيع سحب Column إلى:

- Missing Lab
- Outlier Lab
- Encoding Lab
- Scaling Lab
- Type Repair
- Duplicate Key Builder
- Rule Builder
- Transformation Lab

ثم يرى فورًا:

```text
Original
Preview
Impact
Risk
Recommendation
Reversibility
```

### ميزة أقوى من PyGWalker في هذا السياق

كل interaction يجب أن ينتج في نفس اللحظة:

1. visual state.
2. deterministic operation object.
3. Python code.
4. pipeline node.
5. audit entry.
6. reversible version.

وبذلك لا تكون الواجهة مجرد أداة استكشاف، بل **Visual Data Preparation IDE**.

---

## 71.4 D-Tale

D-Tale من أهم المصادر التي يجب استلهام UX منها.

### أفكار يجب أن نرثها

- spreadsheet-like Data Grid.
- direct cell editing.
- column filtering.
- sorting.
- moving/hiding/locking columns.
- rename/delete/replace.
- column formatting.
- dataframe functions.
- merge/stack.
- duplicates UI.
- missing-data analysis.
- missingno-style visualizations.
- outlier highlighting.
- correlations.
- Predictive Power Score.
- low-variance flags.
- chart builder.
- geospatial views.
- code export.
- CSV/TSV export.
- loading data from UI.
- keyboard shortcuts.
- column analysis panel.

### كيف نتفوق؟

D-Tale يسمح بالتعديل؛ مكتبتنا يجب أن تضيف **Decision Safety Layer**:

قبل التعديل:

- preview affected rows.
- estimate information loss.
- check rule violations.
- check leakage.
- estimate distribution distortion.

بعد التعديل:

- validation.
- change summary.
- undo.
- lineage.
- generated pipeline code.

### إضافة نوعية

أي تعديل يدوي على خلية يمكن تحويله إلى **Pattern Suggestion**:

```text
لاحظنا أنك أصلحت "Alger" إلى "Algiers" في 7 صفوف متشابهة.
هل تريد إنشاء normalization rule؟
```

هذه ميزة قوية جدًا لا تتوفر عادة في spreadsheet-style EDA tools.

---

## 71.5 DataProfiler — Capital One

### أفكار يجب أن نرثها

- automatic file-type detection.
- CSV/JSON/Avro/Parquet/Text ingestion.
- structured profiling.
- unstructured text profiling.
- graph profiling concept.
- schema extraction.
- column-level statistics.
- global statistics.
- per-cell semantic/data labels.
- PII/sensitive-data detection.
- deep-learning-based entity labeling.
- null type identification.
- precision statistics.
- profile update with new batches.
- mergeable profiles.
- distributed-profile mindset.

### كيف نتفوق؟

نضيف:

## Semantic + Policy Layer

مثلاً إذا اكتشف:

```text
EMAIL
PHONE
CREDIT_CARD
PERSON
```

لا نكتفي بالتسمية، بل نقدم:

- privacy risk.
- masking suggestion.
- hashing/tokenization suggestion.
- whether field may be used as ML feature.
- whether export should be blocked.
- whether report screenshots should redact values.
- configurable policy profiles مثل GDPR/Research/Public Release.

### قيمة إضافية

ندمج semantic type detection مع cleaning. مثال:

```text
Semantic type = phone number
```

يؤدي تلقائيًا إلى:

- country-code parsing.
- whitespace/punctuation normalization.
- length validation.
- invalid-number quarantine.
- duplicate-contact detection.

---

## 71.6 Skimpy

### أفكار يجب أن نرثها

- extremely simple summary UX.
- compact dataframe overview.
- fast column cleaning helpers.
- readable terminal/notebook output.

### كيف نتفوق؟

نوفر مستويين دائمًا:

```text
Quick Scan
Deep Scan
```

بحيث يحصل المبتدئ على ملخص سريع، والخبير يستطيع فتح الأدلة الإحصائية والـdiagnostics المتقدمة.

---

## 71.7 Missingno

### أفكار يجب أن نرثها

- missingness matrix.
- missingness bar chart.
- missingness heatmap.
- dendrogram of missingness relationships.

### كيف نتفوق؟

تحويل الرسم إلى **Missingness Intelligence Lab** يضيف:

- row/column missingness clusters.
- co-missingness graph.
- monotone missingness detection.
- time-dependent missingness.
- group-dependent missingness.
- target-dependent missingness warnings.
- candidate MCAR/MAR/MNAR evidence.
- suggested imputation families.
- imputation sensitivity comparison.

---

## 71.8 AutoViz / automatic visualization tools

### أفكار يجب أن نرثها

- automatic chart selection.
- low-code/one-command visualization.
- automatic handling based on variable types.
- fast overview suitable for beginners.

### كيف نتفوق؟

الرسوم لا تختار فقط حسب dtype، بل حسب **issue context**:

```text
Missing problem → missingness view
Outlier problem → robust distribution + influence view
Rare category → frequency tail view
Time gap → temporal continuity view
Encoding decision → cardinality/target-risk view
```

أي أن Visualization Engine يكون **diagnostic-driven** وليس مجرد chart recommender.

---

## 71.9 PandasGUI / spreadsheet-oriented interactive tools

### أفكار يجب أن نرثها

- table browsing.
- filtering.
- editing.
- visual plotting.
- quick reshaping/exploration.

### كيف نتفوق؟

كل تعديل يصبح reproducible operation بدل أن يكون تعديلًا غير موثق في واجهة فقط.

---

## 71.10 PyJanitor

### أفكار يجب أن نرثها

- expressive method-chaining API.
- clean_names.
- remove_empty.
- conditional transformations.
- coalesce.
- reshape helpers.
- convenient joins.
- finance/biology/date utilities عند الحاجة.
- fluent dataframe-cleaning style.

### كيف نتفوق؟

نحافظ على API بسيط جدًا:

```python
project.clean.names()
project.clean.strings()
project.clean.categories()
```

لكن كل operation يمتلك metadata:

```text
reason
confidence
rows affected
reversibility
impact
audit id
```

أي نأخذ **سهولة PyJanitor** ونضيف **ذكاء + lineage + safety**.

---

## 71.11 DataPrep.Clean

### أفكار يجب أن نرثها

- domain-specific cleaning functions.
- cleaning للـemails.
- phone numbers.
- countries.
- addresses.
- dates.
- URLs.
- text normalization.
- standardized outputs.
- report-oriented cleaning workflow.

### كيف نتفوق؟

Semantic detection يقترح cleaner تلقائيًا، ثم يقيس نجاحه.

مثلاً:

```text
98.7% parsed successfully
0.8% ambiguous
0.5% invalid
```

مع quarantine للـambiguous/invalid بدل إسقاطها.

---

## 71.12 Pandera — خصوصًا Pandera + Polars

### أفكار يجب أن نرثها

- DataFrameSchema.
- DataFrameModel.
- column checks.
- dataframe-wide checks.
- strict schemas.
- dtype coercion.
- unique constraints.
- duplicate reporting.
- add missing columns.
- drop invalid rows option.
- lazy validation لجمع جميع الأخطاء.
- schema serialization.
- validation لعدة backends.
- Polars DataFrame/LazyFrame support.
- الاستفادة من Polars lazy execution.
- Pandas/Polars/Ibis/PyArrow/PySpark orientation.
- Narwhals/interoperability idea.
- parser-before-validation concept.

### كيف نتفوق؟

نضيف:

## Schema Discovery + Repair Assistant

المستخدم لا يضطر لكتابة schema من الصفر.

```python
schema = project.infer_schema()
```

ثم تعرض المكتبة:

```text
Observed rule
Confidence
Evidence
Suggested contract
Risk of enforcing it
```

ثم:

```python
project.schema.accept(...)
```

### قيمة مضافة على Polars integration

يجب أن يكون planner واعيًا بما يمكن تنفيذه Lazy وما يتطلب materialization، مع Cost Estimate قبل `collect()`.

---

## 71.13 Great Expectations

### أفكار يجب أن نرثها

- declarative expectations.
- reusable validation suites.
- validation results.
- checkpoints.
- human-readable data documentation.
- batch-oriented validation.
- production quality gates.

### كيف نتفوق؟

نربط expectation بالفشل والعلاج:

```text
Expectation failed
→ root-cause clues
→ affected records
→ repair candidates
→ safe auto-fix eligibility
→ post-fix validation
```

أي ننتقل من **test data** إلى **diagnose + repair + retest**.

---

## 71.14 Soda

### أفكار يجب أن نرثها

- data quality checks.
- contracts.
- freshness/completeness/validity concepts.
- production monitoring mindset.
- CI/CD-friendly quality gates.

### كيف نتفوق؟

نسمح بتحويل أي interactive cleaning session إلى Data Contract مستقبلية:

```text
Learned rule → proposed contract → user approval → production check
```

---

## 71.15 Scikit-learn Preprocessing

هذه طبقة يجب ألا ينقص منها شيء أساسي.

### يجب تغطية

- StandardScaler.
- MinMaxScaler.
- MaxAbsScaler.
- RobustScaler.
- Normalizer.
- PowerTransformer.
- QuantileTransformer.
- polynomial transformations عند الحاجة.
- OneHotEncoder.
- OrdinalEncoder.
- SimpleImputer.
- KNNImputer.
- IterativeImputer.
- MissingIndicator.
- discretization/binning.
- ColumnTransformer philosophy.
- Pipeline compatibility.
- fit/transform separation.
- feature-name propagation.
- output as pandas/polars where appropriate.

### كيف نتفوق؟

لا نعرض 15 transformer فقط؛ نجيب:

```text
أي Transformer يناسب هذا العمود وهذه المهمة؟ ولماذا؟
```

ونضيف **Leakage Guard** يمنع fit على كامل dataset عند وجود train/test context.

---

## 71.16 Feature-engine

### أفكار يجب أن نرثها

- broad sklearn-compatible transformers.
- mean/median imputation.
- arbitrary-value imputation.
- end-tail imputation.
- random-sample imputation.
- missing indicators.
- categorical imputation.
- rare-label encoding.
- count/frequency encoding.
- ordinal encoding.
- target-based encodings.
- discretization.
- mathematical transformations.
- Box-Cox / Yeo-Johnson style transforms.
- winsorization/outlier capping.
- feature selection.
- variable creation.

### كيف نتفوق؟

Treatment Comparison Engine يقارن هذه البدائل وفق:

- distortion.
- downstream CV score.
- stability.
- leakage risk.
- interpretability.
- runtime.

---

## 71.17 Category Encoders

هذه المكتبة مهمة جدًا ويجب ألا يغيب تنوعها.

### يجب تغطية أو التكامل مع أفكار

- One-hot.
- Ordinal.
- Binary.
- Base-N.
- Hashing.
- Count/Frequency.
- Target Encoding.
- Leave-One-Out.
- CatBoost Encoding.
- James-Stein.
- M-estimate.
- GLMM encoding.
- Weight of Evidence.
- Helmert/Sum/Polynomial contrasts.
- handling unknown categories.
- handling missing categories.
- drop invariant columns.
- sklearn pipeline compatibility.

### كيف نتفوق؟

## Encoding Advisor

يأخذ في الاعتبار:

- cardinality.
- sample size.
- target type.
- leakage risk.
- time order.
- model family.
- interpretability requirement.
- memory expansion.
- unknown-category probability.

ثم يصنف الطرق.

مثال:

```text
One-hot         42/100  memory explosion risk
Target          84/100  requires CV encoding
CatBoost        91/100  suitable for ordered/time-aware context
Hashing         75/100  compact but less interpretable
```

---

## 71.18 Skrub / dirty-data preprocessing

Skrub مهم لأنه يعالج "dirty tables" وليس فقط categorical data نظيفة.

### أفكار يجب أن نرثها

- TableVectorizer-style automatic column routing.
- parsing numeric values stored as strings.
- parsing dates.
- missing marker normalization.
- low- vs high-cardinality detection.
- high-cardinality string encoding.
- MinHashEncoder concept.
- GapEncoder/topic-like representation.
- SimilarityEncoder/fuzzy categories.
- text encoders.
- DatetimeEncoder.
- join/enrichment helpers.
- table report.
- column association measures.
- automatic tabular pipeline concept.

### كيف نتفوق؟

نضيف **Dirty Category Resolution Lab** قبل encoding:

```text
"Alger"
"alger"
"ALGER"
"Algiers"
"Algeria - Alger"
```

المكتبة تقترح:

- normalize only.
- fuzzy merge.
- embedding merge.
- external dictionary mapping.
- preserve as distinct.

ثم توضح confidence لكل merge.

هذه الخطوة يجب أن تسبق encoding بدل تشفير الأخطاء نفسها.

---

## 71.19 Imbalanced-learn

رغم أنها ليست Cleaning Library تقليدية، فهي جزء مهم من ML preprocessing.

### أفكار يجب أن نرثها

- random over-sampling.
- random under-sampling.
- SMOTE families.
- SMOTENC/SMOTEN.
- ADASYN.
- Borderline/KMeans/SVM SMOTE variants.
- Tomek links.
- Edited Nearest Neighbours.
- SMOTEENN.
- SMOTETomek.
- sampling-aware Pipeline.
- metrics for imbalanced learning.

### كيف نتفوق؟

## Imbalance Advisor

قبل resampling يجب تحليل:

- severity of imbalance.
- class overlap.
- minority sample size.
- categorical vs numeric features.
- time dependence.
- grouped/panel structure.
- leakage risk.

ولا يسمح تلقائيًا بـSMOTE في time-series أو panel context دون تحذير صريح.

---

## 71.20 MICE / FancyImpute / advanced imputation ecosystem

### أفكار يجب تغطيتها

- KNN imputation.
- iterative/chained-equation imputation.
- multiple imputation.
- model-based imputation.
- random forest / boosting-based imputation where appropriate.
- matrix completion approaches.
- uncertainty across multiple imputations.

### القيمة الجديدة

## Imputation Evaluation Lab

لا نختار الطريقة فقط بناء على RMSE مصطنع.

نقيس:

- reconstruction error عبر masking experiments.
- distribution preservation.
- covariance preservation.
- regression coefficient stability.
- uncertainty.
- subgroup fairness.
- time-series continuity.

---

## 71.21 PyOD / anomaly-detection ecosystem

### أفكار يجب أن نرثها

- multiple outlier detectors.
- distance-based methods.
- density-based methods.
- isolation methods.
- probabilistic/statistical methods.
- ensemble outlier detection.
- anomaly score instead of binary-only decision.

### كيف نتفوق؟

نميز صراحة بين:

```text
Data Error
Rare-but-valid Observation
Statistical Outlier
Contextual Anomaly
Model Influential Point
Fraud-like Pattern
```

ولا نسمح بكلمة `remove_outliers()` كحل افتراضي.

---

## 71.22 Cleanlab Datalab

### أفكار يجب أن نرثها

- data-centric AI philosophy.
- label issue detection.
- outlier issue detection.
- duplicate/near-duplicate data issues.
- class imbalance/data issue auditing.
- ranking issues by severity.
- dataset quality overview.

### كيف نتفوق؟

ندمج هذه الفلسفة مع Data Preparation الأوسع، وننشئ **Unified Issue Inbox** بحيث تظهر label issues بجوار missingness/schema/duplicates/leakage بدل أن تعيش في نظام منفصل.

---

## 71.23 Evidently / Deepchecks / monitoring ecosystem

### أفكار يجب أن نرثها

- dataset drift.
- feature drift.
- target drift.
- train/test comparison.
- data integrity checks.
- production monitoring.
- report/test duality.

### كيف نتفوق؟

أي pipeline تنظيف تحفظ **Baseline Profile** تلقائيًا ويمكنها لاحقًا مقارنة batch جديد:

```text
same schema?
new categories?
missingness drift?
range drift?
distribution drift?
quality score regression?
```

ثم تقرر:

```text
pass
warn
quarantine
block
```

---

## 71.24 Polars

Polars ليس Cleaning Library بحد ذاته، لكنه مهم جدًا للبنية الحديثة.

### أفكار يجب أن نرثها في المحرك

- expression-based transformations.
- immutable/declarative style.
- lazy execution.
- query optimization.
- efficient columnar operations.
- streaming potential.

### كيف نتفوق كطبقة أعلى؟

المستخدم يكتب نفس SmartPrep API، والمكتبة تختار backend مناسبًا وتحوّل العمليات إلى native expressions قدر الإمكان.

---

## 71.25 DuckDB / Arrow philosophy

### أفكار يجب أن نرثها

- columnar interchange.
- zero/low-copy data movement where possible.
- analytical pushdown.
- query large local files without loading everything into pandas.
- Parquet-native execution.

### القيمة الجديدة

Cost Planner يقرر:

```text
Pandas eager
Polars lazy
DuckDB SQL pushdown
Arrow interchange
```

بناءً على حجم البيانات ونوع العملية.

---

# 72. Superset Requirements — الحد الأدنى لكي نقول إن المكتبة تتفوق وظيفيًا

هذه القائمة تتحول إلى **Definition of Done** للمشروع.

## 72.1 Profiling Superset

يجب أن توفر:

- dataset overview.
- column overview.
- inferred physical dtype.
- inferred semantic type.
- uniqueness.
- cardinality.
- missingness.
- zeros.
- negatives.
- infinities.
- empty strings.
- sentinel missing markers.
- descriptive statistics.
- robust statistics.
- quantiles.
- distributions.
- categorical frequency tails.
- mixed-type associations.
- target associations.
- interactions.
- duplicates.
- potential identifiers.
- possible keys.
- PII.
- time-series structure.
- panel structure.
- geospatial hints.
- text hints.

---

## 72.2 Cleaning Superset

يجب دعم:

- column-name normalization.
- whitespace normalization.
- Unicode normalization.
- case normalization.
- punctuation normalization.
- accent handling.
- string replacement.
- regex cleaning.
- numeric parsing.
- locale-aware number parsing.
- currency parsing.
- percentage parsing.
- Boolean normalization.
- date parsing.
- timezone normalization.
- category normalization.
- rare categories.
- inconsistent labels.
- unit conversion.
- phone/email/address/url cleaning.
- duplicate removal.
- near-duplicate resolution.
- invalid row quarantine.
- impossible-value handling.
- cross-column consistency repair.

---

## 72.3 Missing Data Superset

يجب دعم:

- missing marker discovery.
- missingness visualization.
- missingness dependency analysis.
- row and column thresholds.
- complete-case deletion.
- variable deletion.
- constant/arbitrary imputation.
- mean/median/mode.
- group-wise imputation.
- random-sample imputation.
- KNN.
- iterative/MICE.
- model-based imputation.
- time interpolation.
- forward/back fill.
- multiple imputation concept.
- missing indicators.
- masking-based evaluation.
- uncertainty report.

---

## 72.4 Encoding Superset

يجب دعم أو دمج:

- one-hot.
- ordinal.
- count/frequency.
- binary/base-N.
- hashing.
- target encoding.
- leave-one-out.
- CatBoost-style.
- WOE.
- contrast encodings.
- high-cardinality string encoding.
- fuzzy/similarity representations.
- text embeddings as optional extension.

مع:

- leakage-safe fitting.
- unknown-category policies.
- dimensionality estimate.
- interpretability score.
- memory estimate.

---

## 72.5 Numeric Transformation Superset

- Standard scaling.
- Min-max scaling.
- MaxAbs.
- Robust scaling.
- normalization.
- log transformations.
- reciprocal/sqrt transforms عند الصلاحية.
- Box-Cox.
- Yeo-Johnson.
- quantile transformation.
- winsorization/capping.
- clipping.
- discretization.
- domain constraints.

---

## 72.6 Outlier/Anomaly Superset

- IQR.
- robust z-score/MAD.
- percentile rules.
- domain bounds.
- isolation methods.
- local-density methods.
- multivariate methods.
- contextual/time-series anomalies.
- group-wise anomalies.
- influence diagnostics extension for econometrics.
- anomaly score.
- treatment comparison: keep/cap/transform/quarantine/remove.

---

## 72.7 Validation Superset

- dtype checks.
- nullable constraints.
- ranges.
- regex.
- isin/categories.
- uniqueness.
- composite uniqueness.
- column existence/order.
- strict schema.
- row-level rules.
- cross-column rules.
- aggregate checks.
- temporal checks.
- foreign-key/referential checks.
- learned/proposed rules.
- lazy all-error collection.
- data contracts.
- quality gates.

---

## 72.8 Interactive Superset

يجب أن تضم الواجهة على الأقل:

- Data Grid.
- virtualized scrolling.
- search.
- filter builder.
- sorting.
- column pin/hide/move.
- cell editing.
- bulk editing.
- transformation preview.
- visual histogram/distribution.
- missingness views.
- association explorer.
- target explorer.
- dataset comparison.
- issue inbox.
- column inspector.
- transformation lab.
- pipeline DAG.
- history timeline.
- undo/redo.
- version diff.
- code panel.
- generated Python code.
- export cleaned data.
- export report.
- export pipeline.
- keyboard shortcuts.

لكن أهم فرق: **لا يوجد Click غير قابل لإعادة الإنتاج**.

---

# 73. ميزات جديدة لا أريد أن تكون مجرد نسخ من المنافسين

هذه هي الطبقة التي تمنع المشروع من أن يصبح "مجموعة wrappers".

## 73.1 Data Preparation Copilot مع قيود تنفيذية

يمكن للمستخدم كتابة:

```text
جهز هذه البيانات لـ panel fixed-effects regression
```

الـLLM لا يعدل dataframe مباشرة، بل ينتج typed plan يمر عبر validator ثم execution engine.

---

## 73.2 Evidence-Based Recommendation Engine

كل توصية تحتوي:

```text
Recommendation
Evidence
Confidence
Alternatives
Trade-offs
Risk
Expected impact
```

---

## 73.3 Counterfactual Preparation

إنشاء Branches متعددة:

```text
Branch A: Median Imputation
Branch B: KNN
Branch C: MICE
```

ثم مقارنة النتيجة واختيار branch الفائز.

---

## 73.4 Data Preservation Score

يقيس مقدار المحافظة على:

- distributions.
- ranks.
- correlations.
- covariance.
- category structure.
- target relationships.
- temporal structure.

---

## 73.5 Information Loss Budget

المستخدم يستطيع تحديد:

```python
max_row_loss=0.02
max_distribution_shift=0.05
```

وأي تنظيف يتجاوز الميزانية يحتاج موافقة.

---

## 73.6 Transformation Risk Score

لكل عملية:

```text
Risk: Low / Medium / High
```

حسب:

- irreversibility.
- number of cells affected.
- target awareness.
- leakage potential.
- statistical distortion.
- semantic uncertainty.

---

## 73.7 Repair Confidence + Abstention

إذا لم تكن المكتبة واثقة، يجب أن تقول:

```text
I don't know — human review required.
```

وهذه أفضل من auto-cleaning عدواني.

---

## 73.8 Learned Cleaning Rules from User Actions

إذا كرر المستخدم تعديلات متشابهة، تقترح المكتبة Rule قابلة لإعادة الاستخدام.

---

## 73.9 Semantic Constraint Discovery

تكتشف قواعد محتملة مثل:

```text
payment_amount <= invoice_amount
end_date >= start_date
age >= 0
country determines currency غالبًا
```

لكن تعرضها كـproposed rules مع confidence، لا كحقائق مطلقة.

---

## 73.10 Data Quality Root-Cause Graph

بدل 30 alert منفصلًا، تربط المشاكل ببعضها:

```text
Mixed type
   ↓
failed numeric parsing
   ↓
artificial missing values
   ↓
biased summary
   ↓
model row loss
```

فيعرف المستخدم **سبب المشكلة الأصلي** بدل معالجة الأعراض.

---

## 73.11 Issue Dependency Planner

إذا كان إصلاح A يحل B وC، يتم تنفيذ A أولًا.

مثال:

```text
standardize missing markers
before
imputation diagnostics
```

---

## 73.12 Statistical Guardrails

بعد أي transform، يفحص تلقائيًا:

- variance collapse.
- category explosion.
- correlation shifts.
- perfect separation risk.
- target leakage.
- train/test drift amplification.

---

## 73.13 Econometrics Guardrails

إضافات خاصة يمكن أن تجعل المكتبة فريدة جدًا:

- panel index validation.
- duplicate entity-time detection.
- balanced/unbalanced panel report.
- within/between variation.
- time gaps.
- lag feasibility.
- interpolation warning across structural breaks.
- transformations that change long-run interpretation.
- target/response-aware leakage warnings.
- cluster/group integrity during train/test split.

---

## 73.14 Scientific Reproducibility Mode

وضع خاص للباحثين يمنع:

- silent mutation.
- undocumented row deletion.
- undocumented imputation.
- non-seeded stochastic transforms.

ويصدر Appendix تلقائيًا:

```text
Data preparation protocol
```

يمكن إدراجه في ورقة علمية.

---

# 74. تصميم الجزء التفاعلي ليكون أفضل من أدوات EDA التقليدية

## 74.1 الصفحة الأولى — Data Command Center

تظهر:

```text
Data Health Score
Critical Issues
Warnings
Recommended Next Actions
Rows at Risk
Columns at Risk
Privacy Warnings
ML Readiness
Econometrics Readiness
```

---

## 74.2 Issue Inbox

مثل البريد:

```text
Critical | annual_revenue mixed numeric/string
High     | customer_id duplicate key
Medium   | city has 19 near-duplicate labels
Low      | rating mildly skewed
```

يمكن:

- open.
- accept recommendation.
- compare treatments.
- ignore with reason.
- postpone.
- convert to validation rule.

---

## 74.3 Smart Data Grid

إضافة إلى grid التقليدية:

- cell quality badges.
- semantic-type icon.
- invalid-value highlighting.
- rule violation highlighting.
- anomaly highlighting.
- changed-cell highlighting.
- original-value hover.
- provenance hover.
- batch selection.

---

## 74.4 Column Workbench

عند الضغط على عمود، تظهر tabs:

```text
Profile
Quality
Missing
Outliers
Categories
Relationships
Target
Transform
Validate
History
```

---

## 74.5 Treatment Sandbox

يمكن تجربة أكثر من علاج دون لمس النسخة الأصلية.

```text
Try A
Try B
Try C
Compare
Apply winner
```

---

## 74.6 Pipeline Canvas

كل خطوة Node:

```text
Input
  ↓
Normalize missing markers
  ↓
Parse monetary columns
  ↓
Resolve duplicate entities
  ↓
Impute income
  ↓
Encode categories
  ↓
Validate
```

المستخدم يستطيع إعادة الترتيب؛ optimizer ينبه إذا كان الترتيب غير منطقي.

---

## 74.7 Split View — Raw vs Preview

جهة اليسار Raw، جهة اليمين Proposed Output، وبينهما:

- cells changed.
- rows changed.
- statistics changed.
- distribution changed.

---

## 74.8 Visual Rule Builder

بدون كود:

```text
IF status == "paid"
THEN payment_amount > 0
```

ثم يمكن Export إلى Python/YAML/JSON contract.

---

## 74.9 Interactive Association Explorer

نجمع أفكار Sweetviz وD-Tale ونوسعها:

- Pearson.
- Spearman.
- Kendall.
- Cramér's V.
- correlation ratio.
- uncertainty coefficient.
- mutual information.
- PPS optional.
- target relationship.

لكن نضيف:

```text
Before cleaning vs After cleaning association shift
```

---

## 74.10 Interactive Missingness Explorer

يجمع Missingno + diagnostics:

- matrix.
- bars.
- heatmap.
- dendrogram.
- cluster view.
- group comparison.
- time view.
- outcome view.

ثم recommendation panel في نفس الصفحة.

---

# 75. Competitive Acceptance Tests

لا نكتفي بقول "أفضل من Sweetviz" أو "أفضل من PyGWalker". يجب اختبار ذلك.

## 75.1 مقابل YData Profiling

اختبار:

- هل نستخرج نفس الفئات الأساسية من statistics/alerts؟
- هل لدينا actionable treatment لكل alert قابل للعلاج؟
- هل يمكن preview + apply + validate دون مغادرة البيئة؟

## 75.2 مقابل Sweetviz

- هل لدينا dataset comparison؟
- target analysis؟
- mixed-type associations؟
- هل نستطيع تحويل الاختلاف المكتشف إلى recommendation/action؟

## 75.3 مقابل D-Tale

- هل لدينا grid تفاعلية قوية؟
- filters/editing/transforms؟
- code generation؟
- وهل كل تعديل reversible/audited؟

## 75.4 مقابل PyGWalker

- هل الواجهة fluid وnotebook-friendly؟
- هل نستطيع exploration دون كود؟
- هل interactions تتحول إلى reproducible pipeline؟
- هل نضيف preparation-specific labs غير موجودة في generic visual analytics؟

## 75.5 مقابل Pandera

- هل schema/checks قوية؟
- هل ندعم Polars lazy semantics؟
- هل نستطيع infer ثم اقتراح schema بدل الكتابة اليدوية فقط؟

## 75.6 مقابل sklearn/Feature-engine

- هل كل preprocessing الأساس متاح؟
- هل fit/transform آمن؟
- هل recommendation يختار الطريقة بدل إجبار المستخدم على التخمين؟

---

# 76. Competitor Feature Registry — ملف يجب أن يعيش داخل المشروع

أنصح بإنشاء ملف داخل المستودع:

```text
docs/competitive_feature_registry.yaml
```

مثال:

```yaml
- competitor: sweetviz
  feature: compare datasets
  category: profiling
  our_status: planned
  parity_requirement: true
  superiority:
    - statistical drift metrics
    - actionable recommendations
    - pipeline branching

- competitor: pandera
  feature: lazy validation
  category: validation
  our_status: planned
  parity_requirement: true
  superiority:
    - inferred constraints
    - auto repair suggestion
    - cost-aware execution
```

هذا الملف يمنع نسيان أي ميزة عند تطور المشروع.

لكل Release يجب تشغيل **Competitive Coverage Review**:

```text
new competitor feature discovered?
↓
register
↓
classify
↓
parity / integrate / intentionally reject
↓
document reason
```

---

# 77. النتيجة بعد هذا التدقيق

بعد إضافة هذا التدقيق، لا ينبغي وصف المشروع على أنه:

> مكتبة Cleaning وPreprocessing تحتوي وظائف كثيرة.

بل:

> **Interactive, intelligent, auditable, multi-backend Data Preparation Platform that combines the best proven ideas from profiling, EDA, cleaning, validation, preprocessing and data-quality tools, then adds recommendation, explainability, reversible decisions, impact measurement and domain-aware preparation.**

المعادلة الموسعة تصبح:

```text
YData Profiling
+ Sweetviz
+ DataProfiler
+ Skimpy
+ Missingno
+ AutoViz-style automation
+ PyGWalker
+ D-Tale
+ PandasGUI-style editing
+ PyJanitor
+ DataPrep.Clean
+ Pandera + Polars
+ Great Expectations
+ Soda
+ scikit-learn preprocessing
+ Feature-engine
+ Category Encoders
+ Skrub
+ Imbalanced-learn
+ advanced imputation ecosystem
+ PyOD
+ Cleanlab Datalab
+ Evidently/Deepchecks-style monitoring
+ Polars/DuckDB/Arrow execution ideas
+
Recommendation Engine
+ Explainable Cleaning
+ Treatment Ranking
+ Counterfactual Branching
+ Impact Analysis
+ Data Preservation Score
+ Information Loss Budget
+ Transformation Risk Score
+ Human Review / Abstention
+ Learned Cleaning Rules
+ Root-Cause Graph
+ Versioning / Undo
+ Cell-level Lineage
+ Leakage Guard
+ Econometrics/Panel/Time-Series Doctor
+ Interactive Preparation Studio
```

هذه هي الصيغة التي تحقق فعليًا فكرة **"من كل بستان زهرة، ثم نبني بستانًا أفضل"** بدل تقليد مكتبة واحدة.

---

# 78. مراجع إضافية لهذا التدقيق التنافسي

## Sweetviz
- Repository and feature documentation: https://github.com/fbdesignpro/sweetviz

## DataProfiler
- Documentation: https://capitalone.github.io/DataProfiler/
- Repository: https://github.com/capitalone/DataProfiler

## D-Tale
- Repository and UI feature documentation: https://github.com/man-group/dtale

## Pandera / Polars
- Supported dataframe libraries: https://pandera.readthedocs.io/en/latest/supported_libraries.html
- Polars validation: https://pandera.readthedocs.io/en/stable/polars.html
- DataFrameSchema: https://pandera.readthedocs.io/en/stable/reference/generated/pandera.api.polars.container.DataFrameSchema.html
- Parsers: https://pandera.readthedocs.io/en/latest/parsers.html

## Category Encoders
- Documentation: https://contrib.scikit-learn.org/category_encoders/

## Skrub
- Documentation: https://skrub-data.org/stable/
- API reference: https://skrub-data.org/stable/reference/index.html

## Imbalanced-learn
- User guide: https://imbalanced-learn.org/stable/user_guide.html
- API reference: https://imbalanced-learn.org/stable/references/index.html

## Scikit-learn
- Preprocessing: https://scikit-learn.org/stable/modules/preprocessing.html
- Imputation: https://scikit-learn.org/stable/modules/impute.html
- ColumnTransformer: https://scikit-learn.org/stable/modules/generated/sklearn.compose.ColumnTransformer.html
- Pipeline: https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html


# 79. المصادر والمشروعات التي تمت مراجعتها

## YData Profiling

- Concepts / profiling / alerts: https://docs.profiling.ydata.ai/latest/getting-started/concepts/
- Configuration: https://docs.profiling.ydata.ai/4.8/advanced_settings/changing_settings/

## Pandera

- Main documentation: https://pandera.readthedocs.io/en/stable/
- Supported libraries: https://pandera.readthedocs.io/en/latest/supported_libraries.html
- DataFrame schemas: https://pandera.readthedocs.io/en/latest/dataframe_schemas.html

## PyJanitor

- Documentation: https://pyjanitor-devs.github.io/pyjanitor/
- Functions: https://pyjanitor-devs.github.io/pyjanitor/api/functions/

## DataPrep

- Clean introduction: https://docs.dataprep.ai/user_guide/clean/introduction.html
- Clean API: https://docs.dataprep.ai/api_reference/dataprep.clean.html

## D-Tale

- GitHub: https://github.com/man-group/dtale

## Scikit-learn

- Pipeline: https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html
- ColumnTransformer: https://scikit-learn.org/stable/modules/generated/sklearn.compose.ColumnTransformer.html

## Feature-engine

- Main documentation: https://feature-engine.trainindata.com/en/latest/
- User guide: https://feature-engine.trainindata.com/en/latest/user_guide/index.html

## Cleanlab

- Datalab tabular issue detection: https://docs.cleanlab.ai/stable/tutorials/datalab/tabular.html
- Datalab quickstart: https://docs.cleanlab.ai/stable/tutorials/datalab/datalab_quickstart.html

## Soda

- Contract language: https://docs.soda.io/reference/contract-language-reference
- Data contracts: https://docs.soda.io/data-contracts/data-contracts-write
- Release notes: https://docs.soda.io/release-notes/soda-core-release-notes

## Great Expectations

- Documentation: https://docs.greatexpectations.io/

## PyGWalker

- Project repository: https://github.com/Kanaries/pygwalker

---

# 80. الخطوة التالية المقترحة

بعد هذه الخطة، أفضل خطوة تقنية ليست البدء مباشرة في البرمجة، بل إعداد وثيقتين إضافيتين:

1. **Software Requirements Specification (SRS)**: كل feature، المدخلات، المخرجات، behavior، الأخطاء، الأولوية.
2. **Technical Architecture Specification**: interfaces، classes، data model، plugin protocol، backend abstraction، UI protocol، recommendation scoring، history format.

بعدهما يمكن تنفيذ `v0.1` دون إعادة تصميم المشروع من الصفر كل مرة.


---

# 81. Reporting & Interactive EDA System — منظومة التقارير والتحليل الاستكشافي قبل وبعد التنظيف

هذه الطبقة ليست إضافة تجميلية، بل جزء أساسي من هوية المكتبة. الهدف أن تنتج المكتبة **دليلًا مرئيًا وقابلًا للتدقيق** على حالة البيانات قبل التنظيف، وما الذي تغير أثناء التنظيف، وما أصبحت عليه البيانات بعد التنظيف.

## 81.1 المبدأ العام

يجب أن تعمل المنظومة وفق ثلاث لقطات رئيسية:

1. **Pre-Cleaning Snapshot** — حالة البيانات الخام كما وصلت.
2. **Post-Cleaning Snapshot** — حالة البيانات بعد تنفيذ عمليات التنظيف والمعالجة الأولية.
3. **Before/After Comparative Report** — مقارنة مباشرة توضح كل التغيرات، حجمها، سببها، أثرها الإحصائي، وأثرها على جودة البيانات.

ولا ينبغي أن يقتصر الأمر على تقرير واحد، بل يجب دعم عدة مستويات من التقارير حسب المستخدم والغرض.

## 81.2 أنواع التقارير المقترحة

### A. Executive Report

تقرير مختصر للإدارة أو الباحث الذي يريد الخلاصة فقط:

- Data Health Score قبل وبعد.
- عدد المشاكل المكتشفة.
- عدد المشاكل المعالجة.
- عدد المشاكل التي بقيت مفتوحة.
- أهم التحولات التي حدثت.
- نسبة البيانات المتأثرة.
- أخطر القرارات أو التحويلات.
- Top 10 issues.
- أهم الرسوم المقارنة.
- توصيات نهائية.

### B. Technical Data Quality Report

تقرير تقني مفصل يشمل:

- schema.
- data types.
- semantic types.
- missingness.
- duplicates.
- unique values.
- cardinality.
- invalid values.
- constraint violations.
- outliers.
- distributions.
- correlations/associations.
- rare categories.
- suspicious IDs.
- inconsistent dates.
- numerical precision issues.
- string anomalies.
- category normalization issues.

### C. Cleaning Audit Report

يشرح كل عملية تمت:

- operation.
- affected columns.
- affected rows.
- old values/new values.
- method.
- parameters.
- reason.
- recommendation score.
- confidence.
- user approval status.
- timestamp.
- version before/after.
- undo checkpoint.

### D. Statistical Preservation Report

يركز على السؤال: هل غيّر التنظيف طبيعة البيانات؟

يشمل مقارنة:

- mean.
- median.
- variance.
- standard deviation.
- skewness.
- kurtosis.
- quantiles.
- IQR.
- correlation matrix.
- covariance matrix.
- empirical distribution.
- category proportions.
- target distribution.

مع مقاييس مثل:

- Distribution Shift Score.
- Correlation Preservation Score.
- Information Loss Score.
- Data Preservation Score.

### E. ML Readiness Report

بعد preprocessing:

- numeric/categorical readiness.
- remaining missingness.
- encoding readiness.
- scale mismatch.
- constant/quasi-constant features.
- leakage risks.
- class imbalance.
- train/test distribution shift.
- duplicate leakage.
- target leakage.

### F. Econometrics Readiness Report

خصوصًا للباحثين:

- time index integrity.
- panel identifier integrity.
- duplicate entity-time keys.
- gaps.
- unbalanced panel diagnostics.
- within/between variation.
- insufficient variation.
- suspicious structural breaks caused by cleaning.
- interpolation map.
- dropped observations map.
- transformation log.

---

# 82. Output Formats — صيغ التقارير

يجب ألا تربط المكتبة المستخدم بصيغة واحدة.

## 82.1 HTML Interactive Report

يجب أن يكون المخرج الأساسي الأكثر ثراءً.

يدعم:

- tabs.
- filters.
- search.
- drill-down.
- expand/collapse.
- hover.
- zoom.
- pan.
- brush selection.
- linked charts.
- dynamic tables.
- before/after toggle.
- split view.
- issue navigation.
- user decision controls.

ويستفيد من فلسفة Sweetviz في self-contained HTML ومن أدوات visualization التفاعلية الحديثة، لكن يتجاوزها بإضافة **تنفيذ القرارات وإعادة إنتاجها وتسجيلها**.

## 82.2 PDF Static Report

مهم للبحث الأكاديمي، الأرشفة، المؤسسات، والإرسال الرسمي.

يجب دعم:

- Executive PDF.
- Full Technical PDF.
- Audit PDF.
- Before/After PDF.

مع رسوم ثابتة publication-quality.

## 82.3 Notebook Embedded Report

يدعم:

- Jupyter Notebook.
- JupyterLab.
- Google Colab.

ويظهر داخل iframe/widget دون الحاجة إلى فتح نافذة خارجية.

## 82.4 JSON Report

للاستخدام البرمجي والتكامل مع التطبيقات الأخرى.

## 82.5 YAML Report

مفيد للـpipelines والسياسات والـconfiguration.

## 82.6 Markdown Report

مفيد للتوثيق وGitHub وREADME والبحث.

## 82.7 PNG/SVG Export

لكل رسم منفرد.

## 82.8 Optional DOCX / PPTX Export Layer

ليست ضرورية في النواة الأولى، لكنها قيمة إضافية مستقبلية للباحثين والاستشاريين.

---

# 83. Dual Visualization Engine — محرك رسوم ثابتة + تفاعلية

يجب ألا تختار المكتبة بين Matplotlib/Seaborn وبين Plotly؛ بل تدعم فلسفتين متكاملتين.

## 83.1 Static Visualization Engine

للتقارير الأكاديمية والـPDF.

Backend candidates:

- Matplotlib.
- Seaborn-style statistical plots.

يدعم:

- histogram.
- density/KDE.
- ECDF.
- boxplot.
- violin plot.
- strip/swarm.
- bar chart.
- count plot.
- scatter.
- regression plots.
- pair plot.
- heatmap.
- correlation matrix.
- missingness heatmap.
- category frequency chart.
- QQ plot.
- residual-style diagnostics where relevant.

## 83.2 Interactive Visualization Engine

Backend candidates:

- Plotly.
- optional Altair/Vega-Lite adapter.

يقدم:

- hover tooltips.
- zoom.
- pan.
- box/lasso selection.
- linked filtering.
- dynamic legends.
- live thresholds.
- sliders.
- dropdowns.
- before/after toggle.
- animation frames where useful.

Plotly يدعم animation frames وplay/pause controls إضافة إلى hover/zoom/pan، لذلك يمكن استخدامه كمرجع وظيفي للطبقة الديناميكية، مع ضرورة عدم استخدام animation لمجرد الإبهار البصري.

---

# 84. متى نستخدم Animation؟

Animation يجب أن تكون **اختيارية ومبررة تحليليًا**.

الاستخدامات المفيدة:

### A. Cleaning Timeline Animation

يعرض dataset عبر مراحل:

Raw → Type Fix → Missing Treatment → Outlier Treatment → Encoding → Final.

يمكن للمستخدم تحريك Slider ومشاهدة تغير التوزيع.

### B. Before/After Distribution Morph

يوضح كيف تغير توزيع متغير بعد imputation أو transformation.

### C. Missingness Evolution

كيف تقل missingness بعد كل خطوة.

### D. Data Health Evolution

Score عبر pipeline steps.

### E. Outlier Treatment Evolution

عرض النقاط قبل وبعد كل treatment.

### F. Panel/Time-Series Cleaning Timeline

إظهار الفجوات، interpolation، dropped dates، repaired dates عبر الزمن.

### G. Pipeline Replay

تشغيل replay بصري لكل قرارات التنظيف.

## قاعدة مهمة

لا تستخدم animation إذا كان رسم static أو side-by-side أو small multiples أو slider أو toggle أوضح وأكثر صدقًا.

---

# 85. Pre-Cleaning EDA — التحليل الاستكشافي الأولي قبل التنظيف

هذه مرحلة **تشخيص** وليست تحليلًا نهائيًا.

يجب أن تشمل:

## Dataset Overview

- rows/columns.
- memory usage.
- duplicate rows.
- variable types.
- semantic types.
- unique values.
- completeness.

## Univariate EDA

لكل متغير:

- distribution.
- missingness.
- central tendency.
- dispersion.
- quantiles.
- skewness.
- kurtosis.
- rare values.
- suspicious values.
- invalid values.

## Bivariate EDA

- numeric-numeric.
- categorical-categorical.
- numeric-categorical.
- target-feature relations.

## Multivariate EDA

- correlation/association maps.
- clustered correlations.
- pairwise relationships.
- dimensionality overview where justified.

## Data Quality EDA

- missingness patterns.
- duplicate patterns.
- outlier map.
- inconsistent categories.
- invalid ranges.
- cross-column contradictions.

## Critical principle

التقرير يجب أن يضع بوضوح علامة:

> **RAW DATA — BEFORE CLEANING**

حتى لا يختلط هذا التحليل بالتحليل النهائي.

---

# 86. Post-Cleaning EDA — التحليل الاستكشافي بعد التنظيف

لا ينبغي الاكتفاء بإعادة تشغيل نفس التقرير.

يجب أن يتضمن:

- dataset overview after cleaning.
- remaining issues.
- new distributions.
- new associations.
- missingness remaining.
- category structure after normalization.
- outlier structure after treatment.
- feature transformations.
- target distribution after preprocessing.
- readiness scores.

ثم يربط كل نتيجة بما كانت عليه قبل التنظيف.

---

# 87. Before/After Comparative EDA — ميزة مركزية للمكتبة

هذا يجب أن يكون من أهم نقاط التفوق.

لكل Variable Card:

### Before

- dtype.
- semantic type.
- missing %.
- unique count.
- distribution.
- outliers.
- summary statistics.

### After

نفس العناصر.

### Difference

- rows affected.
- values changed.
- missing reduction.
- variance change.
- mean/median change.
- category consolidation.
- outlier reduction.
- distribution shift.
- association changes.

ثم:

### Explanation

لماذا تغير؟

### Risk

هل التغيير صغير أم قد يؤثر على الاستنتاج؟

---

# 88. User Decision Layer — الإنسان داخل الحلقة

لا يجب أن تكون المكتبة Full-Auto فقط.

يجب دعم ثلاثة أنماط واضحة:

## Mode 1 — Auto

المكتبة تنفذ القرارات ذات الثقة العالية حسب policy.

## Mode 2 — Guided

المكتبة تقترح والـuser يقرر.

هذا هو الوضع الافتراضي المقترح.

## Mode 3 — Manual

المستخدم يختار كل عملية بنفسه.

---

# 89. Decision Dialogs — نوافذ القرار التفاعلية

عندما يكون القرار غير قطعي، تظهر للمستخدم نافذة أو panel.

مثال Missing Values:

> Column: income
>
> Missing: 8.3%
>
> Suggested methods:
> - Median
> - Group median
> - KNN
> - Iterative
> - Drop rows
> - Leave unchanged

بجانب كل خيار:

- recommendation score.
- confidence.
- expected distortion.
- runtime.
- memory cost.
- leakage risk.
- preview.

ثم أزرار:

- Preview.
- Apply.
- Apply to similar columns.
- Ignore.
- Ask for explanation.
- Compare methods.

---

# 90. Treatment Sandbox — معمل تجريبي قبل التنفيذ

هذه من أهم القيم المضافة.

عندما يحتار المستخدم بين طريقتين أو أكثر، تقوم المكتبة ببناء نسخ مؤقتة ولا تمس dataset الأصلية.

مثال:

- Candidate A: median.
- Candidate B: KNN.
- Candidate C: iterative.

ثم تعرض:

- distribution comparison.
- summary statistics change.
- correlation change.
- information loss.
- downstream performance if target/model supplied.
- computation cost.

ثم يختار المستخدم.

---

# 91. Live Preview Before Apply

أي عملية يختارها المستخدم يجب أن تعرض Preview فورًا.

مثال:

| Row | Before | After |
|---|---:|---:|
| 12 | NaN | 42800 |
| 45 | NaN | 39100 |

مع:

- affected rows count.
- affected percentage.
- distribution overlay.
- warnings.

ولا تُعتمد العملية إلا بعد Apply، ما لم يكن Auto Mode مفعّلًا.

---

# 92. Interactive Data Grid — جدول تفاعلي متقدم

يجب أن يتجاوز العرض التقليدي للـDataFrame.

المزايا:

- sort.
- filter.
- search.
- column pinning.
- type badges.
- issue badges.
- conditional formatting.
- invalid-value highlighting.
- missing-value highlighting.
- duplicate highlighting.
- outlier highlighting.
- editable cells when allowed.
- context menu.
- column statistics on click.
- before/after value toggle.
- row history.

كل تعديل يدوي يجب أن يدخل Audit Trail.

---

# 93. Linked Visual Analytics

عند اختيار نقاط في scatter plot مثلًا:

- يتم تحديد نفس الصفوف في الجدول.
- يتم تحديث histogram.
- يتم تحديث summary panel.
- يمكن للمستخدم إنشاء filter من selection.
- يمكن تحويل selection إلى cleaning rule.

مثال:

المستخدم يحدد cluster مشبوهًا ثم يختار:

> Inspect selected rows

أو:

> Mark as anomaly candidates

---

# 94. Visual Rule Builder

بدل كتابة كود:

```text
age < 18 AND employment_status == "retired"
```

يمكن إنشاء القاعدة من GUI:

Column → Operator → Value → AND/OR → Column → Operator → Value.

ثم:

- Preview violations.
- Save rule.
- Apply repair.
- Export rule as Python/YAML/JSON.

---

# 95. Smart Chart Recommendation

بدل إظهار عشرات الرسوم دون هدف، تقترح المكتبة الرسم المناسب حسب نوع البيانات والمشكلة.

مثال:

- missingness → matrix/heatmap/bar.
- skewness → histogram + KDE + log-preview.
- categorical imbalance → ordered bar.
- numerical outliers → box + robust z-score view.
- time irregularity → timeline/gap plot.
- panel gaps → entity-time heatmap.
- before/after distribution → overlay/ECDF/side-by-side.

مع إمكانية:

> Show alternatives

---

# 96. Chart Backends & User Choice

يجب أن يستطيع المستخدم الاختيار:

```python
report.plot_backend = "plotly"
```

أو:

```python
report.plot_backend = "matplotlib"
```

أو وضع:

```python
report.plot_backend = "auto"
```

حيث تختار المكتبة:

- interactive backend لـHTML.
- static backend لـPDF.

---

# 97. Report Builder — منشئ تقارير مرن

المستخدم لا يحتاج دائمًا إلى التقرير الكامل.

يجب دعم:

```python
report = project.report(
    sections=[
        "overview",
        "missing",
        "outliers",
        "duplicates",
        "before_after"
    ]
)
```

أو من UI عبر checkboxes.

يمكن التحكم في:

- sections.
- variables.
- chart types.
- level of detail.
- language.
- theme.
- output format.
- branding.

---

# 98. Report Presets

### quick

تقرير سريع.

### full

كل شيء.

### academic

رسوم publication-ready وإحصاءات كاملة.

### business

KPIs وخلاصات.

### audit

كل التغييرات والقرارات.

### ml

ML readiness.

### econometrics

تشخيصات ملائمة للبحث القياسي.

---

# 99. Interactive Story Mode

إضافة مبتكرة:

بدل dashboard ثابت، يمكن أن تبني المكتبة **قصة التنظيف** تلقائيًا:

1. البيانات الخام.
2. أهم المشاكل.
3. أكثر المتغيرات تضررًا.
4. القرارات التي اتخذت.
5. لماذا تم اختيارها.
6. ماذا تغير.
7. هل تأثرت التوزيعات.
8. ما الذي بقي يحتاج تدخلًا.

مع Next/Previous أو scroll narrative.

هذا مفيد جدًا للتعليم والعروض والباحثين.

---

# 100. Explain This Chart / Explain This Issue

في كل رسم أو بطاقة:

- Explain.
- Why is this a problem?
- What should I do?
- Compare treatments.

ويجب أن يكون الشرح مبنيًا على metrics وقواعد موثوقة، لا على نص LLM حر وحده.

---

# 101. Report Diff Engine

يمكن مقارنة ليس فقط Raw vs Final، بل أي إصدارين:

```python
project.report_diff("v2", "v7")
```

ويعرض:

- schema diff.
- rows diff.
- values diff.
- distributions diff.
- quality score diff.
- pipeline diff.

---

# 102. Red Flags في التقرير

يجب أن ترفع المكتبة تحذيرات واضحة إذا:

- التنظيف غيّر mean بشدة.
- variance انهارت بعد imputation.
- correlation تغيرت كثيرًا.
- categories اختفت.
- class balance تغير.
- عدد كبير من الصفوف حذف.
- temporal order تضرر.
- panel structure تغير.
- transformation قد تسبب leakage.

---

# 103. User Approval Workflow

يمكن تعريف policy مثل:

```text
Auto-approve low-risk changes.
Require confirmation for medium-risk changes.
Block high-risk changes until manual approval.
```

مثال:

- trim whitespace → low risk.
- normalize case → low/medium.
- median imputation → medium.
- row deletion > 5% → high.
- target encoding → high leakage sensitivity.

---

# 104. Suggested Reporting API

```python
project.scan()

project.report(stage="raw", format="html")

project.clean(mode="guided")

project.report(stage="clean", format="html")

project.compare_report(
    before="raw",
    after="clean",
    format="html"
)

project.export_report(
    format="pdf",
    preset="academic"
)
```

واجهة أكثر اختصارًا:

```python
project.report.before()
project.report.after()
project.report.compare()
```

---

# 105. SmartPrep Studio — الهيكل المقترح للواجهة

## Top Bar

- Dataset.
- Version.
- Health Score.
- Mode: Auto/Guided/Manual.
- Undo/Redo.
- Export.

## Left Sidebar

- Overview.
- Raw EDA.
- Issues.
- Missing.
- Duplicates.
- Types.
- Categories.
- Outliers.
- Rules.
- Preprocessing.
- Pipeline.
- Post EDA.
- Compare.
- Reports.
- Audit.

## Main Workspace

يتغير حسب المهمة.

## Right Decision Panel

- detected problem.
- evidence.
- recommendations.
- alternatives.
- confidence.
- risk.
- preview.
- apply.

## Bottom Panel

- generated Python code.
- operation history.
- warnings.

---

# 106. أهم مبدأ في الواجهة

يجب الجمع بين:

**Automation + User Control + Explainability + Reproducibility**

أي:

- لا تجبر المستخدم على الكتابة اليدوية لكل شيء.
- لا تجعل المكتبة تتخذ كل القرارات سرًا.
- اقترح القرار.
- اشرح السبب.
- اعرض البدائل.
- اعرض أثر كل بديل.
- اترك القرار للمستخدم عندما تكون المسألة غير قطعية.
- حوّل كل قرار إلى كود قابل للتكرار.

---

# 107. القاعدة الذهبية للتقارير

المكتبة لا تقول فقط:

> هذه هي البيانات بعد التنظيف.

بل تقول:

> هذه كانت البيانات قبل التنظيف، وهذه المشاكل التي اكتشفناها، وهذه البدائل التي كانت ممكنة، وهذه القرارات التي اتخذت، وهذه الصفوف والقيم التي تغيرت، وهذا أثر القرارات على الإحصاءات والتوزيعات والعلاقات، وهذه حالة البيانات بعد التنظيف، وهذه المشاكل المتبقية، وهذا هو الكود الذي يعيد إنتاج كل ما حدث.

هذه النقطة يجب أن تكون واحدة من أهم نقاط التفوق التنافسي للمكتبة.

---

# 108. مراجع إضافية لهذا الجزء

## Sweetviz

- Self-contained HTML EDA reports.
- Target analysis.
- Dataset comparison.
- Mixed-type associations.
- Notebook embedding.
- https://github.com/fbdesignpro/sweetviz

## Plotly

- Interactive charts.
- hover/zoom/pan/select.
- animation frames.
- play/pause controls.
- Dash integration.
- https://plotly.com/python/animations/
- https://plotly.com/graphs/

---

# 109. تعديل الأولوية في Roadmap

يجب نقل Reporting/EDA من feature ثانوية إلى **Core Product Pillar**.

## v0.1

- raw EDA report.
- post-cleaning EDA report.
- before/after comparison.
- HTML interactive report.
- static plots.
- Plotly interactive plots.
- user-guided decisions.
- preview before apply.
- audit trail.

## v0.2

- PDF export.
- report presets.
- report diff.
- linked visual analytics.
- visual rule builder.
- treatment sandbox.

## v0.3

- animation where analytically useful.
- interactive story mode.
- advanced report builder.
- organizational branding.
- scheduled/monitoring reports.


---

# 110. Real-World Stress Test — نتائج `data_project(5).xlsx`

تم استخدام ملف بيانات خام حقيقي/غير منظم كاختبار ضغط عملي لتصميم المكتبة. الهدف هنا ليس تنظيف الملف نفسه فقط، بل تحويل كل مشكلة واقعية مكتشفة إلى **Requirement** داخل المنتج حتى لا تبقى الخطة نظرية.

## 110.1 بصمة البيانات

- عدد الصفوف: **1,210**.
- عدد المتغيرات: **21**.
- ورقة البيانات: `raw_data`.
- قاموس بيانات منفصل: `data_dictionary`.
- المجالات الموجودة تشمل: معرفات، تواريخ، جغرافيا، فئات، كميات، أسعار، نسب، مبالغ مالية، بيانات شركات، تقييمات وقنوات بيع.

هذه البنية مناسبة لاختبار: type inference، semantic typing، missingness، duplicates، categorical normalization، date parsing، numeric parsing، cross-field rules، domain constraints، payment logic، geographic consistency، formula validation، anomaly detection وuser-guided repair.

---

# 111. مشكلة جديدة/مؤكدة: Mixed Physical Types داخل العمود نفسه

يجب ألا تعتمد المكتبة على `dtype` وحده.

## أمثلة فعلية

### `invoice_date`

يحتوي العمود على:

- قيم Excel/Python datetime فعلية.
- نصوص مثل `24/02/2026`.
- نصوص مثل `07-10-2025`.
- نصوص ISO مثل `2026-06-26`.
- تاريخ أمريكي مثل `08-26-2024`.
- تواريخ غير صالحة مثل `31/02/2025`.
- قيمة غير قابلة للتفسير مباشرة مثل `2025-13-04` من دون معرفة النظام المقصود.

إذن dtype العام `object` يخفي عدة representations داخل نفس العمود.

### `unit_price`

يحتوي على:

- `float`.
- `int`.
- numeric strings.
- formatted numeric strings مثل `9,597.80` و`21,475.49`.

### `annual_revenue`

يحتوي على:

- floats.
- integers.
- strings مثل `486,849`.

## Requirement

إنشاء **Mixed-Type Composition Profiler** يعرض ليس dtype واحدًا بل توزيع الأنواع الفيزيائية والأنواع الدلالية:

```text
unit_price
---------------------------------
float                  98.0%
integer                 0.9%
formatted numeric text  1.1%

Semantic target: monetary numeric
Confidence: 99.8%
```

ويجب أن يحتفظ بالقيمة الأصلية إلى جانب parsed value أثناء مرحلة Preview.

---

# 112. Multi-Format Date Intelligence

المكتبة تحتاج Date Engine أعمق من `pd.to_datetime()`.

## المطلوب اكتشافه

- mixed separators `/`, `-`, `.`.
- `DD/MM/YYYY` مقابل `MM/DD/YYYY`.
- ISO dates.
- Excel serial dates.
- timestamps.
- timezone-bearing timestamps.
- impossible dates.
- ambiguous dates.
- locale-specific formats.
- partial dates.
- year-only/month-only values.

## حالات حقيقية في الملف

هناك **4 قيم فشلت في parsing قياسي**، من بينها ثلاثة occurrences لـ `31/02/2025` وقيمة `2025-13-04`.

## الابتكار المقترح

### Date Ambiguity Resolver

بدل اختيار `dayfirst=True/False` بشكل أعمى:

1. infer dominant format من العمود.
2. infer locale من country/context إن توفر.
3. score لكل تفسير ممكن.
4. flag ambiguous rows.
5. يعرض preview للمستخدم.

مثال:

```text
Value: 04/05/2024
Possible interpretations:
1. 4 May 2024   confidence 0.81
2. 5 April 2024 confidence 0.19

Column dominant format: DD/MM/YYYY
Recommendation: 4 May 2024
```

## Hard Error vs Ambiguity

- `31/02/2025` = **Hard invalid date**.
- `04/05/2024` = **Ambiguous date** حسب السياق.

يجب ألا يعاملا بالطريقة نفسها.

---

# 113. Identifier Integrity Engine

وجود duplicate rows لا يكفي. يجب تحليل **هوية السجل**.

في الملف:

- `invoice_id` يحتوي **18 معرف فاتورة مكررًا**.
- تمثل هذه المعرفات 36 صفًا.
- **9 IDs** هي duplicates متطابقة بالكامل.
- **9 IDs** هي **Conflicting Duplicates**: المعرف نفسه لكن قيم أخرى مختلفة.

هذه فئة أهم بكثير من `df.duplicated()`.

## يجب دعم أربع حالات

1. Exact row duplicate.
2. Duplicate business key + identical payload.
3. Duplicate business key + conflicting payload.
4. Near-duplicate entities مع اختلافات بسيطة في النصوص.

## UI المقترحة

```text
Invoice ID: INV-2025-00109
Conflict detected

Record A     Record B
customer     ...
invoice_date ...
country      ...
amount       ...

Actions:
[Keep A] [Keep B] [Merge] [Mark unresolved] [Define precedence rule]
```

ويجب ألا يتم auto-delete للـconflicting duplicates.

---

# 114. Identifier-Embedded Metadata Validation

إذا كان الـID يحمل معلومة داخل بنيته، يجب استخراجها والتحقق منها.

مثال:

```text
INV-2025-xxxxx
```

يحتوي سنة ضمن الـID.

في البيانات ظهرت عدة حالات لا تتطابق فيها السنة المشفرة في `invoice_id` مع سنة `invoice_date`.

## Requirement

إنشاء **Identifier Pattern + Embedded Metadata Validator**:

```python
rule = EmbeddedRule(
    field="invoice_id",
    regex=r"INV-(?P<year>\\d{4})-\\d{5}",
    compare={"year": "invoice_date.year"}
)
```

ويجب أن يستطيع النظام اقتراح هذه القاعدة تلقائيًا ثم طلب تأكيد المستخدم.

---

# 115. Categorical Canonicalization أعمق من trim/lower

ظهرت حالات متعددة من نفس الفئة:

### Country

- `Algeria`
- `ALGERIA`
- `algeria`
- ` Algeria`
- `Algeria `
- `Algérie`

### Sector

- `Construction` / `construction`
- `Retail` / `retail` / `Retail `
- `ICT` / `ICT ` / `I.C.T`
- `Tourismm`
- `Manufacturıng` حيث يوجد حرف Unicode مختلف (`ı`).

### Payment method

- `Card` / `CARD`
- `Cash` / `Cash `
- `Cheque` / `Cheque `
- `Bank Transfer` / `bank transfer` / `Bank transfer `
- `Mobile Payment` / `mobile payment`

## Requirement

إنشاء **Canonicalization Engine** متعدد المراحل:

1. whitespace normalization.
2. Unicode normalization.
3. case folding.
4. punctuation normalization.
5. accent/diacritic-aware comparison.
6. typo similarity.
7. abbreviation equivalence.
8. language-aware aliases.
9. domain dictionary lookup.
10. user-confirmed canonical map.

مثال:

```text
Suggested cluster:
ICT
ICT 
I.C.T

Canonical value: ICT
Confidence: 0.99
```

أما `Tourismm -> Tourism` فيجب أن يكون اقتراحًا مع confidence، لا تعديلًا صامتًا.

---

# 116. Unicode Confusable Character Detection

قيمة مثل:

```text
Manufacturıng
```

تحتوي على dotless `ı` بدل ASCII `i`.

هذه مشكلة قد تمر على trim/lowercase العادي.

## Requirement جديد

**Unicode Confusable Detector** لاكتشاف:

- homoglyphs.
- zero-width characters.
- non-breaking spaces.
- Unicode normalization differences.
- Arabic/Persian digit variants.
- Latin/Cyrillic lookalikes.

ويعرض الفرق بصريًا للمستخدم.

---

# 117. Geographic Consistency Engine

تم العثور على أمثلة مثل:

- Country = Algeria مع City = Fes.
- Country = France مع City = Algiers.
- Country = Morocco مع City = Cairo.
- Country = Tunisia مع City = Paris.

وفق mapping جغرافي معروف للمدن في هذه العينة، ظهرت **26 حالة country-city mismatch**.

## Requirement

المكتبة يجب أن تستطيع التحقق من:

```text
country <-> city
country <-> state/province
postal code <-> city
latitude/longitude <-> country
```

لكن قواعد الجغرافيا يجب أن تكون plugin-based وقابلة للتحديث.

---

# 118. Currency-Context Consistency

ظهرت **22 حالة country-currency mismatch** إذا اعتبرنا العملة المحلية المتوقعة هي:

- Algeria -> DZD
- Morocco -> MAD
- Tunisia -> TND
- Egypt -> EGP
- France -> EUR

كما ظهر `USD` مرة واحدة.

لكن هذه ليست دائمًا أخطاء؛ الفاتورة قد تكون مقومة بعملة أجنبية.

## لذلك يجب تصنيفها كـ

**Contextual/Semantic Suspicion** وليس Hard Error.

UI:

```text
Country: Algeria
Currency: EUR

Possible interpretations:
- legitimate foreign-currency transaction
- miscoded currency

[Allow foreign currency] [Flag for review] [Define country-currency policy]
```

هذه الحالة مثال ممتاز على أهمية Human-in-the-loop.

---

# 119. Domain Range Constraints

ظهرت قيم مؤكدة خارج حدود طبيعية/معلنة ضمنيًا:

- `quantity < 0`: **3**.
- `quantity == 0`: **2**.
- `discount_pct < 0`: **4**.
- `discount_pct > 1`: **1** (1.25 = 125%).
- `tax_pct < 0`: **1**.
- `tax_pct > 1`: **3** (1.50 = 150%).
- `customer_rating > 5`: **5**، منها 9.9 و6.7.
- `employee_count < 0`: **1**.
- `employee_count == 0`: **1**.
- `employee_count = 999999`: **2** وهي قيم مرشحة بقوة لأن تكون sentinel/error وليست مجرد outlier إحصائي.

## Requirement

إنشاء **Constraint Layer** يميز بين:

- hard domain bounds.
- soft expected ranges.
- statistical outliers.
- sentinel-code suspicion.

فـ`999999` لا ينبغي التعامل معها كـoutlier عادي باستخدام IQR فقط.

---

# 120. Sentinel Value Intelligence

القيم مثل:

```text
999
9999
999999
-1
-99
0
```

قد تكون Missing Codes أو placeholder وليست قيماً حقيقية.

في الملف ظهر `employee_count=999999` مرتين.

## Requirement جديد

**Sentinel Detector** يعتمد على:

- repeated extreme round values.
- documentation/data dictionary.
- gap from neighboring distribution.
- field semantics.
- cross-column plausibility.

ثم يسأل المستخدم:

```text
999999 appears twice in employee_count and is far outside the normal range.
Treat as:
[Valid] [Missing sentinel] [Data-entry error] [Custom rule]
```

---

# 121. Derived-Field / Formula Consistency Engine

إذا كانت هناك علاقة مرشحة مثل:

```text
invoice_amount ≈ quantity * unit_price * (1 - discount_pct) * (1 + tax_pct)
```

فإن البيانات تظهر أكثر من **100 صف** لا يطابق هذه العلاقة عند استخدام هذه الصيغة المرشحة.

لكن يجب **عدم افتراض** أن هذه هي الصيغة الصحيحة دون metadata أو تأكيد المستخدم؛ قد توجد رسوم أو قواعد أخرى.

## مفهوم جديد: Candidate Invariant Discovery

المكتبة:

1. تبحث عن علاقات حسابية محتملة.
2. تقيس مدى انطباقها.
3. تعرض evidence.
4. تطلب تأكيد business rule.
5. بعد التأكيد تتحول إلى validation rule.

مثال:

```text
Candidate relation discovered:
invoice_amount ~ quantity * unit_price * (1-discount) * (1+tax)

Fit on apparently clean rows: 91.6%
Violations: 101

[Confirm rule] [Modify formula] [Ignore]
```

هذه أقوى من مجرد hard-coded validation.

---

# 122. Cross-Field Workflow/State Consistency

حالة الدفع ليست عمودًا منفصلًا؛ يجب مقارنتها بـ:

- `payment_date`.
- `payment_amount`.
- `invoice_amount`.
- التاريخ الحالي أو due date إذا توفر.

في الملف ظهرت أمثلة مثل:

- **7** سجلات `Paid` لكن `payment_date` مفقود.
- **8** سجلات `Paid` لكن `payment_amount` مفقود.
- **55** سجلاً `Paid` لكن المبلغ المسجل لا يساوي invoice amount ضمن tolerance بسيط.
- **2** سجلات `Pending` فيها payment amount غير صفري.
- **1** سجل `Partial` بلا payment date.
- عدد كبير من `Overdue` لديه payment date، وهو قد يكون مشروعًا إذا كان الدفع تم متأخرًا؛ لذلك يحتاج إلى تعريف معنى status.

## Requirement

إنشاء **State Machine Validator** بدل if-statements منفصلة.

مثال:

```text
Pending -> Partial -> Paid
        -> Overdue -> Paid
```

ويحدد المستخدم قواعد الانتقال والمعنى الدقيق لكل state.

---

# 123. Missingness Semantics — Structural vs Suspicious Missing

المفقودات المكتشفة:

- `payment_date`: 333 (27.52%).
- `city`: 26 (2.15%).
- `payment_amount`: 16 (1.32%).
- `reported_profit`: 18 (1.49%).

لكن Missing في `payment_date` عندما status=`Pending` قد يكون **Structural/Expected Missing** وليس مشكلة جودة.

أما `Paid + missing payment_date` فهو **Suspicious Missing**.

## Requirement جديد

Missingness يجب أن يصنف إلى:

1. Expected/structural missing.
2. Conditionally expected missing.
3. Suspicious missing.
4. Invalid missing according to rule.
5. Unknown missing.

هذا أكثر فائدة من نسبة missing العامة.

---

# 124. Statistical Outlier vs Semantic Error

IQR يحدد عشرات/مئات القيم المتطرفة في المتغيرات المالية، لكنه لا يستطيع التفريق بين:

- شركة كبيرة حقيقية.
- خطأ decimal.
- sentinel value.
- currency mismatch.
- data-entry mistake.

مثلاً `employee_count=999999` يختلف نوعيًا عن invoice amount كبير لشركة كبيرة.

## Requirement

كل outlier يجب أن يحصل على **Outlier Reason Profile**:

```text
Statistical extremeness       0.99
Domain plausibility           0.03
Sentinel likelihood           0.97
Cross-field inconsistency     0.88
Data-entry-error likelihood   0.91
```

---

# 125. Profit/Revenue Semantic Checks

ظهرت حالات `reported_profit > annual_revenue`.

هذه قد تكون:

- خطأ.
- اختلاف تعريف revenue/profit.
- اختلاف period.
- اختلاف currency/unit.

إذن يجب دعم **soft accounting/business constraints** مع user confirmation، لا hard-coded repair.

---

# 126. Hard Errors vs Soft Warnings vs Contextual Questions

هذه البيانات أثبتت ضرورة نظام severity متعدد الطبقات:

## Hard Error

أمثلة:

- impossible date `31/02/2025`.
- negative employee count إذا كان تعريفه headcount.
- rating 9.9 إذا scale المؤكد 1–5.

## Strong Suspicion

- `employee_count=999999`.
- conflicting duplicate invoice ID.
- identifier-year mismatch.

## Contextual Warning

- Algeria + EUR.
- profit > revenue.
- overdue record with payment date.

## Informational

- high cardinality.
- skewness.
- statistical outlier بدون violation دلالي.

## Requirement

كل issue يحمل:

```text
severity
confidence
evidence
rule_source
auto_fixable
needs_user_context
impact_if_ignored
```

---

# 127. Rule Source Provenance

يجب أن يعرف المستخدم **من أين جاءت القاعدة**:

```text
Source = physical type inference
Source = statistical rule
Source = data dictionary
Source = inferred relationship
Source = domain pack
Source = user-defined rule
Source = external reference table
Source = LLM suggestion
```

لا يجوز خلط قاعدة مؤكدة من schema مع اقتراح من نموذج ذكاء اصطناعي بنفس مستوى الثقة.

---

# 128. Guided Cleaning Dialog — تطبيق مباشر على هذه البيانات

عند تشغيل Guided Mode يجب أن تظهر قرارات مثل:

## مثال 1 — Dates

```text
4 impossible/ambiguous invoice dates detected.

[Review individually]
[Infer dominant format]
[Set day-first]
[Set month-first]
[Convert invalid to missing]
[Create custom parser]
```

## مثال 2 — Categories

```text
Possible duplicate labels detected:
Algeria / ALGERIA / algeria / Algérie

Suggested canonical: Algeria

[Accept]
[Edit mapping]
[Keep separate]
```

## مثال 3 — Duplicate identifier

```text
Same invoice_id has conflicting records.
Automatic deletion is disabled.

[Compare]
[Choose record]
[Merge fields]
[Define precedence]
[Mark unresolved]
```

## مثال 4 — Currency

```text
Algeria + EUR detected.
This may be legitimate.

[Allow]
[Flag]
[Define currency policy]
```

## مثال 5 — Candidate formula

```text
A possible invoice amount formula was inferred.
101 records violate it.

[Confirm formula]
[Edit formula]
[Do not use this rule]
```

---

# 129. Pre-Cleaning EDA Report — متطلبات أضيفت من الاختبار الواقعي

التقرير الأولي يجب ألا يكتفي بالرسومات التقليدية، بل يعرض:

1. Physical dtype composition لكل عمود.
2. Semantic type inference.
3. Parseability score.
4. Mixed representations.
5. invalid/ambiguous dates.
6. categorical normalization clusters.
7. Unicode/confusable warnings.
8. missingness by semantic context.
9. exact + conflicting duplicates.
10. identifier pattern integrity.
11. range violations.
12. sentinel candidates.
13. cross-field contradictions.
14. candidate derived-field rules.
15. geographic/context inconsistencies.
16. statistical outliers.
17. issue dependency graph.
18. issue severity/confidence matrix.

---

# 130. Post-Cleaning EDA Report — ماذا يجب أن يثبت؟

بعد التنظيف يجب إعادة نفس الاختبارات وعدم الاكتفاء بإظهار أن missing values قلت.

يجب مقارنة:

```text
Issue                         Before    After
------------------------------------------------
Mixed date representations       ...       ...
Impossible dates                   3         0
Conflicting business keys          9         ...
Category aliases                  ...        0
Country-city conflicts            26        ...
Range violations                  ...        0
Sentinel candidates                2        ...
Formula violations               101        ...
Paid-state contradictions         ...       ...
```

ويجب أن يوضح:

- ماذا أصلح تلقائيًا.
- ماذا وافق عليه المستخدم.
- ماذا بقي unresolved.
- ماذا تغير في التوزيعات.
- ماذا تغير في correlations.
- هل حدث information loss.
- هل تغير عدد الصفوف.
- هل تغيرت business totals.

---

# 131. Data Quality Issue Dependency Graph

بعض المشاكل ليست مستقلة.

مثال:

```text
formatted numeric string
        |
        v
wrong dtype
        |
        v
formula check unreliable
```

أو:

```text
country typo
   |
   v
country-currency check false-positive
```

لذلك يجب ألا يتم تنفيذ الفحوص/الإصلاحات بترتيب عشوائي.

## Requirement

إنشاء **Issue Dependency Planner** يحدد مثلًا:

1. normalize representation.
2. parse types.
3. resolve identifiers.
4. canonicalize categories.
5. validate domain constraints.
6. run cross-field rules.
7. run statistical anomaly detection.
8. evaluate impact.

---

# 132. New Core Engine: Data Repair Triage

من نتائج هذا الملف، نقترح إضافة طبقة جديدة باسم:

## `RepairTriageEngine`

وظيفتها وضع كل مشكلة في إحدى الفئات:

```text
SAFE_AUTO_FIX
AUTO_FIX_WITH_LOG
USER_CONFIRMATION_REQUIRED
DOMAIN_RULE_REQUIRED
AMBIGUOUS
UNRESOLVED
DO_NOT_TOUCH
```

مثال:

- trailing whitespace -> `SAFE_AUTO_FIX`.
- `CARD -> Card` -> غالبًا `AUTO_FIX_WITH_LOG`.
- `Tourismm -> Tourism` -> `USER_CONFIRMATION_REQUIRED`.
- `31/02/2025` -> `AMBIGUOUS` بعد إثبات invalidity؛ لا نخترع التاريخ الصحيح.
- conflicting invoice IDs -> `DO_NOT_TOUCH` حتى توجد قاعدة precedence.

---

# 133. Real-Data Acceptance Tests أضيفت إلى المشروع

يجب أن ينجح الإصدار المستقبلي للمكتبة في الاختبارات التالية على dataset مشابه:

- [ ] اكتشاف mixed physical types في `invoice_date`.
- [ ] اكتشاف numeric strings في `unit_price` و`annual_revenue`.
- [ ] فصل invalid dates عن ambiguous date formats.
- [ ] اكتشاف exact duplicates وconflicting duplicate IDs بشكل منفصل.
- [ ] اكتشاف identifier embedded-year mismatch.
- [ ] تجميع variants النصية دون دمج خاطئ تلقائيًا.
- [ ] اكتشاف Unicode confusables.
- [ ] اكتشاف country-city mismatch.
- [ ] تصنيف country-currency mismatch كcontextual warning افتراضيًا.
- [ ] اكتشاف hard range violations.
- [ ] اكتشاف sentinel-like extreme values.
- [ ] اكتشاف conditional missingness contradictions.
- [ ] اكتشاف workflow/state inconsistencies.
- [ ] اقتراح candidate formulas دون افتراض أنها صحيحة.
- [ ] طلب user confirmation للـsemantic/business rules.
- [ ] إنشاء pre-cleaning report.
- [ ] إنشاء post-cleaning report.
- [ ] إنشاء before/after issue diff.
- [ ] حفظ كل قرار في audit trail.
- [ ] تصدير كل قرار ككود reproducible.

---

# 134. نتيجة الاختبار الواقعي على فلسفة المكتبة

هذا الملف يثبت أن التصميم الصحيح لا ينبغي أن يكون:

```text
find problem -> auto fix
```

بل:

```text
Observe
-> Parse representations
-> Infer semantics
-> Detect issue
-> Determine certainty
-> Determine rule provenance
-> Classify severity
-> Distinguish hard error from contextual suspicion
-> Generate alternatives
-> Ask user when context is required
-> Preview
-> Apply
-> Revalidate
-> Compare before/after
-> Log decision
```

وبالتالي يصبح الهدف النهائي للمكتبة ليس فقط **Automatic Cleaning**، وإنما:

> **Evidence-Aware, Context-Aware, Human-Guided Data Preparation**

وهذه نتيجة مهمة أضافها الاختبار الواقعي إلى تصميم المشروع.

---

# 81. توسعة النظام البيئي بعد مراجعة قائمة مكتبات Cleaning / Preprocessing الإضافية

هذا القسم يضيف المكتبات والأنماط الوظيفية التي ظهرت في المراجعة الموسعة ولم تكن ممثلة بما يكفي كـ **Competitor Requirements مستقلة** في الإصدارات السابقة. الهدف ليس إضافة أسماء إلى قائمة، بل تحويل كل مكتبة إلى قدرة يجب أن يرثها SmartPrep أو يقدم بديلًا متفوقًا عليها.

## 81.1 قاعدة Coverage الجديدة

من الآن فصاعدًا يُصنَّف كل منافس أو مكتبة ضمن سجل يسمى:

`Competitor Capability Registry`

ويحتوي لكل مكتبة على:

- الفئة الوظيفية.
- أهم القدرات.
- هل لدينا Feature Parity؟
- هل لدينا Better UX؟
- هل لدينا Better Intelligence؟
- هل لدينا Better Safety؟
- هل لدينا Better Performance؟
- هل لدينا Better Reproducibility؟
- الاختبار الذي يثبت التفوق.
- الإصدار الذي ستدخل فيه الميزة.

لا تعتبر المكتبة المنافسة "مغطاة" بمجرد ذكر اسمها.

---

# 82. RapidFuzz — Fuzzy Matching وCategory Reconciliation

## ما الذي نرثه؟

- string similarity.
- fuzzy matching.
- nearest candidate search.
- typo-tolerant matching.
- ranking of possible matches.
- batch matching على القيم الفئوية.

## ما الذي نضيفه فوقه؟

نبني **Category Reconciliation Studio**:

```text
Raw categories
→ normalize text safely
→ candidate clusters
→ fuzzy similarity
→ frequency-aware evidence
→ semantic evidence
→ user confirmation
→ canonical mapping
→ audit trail
```

الواجهة تعرض مثلًا:

```text
Tourismm  → Tourism       confidence 0.98
Alger     → Algiers       confidence 0.82
Algérie   → Algeria       semantic equivalence candidate
```

ويستطيع المستخدم اختيار:

- Accept.
- Reject.
- Merge.
- Create canonical label.
- Apply to similar cases.
- Save as reusable dictionary.

## القيمة المضافة

لا نعتمد فقط على similarity score، بل على:

- frequency.
- co-occurring columns.
- language detection.
- locale.
- semantic type.
- domain dictionaries.
- historical user decisions.

---

# 83. recordlinkage + dedupe — Entity Resolution Engine

`drop_duplicates()` غير كافٍ في البيانات الواقعية.

## يجب أن ندعم

- exact duplicates.
- subset-key duplicates.
- near duplicates.
- fuzzy duplicates.
- probabilistic record linkage.
- entity clustering.
- cross-table linkage.
- candidate blocking.
- pairwise comparison.
- learned matching rules.

## Smart Entity Resolution Lab

```text
Records
→ Blocking
→ Candidate Pairs
→ Similarity Features
→ Match Probability
→ Cluster Entities
→ Human Review
→ Canonical Record
```

### حالات مهمة

- نفس العميل بأسماء مختلفة.
- نفس المؤسسة بعناوين مختلفة.
- duplicate invoice ID مع بيانات متعارضة.
- سجل موجود في مصدرين مختلفين.

### لا يجوز

دمج السجلات تلقائيًا إذا كانت الأدلة متعارضة.

المحرك يجب أن يقدم:

- match confidence.
- conflicting-field score.
- merge preview.
- field-by-field survivor rule.
- provenance لكل قيمة في السجل النهائي.

---

# 84. ftfy + Unicode normalization + Unidecode — Text Integrity Layer

## المشاكل التي يجب كشفها

- mojibake مثل `FranÃ§ois`.
- Unicode confusables.
- zero-width characters.
- non-breaking spaces.
- inconsistent normalization forms NFC/NFD/NFKC/NFKD.
- visually similar letters من أبجديات مختلفة.
- invisible control characters.
- mixed Arabic/Latin punctuation.
- accidental transliteration.

## Text Repair Engine

يدعم مستويات مختلفة:

### Safe normalization

- whitespace normalization.
- Unicode normalization.
- invisible-character removal.
- encoding repair when confidence is high.

### Destructive normalization

مثل transliteration عبر Unidecode لا تنفذ افتراضيًا، خصوصًا مع العربية.

يجب أن تظهر كـ:

`USER_CONFIRMATION_REQUIRED`

مع Preview واضح لما سيتغير.

## قيمة مضافة

إنشاء **Text Integrity Score** لكل عمود نصي.

---

# 85. dateparser + python-dateutil — Messy Datetime Intelligence

التاريخ ليس مجرد `pd.to_datetime(errors='coerce')`.

## يجب أن يدعم المحرك

- multiple date formats داخل العمود نفسه.
- locale-aware parsing.
- day-first/month-first ambiguity.
- natural-language dates عند الحاجة.
- timezone parsing.
- impossible dates.
- partially specified dates.
- Excel serial dates.
- Unix timestamps.
- mixed date + datetime.
- mixed timezone awareness.
- inconsistent granularity.

## Date Ambiguity Resolver

مثل:

```text
03/04/2026
```

لا يحول بصمت.

يعرض:

```text
Possible interpretations:
2026-04-03   day-first
2026-03-04   month-first
```

ثم يستخدم:

- locale.
- neighboring observations.
- dominant format.
- known date range.
- domain constraints.

لإعطاء confidence، وإذا بقي الغموض يطلب المستخدم.

## Time Integrity Report

- invalid dates.
- ambiguous dates.
- duplicated timestamps.
- missing periods.
- irregular frequency.
- timezone inconsistencies.
- chronological contradictions.

---

# 86. phonenumbers — Phone Semantic Cleaning

ليس كافيًا تطبيق Regex.

## Phone Cleaning Module

- parse phone numbers.
- infer/confirm country code.
- validate plausibility.
- normalize إلى E.164 عند الاختيار.
- separate extensions.
- detect impossible lengths.
- detect text contamination.
- preserve original value.

## Interactive behavior

إذا كان رقم بلا country code ويحتمل أكثر من دولة:

- use country column as evidence.
- offer possible interpretations.
- do not invent a country silently.

---

# 87. email-validator — Email Quality Module

يجب التفريق بين:

- syntax valid.
- normalized representation.
- suspicious domain.
- duplicate email identities.
- disposable/temporary domain إذا توفرت قواعد اختيارية.

ولا ينبغي أن تتحول مكتبة Data Preparation إلى أداة إرسال أو تحقق شبكي إجباري؛ network checks تكون optional وقابلة للإيقاف.

---

# 88. Address Parsing — usaddress وما يقابله دوليًا

بدل بناء `US-only` architecture، ننشئ:

## Pluggable Address Intelligence

يدعم provider adapters حسب الدولة/اللغة.

القدرات:

- address parsing.
- component extraction.
- normalization.
- postal-code validation.
- city-region-country consistency.
- geocoding integration اختياري.

## قاعدة مهمة

العنوان شديد الاعتماد على البلد؛ لذلك Domain Adapter أفضل من قواعد عالمية صلبة.

---

# 89. Pydantic — Row/Object Input Validation

Pandera ممتاز للـDataFrame، لكن المكتبة تحتاج أيضًا طبقة **ingestion validation** للبيانات القادمة record-by-record.

## نرث من Pydantic

- typed input models.
- coercion policies.
- field validators.
- nested records.
- structured error messages.

## القيمة المضافة

إنشاء bridge:

```text
Pydantic-like Record Contract
↕
DataFrame Schema
↕
Data Quality Rules
```

بحيث يمكن تعريف القاعدة مرة واحدة ثم تطبيقها على API ingestion وbatch DataFrame معًا.

---

# 90. AutoClean / Automated Cleaning Libraries — Baseline Automation

يجب دراسة فلسفة الأدوات التي تنفذ cleaning بضغطة واحدة، لكن لا نقلد خطرها.

## نرث

- one-command baseline.
- automated missing handling.
- duplicate removal options.
- encoding defaults.
- datetime extraction.
- outlier options.

## نتفوق عبر Safe Auto Mode

```python
project.clean(mode="auto", confidence_threshold=0.98)
```

ولا ينفذ إلا العمليات التي تحقق شروط السلامة.

كل ما هو غير يقيني ينتقل إلى Guided Queue.

## Auto Mode يجب أن ينتج

- executed operations.
- skipped operations.
- unresolved issues.
- confidence.
- reason.
- rollback checkpoint.

---

# 91. Featuretools — Automated Feature Engineering

لأن Data Preparation لا تنتهي عند cleaning، نضيف طبقة اختيارية للـFeature Engineering.

## نرث

- relational feature generation.
- aggregation primitives.
- transformation primitives.
- entity/table relationships.
- time-aware feature calculation.

## نتفوق عبر Feature Governance

كل feature مولدة يجب أن تحمل:

- lineage.
- source columns.
- transformation definition.
- leakage risk.
- timestamp cutoff awareness.
- complexity score.
- interpretability metadata.

## Feature Proposal Lab

المكتبة لا تولد آلاف features بصمت، بل ترتبها وفق:

- usefulness.
- redundancy.
- leakage risk.
- computational cost.
- interpretability.

---

# 92. SciPy + NumPy — Numerical and Statistical Transformation Foundation

رغم أنهما ليستا Cleaning Frameworks، يجب تمثيل قدراتهما الأساسية داخل engine.

## NumPy-inspired capabilities

- vectorized missing operations.
- clipping.
- conditional replacement.
- numerical transforms.
- stable numerical kernels.

## SciPy-inspired capabilities

- z-score diagnostics.
- Box-Cox.
- Yeo-Johnson via appropriate backend.
- winsorization concepts.
- robust/statistical summaries.
- distribution fitting/tests عند الحاجة.

## القيمة المضافة

أي transformation إحصائي يجب أن يملك:

- assumptions.
- applicability test.
- inverse transformation إن أمكن.
- impact report.
- warning عند خرق الفروض.

---

# 93. Dask — Out-of-Core / Parallel Data Preparation

## نرث

- partitioned DataFrame execution.
- out-of-core processing.
- parallel operations.
- pandas-like mental model.

## SmartPrep Execution Planner

يقرر backend تلقائيًا أو يقترحه:

```text
Small / medium data → Pandas or Polars
Large local data → Polars streaming / DuckDB / Dask
Distributed cluster → Spark
Columnar interchange → Arrow
```

لا ينبغي أن تختلف semantics الأساسية للـcleaning باختلاف backend.

---

# 94. PySpark — Distributed Cleaning + ML Preparation

## القدرات التي يجب أن يكون لها مقابل

- distributed missing handling.
- duplicate handling.
- casting.
- StringIndexer-style category indexing.
- OneHot encoding.
- vector assembly.
- scaling.
- imputation.

## القيمة المضافة

نحتاج **Backend Capability Negotiation**:

إذا كانت عملية معينة غير مدعومة بنفس المعنى في Spark، يجب أن:

1. تعلن الفرق.
2. تعرض fallback.
3. تمنع silent semantic drift.

---

# 95. PyArrow — Schema + Interchange + Columnar Integrity

يجب توسيع حضور Arrow في الخطة من مجرد performance backend إلى طبقة أساسية للـinteroperability.

## متطلبات

- Arrow-compatible schemas.
- nullable types.
- dictionary/categorical representation.
- zero-copy interchange عندما يكون ممكنًا.
- Parquet metadata awareness.
- preservation of logical types.

## قيمة مضافة

### Schema Round-Trip Test

نختبر:

```text
Pandas → Arrow → Polars → Arrow → Pandas
```

ونرصد:

- dtype drift.
- timezone loss.
- categorical loss.
- decimal precision loss.
- null-semantic changes.

---

# 96. DuckDB — SQL-Native Data Preparation

نضيف واجهة SQL كـFirst-Class Citizen لا كإضافة جانبية.

## SQL Preparation Mode

المستخدم يستطيع رؤية العملية كـ:

- Python operation.
- visual node.
- SQL expression عندما تكون قابلة للترجمة.

مثال فلسفي:

```text
trim + lower + try_cast
```

يجب أن يكون قابلاً للتنفيذ عبر backend مناسب مع نفس lineage.

## Query Pushdown

المحرك يحاول دفع filters/projections/casts إلى DuckDB/Parquet قبل تحميل البيانات كاملة.

---

# 97. Domain-Specific Cleaning Registry

المراجعة أوضحت أن المكتبة يجب ألا تتوقف عند generic cleaning.

ننشئ Registry قابلًا للتوسعة:

```text
Email
Phone
URL
IP Address
Country
Currency
Address
Postal Code
ISBN
Coordinates
Date/Time
Measurement Unit
Identifier
Tax ID
Banking Identifier
Language-specific text
```

كل Domain Type يملك:

- detector.
- parser.
- validator.
- normalizer.
- formatter.
- repair candidates.
- confidence rules.
- privacy classification.

---

# 98. Specialized Missing-Data Ecosystem Extension

إضافة إلى sklearn وMICE/FancyImpute، يجب أن يحتفظ التصميم بفكرة أن missingness ليست عملية `fillna` فقط.

## Missing Data Lab يجب أن يدعم

- simple imputation.
- group-wise imputation.
- KNN.
- iterative regression imputation.
- multiple imputation.
- tree/boosting-based imputation adapters.
- low-rank/matrix completion adapters.
- missing indicators.
- structural missingness.
- time-aware interpolation.
- panel-aware treatment.

## Imputation Evaluation

لكل طريقة:

- distribution preservation.
- correlation preservation.
- uncertainty.
- downstream stability.
- runtime.
- memory.
- leakage risk.

---

# 99. Expanded Interactive Studio Based on the Added Ecosystem

المكتبات الجديدة تضيف Workbenches جديدة إلى الواجهة:

## 99.1 Text Integrity Workbench

- Unicode issues.
- mojibake.
- confusables.
- whitespace/control chars.
- transliteration preview.

## 99.2 Entity Resolution Workbench

- duplicate clusters.
- candidate matches.
- merge preview.
- survivor rules.
- provenance.

## 99.3 Date Intelligence Workbench

- format distribution.
- invalid dates.
- ambiguity queue.
- timezone panel.
- frequency/gap diagnostics.

## 99.4 Semantic Field Workbench

لـ:

- phone.
- email.
- address.
- country.
- currency.
- URL.
- identifiers.

## 99.5 Feature Engineering Workbench

- proposed features.
- lineage graph.
- leakage risk.
- relevance/redundancy.

## 99.6 Backend Execution Panel

يعرض:

- selected backend.
- estimated memory.
- estimated runtime class.
- pushdown opportunities.
- unsupported operation warnings.

---

# 100. Updated Superset Acceptance Checklist

لا تُعد SmartPrep منافسًا شاملًا حتى تنجح في الاختبارات الآتية:

## Cleaning

- [ ] exact duplicates.
- [ ] conflicting duplicates.
- [ ] fuzzy duplicate detection.
- [ ] entity resolution.
- [ ] category fuzzy reconciliation.
- [ ] Unicode/encoding repair.
- [ ] mixed-format date parsing.
- [ ] ambiguous date handling.
- [ ] phone validation/normalization.
- [ ] email validation/normalization.
- [ ] pluggable address parsing.
- [ ] country/currency/geography consistency.
- [ ] semantic domain cleaning.

## Preprocessing

- [ ] scaling family.
- [ ] normalization family.
- [ ] power transformations.
- [ ] categorical encoding families.
- [ ] dirty/high-cardinality category encoding.
- [ ] simple + advanced + multiple imputation.
- [ ] class-imbalance strategies.
- [ ] feature engineering.
- [ ] feature selection.
- [ ] dimensionality-reduction adapters.

## Validation

- [ ] DataFrame schemas.
- [ ] row/object validation.
- [ ] batch + streaming contracts.
- [ ] cross-column rules.
- [ ] candidate invariant discovery.
- [ ] hard vs soft rule semantics.

## Interactive

- [ ] fuzzy-category review UI.
- [ ] entity-resolution review UI.
- [ ] date ambiguity review UI.
- [ ] semantic-field cleaning UI.
- [ ] before/after interactive EDA.
- [ ] treatment sandbox.
- [ ] visual pipeline DAG.
- [ ] every click reproducible as code.

## Execution

- [ ] Pandas.
- [ ] Polars.
- [ ] Arrow interchange.
- [ ] DuckDB pushdown.
- [ ] Dask/out-of-core adapter.
- [ ] Spark/distributed adapter.
- [ ] backend semantic-equivalence tests.

## Safety and reproducibility

- [ ] confidence-aware repair.
- [ ] abstention when uncertain.
- [ ] original-value preservation.
- [ ] undo/rollback.
- [ ] audit trail.
- [ ] lineage.
- [ ] code export.
- [ ] schema round-trip tests.
- [ ] leakage guard.

---

# 101. Updated Competitive Formula

بعد هذه التوسعة، الهدف لم يعد فقط جمع أدوات profiling/cleaning/preprocessing الكبرى، بل تغطية النظام البيئي المتخصص أيضًا:

```text
Profiling / EDA
+ Interactive visual exploration
+ Data quality / validation
+ General cleaning
+ Semantic/domain cleaning
+ Fuzzy category reconciliation
+ Entity resolution
+ Unicode/text integrity
+ Date intelligence
+ Phone/email/address validation
+ Missing-data science
+ Outlier/anomaly detection
+ Categorical encoding
+ Dirty/high-cardinality encoding
+ Scaling/transformation
+ Imbalanced learning preparation
+ Automated feature engineering
+ Row/object contracts
+ DataFrame contracts
+ Multi-backend execution
+ Distributed/out-of-core execution
+ Arrow interoperability
+ SQL pushdown
+ Recommendation intelligence
+ Human-in-the-loop decisions
+ Explainability
+ Impact evaluation
+ Versioning/audit/lineage
+ Static + interactive pre/post EDA reports
```

التميّز الحقيقي ليس أن تكون كل هذه الميزات موجودة فقط، بل أن تعمل كلها داخل **نموذج قرار موحد**:

```text
Detect
→ Classify
→ Explain
→ Recommend
→ Compare
→ Ask when uncertain
→ Preview
→ Apply
→ Validate
→ Measure impact
→ Record decision
→ Reproduce
```

وهذا هو معيار التفوق الذي يجب الحفاظ عليه في كل إصدار من المشروع.

---

# 102. التدقيق العميق النهائي قبل الإطلاق — Final Deep Gap Audit (2026)

بعد مراجعة إضافية للأدوات الحديثة في Data Quality، Data Observability، Streaming ML، Data Contracts، Data Lineage، Privacy، Multi-backend execution، Interactive Data Editing، Synthetic Data، وProduction Monitoring، ظهرت طبقات لم يكن من المناسب تركها كإضافات اختيارية. بعض هذه الطبقات يجب أن تدخل في الـCore Architecture منذ البداية حتى لا يصبح من الصعب إضافتها لاحقًا.

الهدف من هذا القسم ليس إضافة أسماء مكتبات جديدة فقط، بل تحويل أفضل الأفكار الموجودة في النظام البيئي إلى **متطلبات تصميم Superset Requirements** مع قيم مضافة خاصة بمكتبتنا.

المراجع الرسمية الأساسية لهذه الجولة تشمل:

- Frictionless Framework: https://framework.frictionlessdata.io/
- Pointblank: https://posit-dev.github.io/pointblank/
- whylogs: https://whylogs.readthedocs.io/
- Alibi Detect: https://docs.seldon.ai/alibi-detect/
- River: https://riverml.xyz/
- OpenLineage: https://openlineage.io/docs/
- Narwhals: https://narwhals-dev.github.io/narwhals/
- Ibis: https://ibis-project.org/
- Presidio: https://presidio.dataprivacystack.org/
- Panel Tabulator: https://panel.holoviz.org/reference/widgets/Tabulator.html
- SDV: https://docs.sdv.dev/

---

# 103. Continuous Data Quality & Data Observability — لا تنتهي المكتبة بعد clean()

معظم مكتبات Cleaning تتعامل مع Dataset كجسم ثابت: ندخله، ننظفه، ننتهي. لكن البيانات الحقيقية تتغير مع الزمن.

يجب أن تضيف المكتبة مفهوم:

## Continuous Data Preparation

أي أن نفس قواعد Cleaning/Validation التي أنشأها المستخدم للبيانات الحالية يمكن تشغيلها لاحقًا على دفعات جديدة من البيانات.

المطلوب:

```text
Reference Dataset / Baseline
        ↓
New Batch / New Period
        ↓
Profile
        ↓
Quality Comparison
        ↓
Drift Detection
        ↓
Rule Violations
        ↓
Alert / Review / Auto Action
```

## ما الذي نتعلمه من whylogs؟

whylogs يعتمد على lightweight statistical profiles قابلة للدمج ومناسبة للمراقبة المستمرة، ويتيح constraints ومقارنة profiles واكتشاف drift.

يجب أن توفر المكتبة:

- DatasetProfile snapshots.
- Mergeable profiles.
- Reference profiles.
- Time-indexed profiles.
- Segment-specific profiles.
- Data quality trend charts.
- Missingness trend.
- Cardinality drift.
- Type drift.
- Distribution drift.
- Category emergence/disappearance.
- Null-rate drift.
- Range drift.
- Text-length drift.
- Unicode-range drift.

## قيمة مضافة مقترحة: Cleaning Drift

ليس فقط Data Drift، بل:

**Cleaning Drift** = تغير طبيعة الأخطاء التي تحتاج تنظيفًا عبر الزمن.

مثال:

```text
January:
2% missing
0.5% invalid dates

February:
2.1% missing
0.4% invalid dates

March:
18% invalid dates
```

المكتبة يجب أن تقول:

```text
New upstream formatting issue likely started in March.
Possible source-system change detected.
```

## Cleaning Stability Score

مقياس جديد:

```text
Cleaning Stability Score = 0..100
```

ويقيس مدى ثبات قواعد التنظيف عبر batches.

إذا كانت كل دفعة تحتاج قواعد جديدة، فهذا مؤشر أن المشكلة upstream وليست مجرد مشكلة تنظيف محلية.

---

# 104. Drift Intelligence Layer — من Cleaning إلى Data Reliability

Alibi Detect يوضح أهمية الفصل بين:

- Outliers.
- Data Drift.
- Concept Drift.
- Online Drift.
- Mixed-type tabular drift.

لذلك يجب ألا تكون مقارنة Before/After هي المقارنة الوحيدة.

نضيف:

## `DriftLab`

يدعم:

### Univariate drift

- KS.
- Chi-square.
- Fisher exact.
- Cramér-von Mises.
- PSI.
- Jensen-Shannon divergence.
- Wasserstein distance.

### Multivariate drift

- MMD.
- Classifier-based drift.
- Learned-kernel drift.
- Mixed-type drift.

### Context-aware drift

مثال:

ارتفاع متوسط الدخل قد يبدو Drift، لكنه طبيعي إذا تغيرت عينة المناطق الجغرافية.

المكتبة يجب أن تسمح بمقارنة drift conditional on context.

## Drift Severity

```text
NONE
MINOR
MODERATE
SEVERE
CRITICAL
```

## Drift Explanation

ليس:

```text
Drift detected = True
```

بل:

```text
Primary contributors:
region              42%
income              28%
payment_method      17%
age                  13%
```

## Cleaning vs Drift Separation

يجب ألا تعتبر المكتبة كل اختلاف distribution خطأ تنظيف.

```text
Data error?          → Cleaning
Natural population shift? → Drift
System/schema change? → Data Contract violation
Model-related shift? → Monitoring
```

---

# 105. Streaming / Online Preprocessing — إضافة River Philosophy

هذه فجوة مهمة جدًا في معظم مكتبات Data Preparation التقليدية.

River يقدم مفهوم Online / Incremental preprocessing حيث الإحصاءات تتحدث مع كل observation أو mini-batch بدل الحاجة إلى إعادة fit على Dataset كاملة.

نضيف:

## `StreamingPrep`

يدعم:

- incremental mean/variance.
- online StandardScaler.
- online MinMax estimates where appropriate.
- incremental categorical statistics.
- rolling missingness.
- rolling outlier thresholds.
- online anomaly detection.
- online drift detection.
- streaming feature extraction.

API مقترحة:

```python
prep = SmartPrep.streaming()

for batch in stream:
    result = prep.update(batch)
```

أو:

```python
prep.learn_one(row)
clean_row = prep.transform_one(row)
```

## Streaming Safety

المشكلة الأساسية أن preprocessing في streaming لا يمتلك المستقبل.

لذلك يجب أن تفرق المكتبة بين:

```text
Batch-safe operation
Online-safe operation
Requires future information
```

مثال:

Centered rolling mean قد يستخدم future observations إذا كتب بطريقة خاطئة.

نضيف:

### Temporal Causality Guard

يمنع أي transformation تستخدم معلومات مستقبلية عند تشغيل Time Series / Forecasting mode.

---

# 106. Data Contracts + Schema Evolution — من Validation إلى اتفاق رسمي

Pandera وGreat Expectations يعالجان validation، لكن Frictionless يضيف فكرة قوية جدًا: البيانات ليست فقط DataFrame بل Resource + Schema + Metadata + Validation + Transformation.

نضيف مفهوم:

## `DataContract`

يشمل:

```yaml
name: invoices
version: 2.1
columns:
  invoice_id:
    semantic_type: identifier
    nullable: false
    unique: true

  invoice_date:
    semantic_type: datetime
    timezone: Africa/Algiers

  amount:
    semantic_type: currency
    currency_column: currency
```

إضافة إلى:

- expected columns.
- optional columns.
- forbidden columns.
- dtype constraints.
- semantic types.
- allowed categories.
- units.
- locale.
- null policy.
- uniqueness.
- primary keys.
- foreign keys.
- row constraints.
- cross-column rules.
- distribution expectations.

## Schema Evolution Engine

عند وصول Dataset جديدة:

```text
Added column
Removed column
Renamed column candidate
Type widened
Type narrowed
Nullable changed
Category set changed
Unit changed
Timezone changed
```

ثم تصنيف التغيير:

```text
Backward compatible
Forward compatible
Breaking change
Potential semantic breaking change
```

## Contract Diff

```python
contract.diff(old, new)
```

## Contract-to-Code

يمكن تحويل Contract إلى:

- Pandera schema.
- Pydantic models.
- Frictionless schema.
- SQL DDL checks.
- JSON Schema.
- YAML.

وهذه قيمة مضافة قوية: **One semantic contract, multiple validation targets**.

---

# 107. Pointblank-inspired Validation Experience — Validation يجب أن تكون قابلة للفهم

من أقوى الأفكار الحديثة في Pointblank أن validation ليست فقط exception؛ بل Validation Plan ثم Interrogation ثم تقرير واضح مع مستويات Warning/Error/Critical وإمكانية استخراج failing rows.

يجب إضافة:

## `ValidationPlan`

```python
plan = (
    project.validate()
    .column_exists("customer_id")
    .between("rating", 1, 5)
    .unique("invoice_id")
    .custom("payment <= invoice")
)
```

ثم:

```python
result = plan.run()
```

## Validation Thresholds

كل Rule تدعم:

```text
PASS
WARNING
ERROR
CRITICAL
```

بناءً على:

- absolute number of failures.
- percentage of failures.
- weighted severity.
- business impact.

## Sundered Data

ميزة مهمة:

```python
valid_rows, invalid_rows = result.split()
```

أو UI:

```text
Show passing rows
Show failing rows
Show only critical violations
```

## Validation Conversation

التقرير لا يكتفي بـ:

```text
Rule failed
```

بل:

```text
1,238 rows evaluated
27 failed (2.18%)
Threshold for warning = 1%
Threshold for error = 5%
Current state = WARNING
```

---

# 108. Privacy, PII & Sensitive Data Preparation — Presidio-inspired layer

هذه إضافة أراها أساسية إذا كانت المكتبة ستستخدم في الشركات أو الأبحاث أو البيانات الإدارية.

Presidio يوضح أن PII detection يمكن أن يعتمد على:

- NER.
- regex.
- rule-based logic.
- checksums.
- contextual evidence.
- custom recognizers.

نضيف:

## `PrivacyScanner`

يكتشف على مستوى الأعمدة والخلايا:

- names.
- email.
- phone.
- national identifiers.
- credit cards.
- bank account numbers.
- IP addresses.
- geographic identifiers.
- passport IDs.
- free-text PII.

## Column Privacy Classification

```text
PUBLIC
INTERNAL
CONFIDENTIAL
SENSITIVE
DIRECT_IDENTIFIER
QUASI_IDENTIFIER
```

## Privacy Actions

- mask.
- redact.
- hash.
- tokenize.
- pseudonymize.
- generalize.
- bucket.
- drop.
- encrypt through plugin/integration.

## Privacy Preview

قبل التطبيق:

```text
Original                  Preview
m.roudane@email.com       m******@email.com
0555123456                055*****56
```

## Privacy Risk Score

لا يقتصر على وجود PII؛ بل يحاول تقييم إعادة التعرف عبر quasi-identifiers.

## قاعدة مهمة

أي PII detector يجب أن يعرض Confidence وPotential False Negative warning، لأن الكشف الآلي لا يمكن اعتباره ضمانًا مطلقًا.

---

# 109. Data Lineage & Provenance — OpenLineage-inspired architecture

لدينا Audit Trail على مستوى التغييرات، لكن نحتاج مستوى أعلى: من أين جاءت البيانات؟ ومن أي Dataset؟ وما العملية التي أنتجت Dataset الحالية؟

OpenLineage يقدم نموذجًا عامًا:

```text
Dataset
Job
Run
```

نضيف:

## `LineageGraph`

```text
raw_sales.xlsx
     ↓
Import
     ↓
TypeNormalization
     ↓
MissingTreatment
     ↓
CategoryRepair
     ↓
validated_sales.parquet
     ↓
FeatureEngineering
     ↓
model_ready.parquet
```

كل Node يجب أن يحتوي:

- operation ID.
- timestamp.
- input dataset hash.
- output dataset hash.
- code/config version.
- environment.
- library version.
- user decision where applicable.
- columns affected.

## Column-level lineage

مثال:

```text
net_amount
  ← gross_amount
  ← discount_pct
  ← tax_pct
```

## Lineage Export

- OpenLineage-compatible events.
- JSON.
- GraphML.
- Mermaid.
- interactive DAG.

---

# 110. Reproducibility Beyond Code — Dataset Fingerprinting & Environment Capture

توليد Python code وحده لا يكفي لإعادة إنتاج cleaning فعليًا.

نضيف:

## Dataset Fingerprint

يحسب:

- file hash.
- schema hash.
- row count.
- column count.
- column-order hash.
- sampled content fingerprint.
- optional full content hash.

## Environment Manifest

يحفظ:

```text
Python version
OS
SmartPrep version
backend
pandas/polars version
locale
timezone
random seeds
operation configuration
```

## Determinism Test

تشغيل pipeline مرتين على نفس البيانات يجب أن ينتج نفس output عندما تكون العمليات deterministic.

## Idempotence Test

قاعدة قوية جدًا للتنظيف:

```text
clean(clean(df)) == clean(df)
```

ليست كل transformation يجب أن تكون idempotent، لكن معظم Cleaning rules ينبغي أن تكون كذلك.

نضيف:

```python
project.test_idempotence()
```

وتقرير:

```text
clean_names           PASS
trim_strings          PASS
currency_parse        PASS
custom_rule_17        FAIL
```

هذه إضافة يمكن أن تميز المكتبة أكاديميًا وتقنيًا.

---

# 111. Backend-Agnostic Core — Narwhals + Ibis Architecture

الخطة السابقة تضمنت Multi-backend، لكن التدقيق الجديد يشير إلى أن الأمر يجب أن يكون **قرارًا معماريًا أساسيًا** لا adapters متأخرة.

Narwhals يوضح إمكانية بناء مكتبة dataframe-agnostic مع overhead منخفض، بينما Ibis يوفر expression layer يمكن تشغيلها على عدد كبير من backends المحلية وقواعد البيانات.

## Architecture مقترحة

```text
User API
   ↓
Semantic Operation IR
   ↓
Backend Capability Planner
   ↓
-----------------------------------
Pandas | Polars | Arrow | DuckDB
Ibis   | Dask   | Spark | SQL
-----------------------------------
```

## Intermediate Representation — IR

كل عملية تنظيف تمثل كـ operation مستقلة عن backend:

```json
{
  "operation": "trim_strings",
  "columns": ["city"],
  "null_policy": "preserve"
}
```

ثم compiler يحولها إلى:

- pandas code.
- Polars expression.
- SQL expression.
- Spark expression.

## Backend Capability Matrix

مثال:

```text
Operation                Pandas   Polars   DuckDB   Spark
trim strings             ✓        ✓        ✓        ✓
fuzzy entity resolution  ✓        ✓*       limited  distributed*
MICE                     ✓        convert  no       plugin
```

## No Silent Fallback Rule

إذا لم يدعم backend عملية معينة، لا يجوز التحويل إلى Pandas بصمت إذا كانت البيانات ضخمة.

يجب أن تقول المكتبة:

```text
Operation requires materialization into Pandas.
Estimated memory: 14.2 GB
Proceed / choose alternative / skip
```

---

# 112. Interactive Data Grid 2.0 — الاستفادة من Panel/Tabulator

الـInteractive Grid يجب أن يصبح Workbench حقيقيًا.

Panel Tabulator يقدم أفكارًا مهمة مثل editing، selection، filtering، callbacks، streaming، patching، pagination، nested editors.

نضيف إلى SmartPrep Grid:

## Editing

- editable cells.
- typed editors.
- dropdown categories.
- date picker.
- checkbox Boolean.
- number constraints.

## Conditional Editors

خيارات عمود تعتمد على عمود آخر.

مثال:

```text
country = Algeria
→ city options = Alger, Oran, Constantine...
```

## Cell-level Issue Badges

كل خلية يمكن أن تحمل:

```text
MISSING
TYPE_MISMATCH
OUTLIER
RULE_VIOLATION
PII
AMBIGUOUS_DATE
DUPLICATE_KEY
```

## Cell History

عند الضغط:

```text
Raw value
Normalized value
Current value
Who/what changed it
Rule ID
Confidence
Timestamp
Undo
```

## Selection-as-Rule

إذا اختار المستخدم مجموعة خلايا/صفوف، يمكنه:

```text
Create cleaning rule from selection
Mark as valid exception
Add to allowlist
Quarantine
```

## Streaming Grid

يمكن للجدول استقبال batches جديدة دون إعادة تحميل التطبيق كله.

---

# 113. Large-Data Visualization Strategy — لا ترسم مليون نقطة مباشرة

الرسومات التفاعلية مهمة، لكن Plotly وحده ليس كافيًا لكل الأحجام.

يجب أن يحتوي Visualization Engine على Planner:

```text
Small data
→ full plot

Medium data
→ sampling / aggregation

Large data
→ server-side aggregation / rasterization

Streaming data
→ rolling window / incremental aggregation
```

## Visual Fidelity Guard

يجب أن يسجل التقرير إذا كان الرسم مبنيًا على:

```text
FULL DATA
RANDOM SAMPLE
STRATIFIED SAMPLE
AGGREGATED DATA
RASTERIZED DATA
```

حتى لا يعتقد المستخدم أن الرسم يمثل كل النقاط وهو في الحقيقة sample.

## Distribution-preserving sampling

اقتراح sampling يحافظ قدر الإمكان على:

- target balance.
- tails.
- rare categories.
- outliers.
- temporal coverage.

---

# 114. Synthetic Data as a Diagnostic Tool — SDV-inspired but not default replacement

Synthetic Data ليست Cleaning، لكن يمكن استخدامها كأداة تشخيص واختبار قوية.

SDV يركز على metadata وstatistical similarity وcolumn-pair trends وcardinality.

نضيف Optional Module:

## `SyntheticSandbox`

الاستخدامات:

1. اختبار pipeline بدون كشف البيانات الأصلية.
2. إنشاء examples للوثائق.
3. stress-testing للقواعد.
4. توليد rare edge cases.
5. مقارنة تأثير cleaning على structure.

## Synthetic Quality Report

- column shapes.
- pairwise trends.
- cardinality.
- constraint adherence.
- privacy risk checks.

## ممنوع افتراضيًا

لا تستخدم synthetic rows لتعويض missing observations في dataset العلمية تلقائيًا دون قرار صريح؛ فهذا موضوع مختلف عن imputation.

---

# 115. Data Documentation & Dataset Card Generator

المكتبة يجب أن تنتج إلى جانب EDA report وثيقة وصف Dataset.

## `DatasetCard`

تحتوي:

- source.
- acquisition date.
- owner/producer.
- license if known.
- tables.
- keys.
- variables.
- semantic types.
- units.
- missingness.
- known limitations.
- cleaning operations.
- unresolved issues.
- privacy classification.
- intended use.
- prohibited/unsafe uses.
- transformation history.

## Variable Dictionary

يولد Data Dictionary قابلًا للتعديل من المستخدم.

```text
Variable
Technical dtype
Semantic type
Description
Unit
Allowed values
Missing policy
Source
Derived from
```

ويمكن تصديره إلى HTML / Markdown / PDF / CSV / Excel.

---

# 116. Root-Cause & Upstream Diagnosis — لا تعالج العرض فقط

إذا كان نفس الخطأ يتكرر، يجب أن تحاول المكتبة اكتشاف مصدره.

مثال:

```text
invalid_date format appears only when source_file = branch_03.xlsx
```

فتقترح:

```text
Likely upstream source-specific formatting issue.
```

## Root Cause Dimensions

- source file.
- ingestion batch.
- sheet.
- API source.
- branch/site.
- user/operator.
- period.
- device/system.

## Issue Clustering

بدل 10,000 warning منفصلة:

```text
Cluster #17
8,423 rows
Root pattern: comma decimal separator
Source: ERP export v4
First observed: 2026-07-01
```

هذه من أهم القيم المضافة للشركات.

---

# 117. Cleaning Rule Learning — من قرارات المستخدم إلى Knowledge Base

كل مرة يؤكد المستخدم قرارًا يمكن للمكتبة التعلم منه محليًا.

مثال:

```text
"Algérie" → "Algeria"
```

بعد عدة datasets يمكن اقتراح نفس mapping بثقة أعلى.

## Rule Memory

تنقسم إلى:

```text
Project rules
Organization rules
Domain rules
Global built-in rules
```

## Rule Provenance

كل قاعدة لديها:

- origin.
- creator.
- evidence.
- confidence.
- last used.
- datasets applied to.
- failure history.

## No Blind Generalization

قاعدة تعلمت من Dataset واحدة لا تصبح Global Rule تلقائيًا.

---

# 118. Property-based & Metamorphic Testing for Data Preparation

إضافة مبتكرة مهمة للجودة البرمجية.

بدل اختبار مثال واحد فقط، يجب اختبار خصائص العملية.

## Properties

### Idempotence

```text
normalize(normalize(x)) == normalize(x)
```

### Row preservation

عملية rename columns يجب ألا تغير عدد الصفوف.

### Missingness monotonicity

عملية fill missing يجب ألا تزيد missingness إلا إذا كان ذلك مقصودًا.

### Type guarantee

بعد currency parser:

```text
all successfully parsed values must be numeric
```

### Range guarantee

بعد clipping:

```text
min >= lower_bound
max <= upper_bound
```

## Metamorphic tests

مثال:

ترتيب الصفوف قبل cleaning لا يجب أن يغير النتيجة في عمليات غير زمنية.

```text
clean(shuffle(df))
≈ shuffle(clean(df))
```

هذه الاختبارات تجعل المكتبة أقرب إلى infrastructure موثوق وليس مجموعة functions.

---

# 119. Uncertainty as a First-Class Object

الخطة تحتوي Confidence، لكن يجب جعل uncertainty جزءًا من API نفسها.

بدل أن تعيد الدالة قيمة فقط:

```python
result = parse_date(value)
```

يمكن أن تعيد:

```text
value: 2026-08-03
confidence: 0.61
alternatives:
  - 2026-03-08: 0.39
reason: locale ambiguity
```

## Decision Policy

```text
confidence >= .98 → safe auto
.85-.98 → auto with log
.60-.85 → guided review
< .60 → abstain
```

## Calibration

يجب تقييم هل confidence نفسها calibrated أم لا.

إذا قالت المكتبة 90% confidence على 100 قرار، يجب أن يكون تقريبًا 90 منها صحيحًا في benchmark مناسب.

---

# 120. Benchmark Suite — كيف نثبت أن المكتبة أفضل؟

هذه إضافة ضرورية قبل ادعاء التفوق.

ننشئ:

## `SmartPrepBench`

يتضمن datasets مصممة لكل مشكلة:

- mixed types.
- corrupted dates.
- missing mechanisms.
- duplicate entities.
- Unicode confusables.
- unit mismatches.
- currencies.
- schema drift.
- category drift.
- label errors.
- outliers.
- time-series gaps.
- panel inconsistencies.
- PII.
- multilingual dirty text.

## مقاييس

### Detection

- precision.
- recall.
- F1.
- false-positive rate.

### Repair

- exact repair accuracy.
- semantic repair accuracy.
- information loss.
- distribution distortion.

### Recommendation

- expert agreement.
- downstream performance impact.
- statistical preservation.

### Performance

- runtime.
- peak memory.
- scalability.

### UX

- clicks to resolution.
- time to resolve issue.
- undo success.
- reproducibility success.

## Competitor Matrix

تشغيل نفس benchmark على:

```text
pandas
PyJanitor
DataPrep
YData Profiling
Sweetviz
Pandera
Pointblank
Great Expectations
AutoClean
skrub
Feature-engine
scikit-learn
PyOD
Cleanlab
```

مع توضيح أن بعض المكتبات ليست منافسًا مباشرًا وإنما baseline لفئة معينة.

---

# 121. Plugin Architecture — شرط أساسي للاستدامة

لا يمكن وضع كل domain داخل core package.

لذلك:

```text
smartprep-core
smartprep-viz
smartprep-ml
smartprep-timeseries
smartprep-panel
smartprep-privacy
smartprep-geospatial
smartprep-text
smartprep-spark
smartprep-econometrics
```

## Plugin Interface

يمكن للمطور إنشاء:

- detector.
- repairer.
- validator.
- transformer.
- semantic type.
- report panel.
- visualization.
- backend compiler.

بدون تعديل core.

---

# 122. Dependency Isolation & Optional Extras

بسبب كثرة المكتبات الثقيلة وتعارض dependencies، يجب ألا تصبح المكتبة monolithic.

مثال تثبيت:

```bash
pip install smartprep
pip install "smartprep[viz]"
pip install "smartprep[ml]"
pip install "smartprep[privacy]"
pip install "smartprep[spark]"
pip install "smartprep[all]"
```

## Capability Detection

```python
project.capabilities()
```

يعرض:

```text
Plotly       available
PyArrow      available
Presidio     not installed
Spark        not installed
MICE         available
```

بدل crash غير مفهوم.

---

# 123. Final Architecture بعد التدقيق الأخير

```text
                           ┌──────────────────────────────┐
                           │        USER / API / UI       │
                           └──────────────┬───────────────┘
                                          ↓
                           ┌──────────────────────────────┐
                           │   Project + Data Contract    │
                           └──────────────┬───────────────┘
                                          ↓
┌──────────────────────────────────────────────────────────────────┐
│                         UNDERSTANDING LAYER                       │
│ Profiling | Semantic Types | PII | Schema | Metadata | Lineage   │
└──────────────────────────────────────────────────────────────────┘
                                          ↓
┌──────────────────────────────────────────────────────────────────┐
│                         DIAGNOSIS LAYER                           │
│ Missing | Types | Dates | Duplicates | Rules | Outliers | Drift  │
│ Text | Entities | Time/Panel | Cross-field | Upstream Root Cause │
└──────────────────────────────────────────────────────────────────┘
                                          ↓
┌──────────────────────────────────────────────────────────────────┐
│                       DECISION INTELLIGENCE                       │
│ Evidence | Confidence | Risk | Alternatives | Abstention         │
│ Counterfactual Evaluation | User Guidance | Learned Rules        │
└──────────────────────────────────────────────────────────────────┘
                                          ↓
┌──────────────────────────────────────────────────────────────────┐
│                         PREPARATION ENGINE                        │
│ Cleaning | Imputation | Encoding | Scaling | Feature Engineering │
│ Privacy | Validation | Streaming | Domain-specific Operations    │
└──────────────────────────────────────────────────────────────────┘
                                          ↓
┌──────────────────────────────────────────────────────────────────┐
│                         EXECUTION LAYER                           │
│ IR | Narwhals | Ibis | Pandas | Polars | Arrow | DuckDB | Spark │
└──────────────────────────────────────────────────────────────────┘
                                          ↓
┌──────────────────────────────────────────────────────────────────┐
│                        ASSURANCE LAYER                            │
│ Validation | Impact | Preservation | Idempotence | Reproducibility│
│ Contract Diff | Drift | Privacy | Benchmarks                      │
└──────────────────────────────────────────────────────────────────┘
                                          ↓
┌──────────────────────────────────────────────────────────────────┐
│                     REPORTING / INTERACTIVE IDE                   │
│ Pre-EDA | Post-EDA | Before/After | Grid | Sandbox | DAG | Audit │
│ Static Reports | Interactive HTML | PDF | Monitoring Dashboard    │
└──────────────────────────────────────────────────────────────────┘
```

---

# 124. Final Superset Checklist — بعد التدقيق العميق

قبل اعتبار النسخة 1.0 متفوقة وظيفيًا، يجب أن تغطي الفئات التالية.

## A. Understand

- [ ] Technical dtype inference.
- [ ] Semantic type inference.
- [ ] Probabilistic type inference.
- [ ] Dataset metadata.
- [ ] Data dictionary.
- [ ] PII/sensitivity scan.
- [ ] Schema inference.
- [ ] Relationship/key inference.

## B. Diagnose

- [ ] Missingness.
- [ ] hidden missing tokens.
- [ ] mixed types.
- [ ] invalid dates.
- [ ] ambiguous dates.
- [ ] duplicates.
- [ ] near duplicates.
- [ ] entity resolution.
- [ ] outliers.
- [ ] anomalies.
- [ ] Unicode corruption.
- [ ] categorical inconsistency.
- [ ] cross-column contradictions.
- [ ] formula/invariant violations.
- [ ] time-series gaps.
- [ ] panel inconsistencies.
- [ ] schema drift.
- [ ] data drift.
- [ ] cleaning drift.
- [ ] source-specific root causes.

## C. Decide

- [ ] alternatives.
- [ ] recommendation score.
- [ ] calibrated confidence.
- [ ] risk score.
- [ ] abstention.
- [ ] human approval.
- [ ] expected impact.
- [ ] runtime/memory cost.
- [ ] leakage risk.

## D. Repair / Preprocess

- [ ] names.
- [ ] strings.
- [ ] Unicode.
- [ ] dates.
- [ ] missing data.
- [ ] duplicates/entity resolution.
- [ ] categorical normalization.
- [ ] numeric parsing.
- [ ] units/currencies.
- [ ] semantic fields.
- [ ] outlier treatments.
- [ ] encoding.
- [ ] scaling.
- [ ] transformations.
- [ ] feature engineering.
- [ ] resampling.
- [ ] dimensionality reduction.
- [ ] privacy transformations.
- [ ] online/streaming transformations.

## E. Validate

- [ ] row rules.
- [ ] column rules.
- [ ] schema rules.
- [ ] cross-column rules.
- [ ] cross-table rules.
- [ ] primary/foreign keys.
- [ ] severity thresholds.
- [ ] extract failing rows.
- [ ] Data Contract.
- [ ] Contract diff.

## F. Explain / Audit

- [ ] why issue was detected.
- [ ] why treatment recommended.
- [ ] why alternative rejected.
- [ ] user decision recorded.
- [ ] operation lineage.
- [ ] column lineage.
- [ ] dataset fingerprint.
- [ ] environment manifest.

## G. Assure

- [ ] Before/After statistics.
- [ ] distribution preservation.
- [ ] correlation preservation.
- [ ] information-loss score.
- [ ] idempotence test.
- [ ] determinism test.
- [ ] leakage guard.
- [ ] temporal causality guard.
- [ ] privacy risk.

## H. Interactive

- [ ] editable smart grid.
- [ ] typed editors.
- [ ] nested editors.
- [ ] issue badges.
- [ ] linked charts.
- [ ] selection-as-rule.
- [ ] treatment sandbox.
- [ ] visual rule builder.
- [ ] pipeline DAG.
- [ ] undo/redo.
- [ ] history.
- [ ] pre/post toggle.
- [ ] dynamic reports.
- [ ] streaming updates.

## I. Reports

- [ ] Pre-Cleaning EDA.
- [ ] Post-Cleaning EDA.
- [ ] Before/After comparison.
- [ ] Validation report.
- [ ] Audit report.
- [ ] Privacy report.
- [ ] Drift report.
- [ ] Data Contract report.
- [ ] Dataset Card.
- [ ] Executive report.
- [ ] Technical report.
- [ ] HTML interactive.
- [ ] PDF static.
- [ ] Markdown.
- [ ] JSON/YAML machine-readable.

## J. Execution

- [ ] Pandas.
- [ ] Polars.
- [ ] Arrow.
- [ ] DuckDB.
- [ ] Ibis.
- [ ] Dask.
- [ ] Spark.
- [ ] SQL pushdown.
- [ ] streaming.
- [ ] backend capability planner.
- [ ] no silent materialization.

## K. Production

- [ ] reference profiles.
- [ ] profile history.
- [ ] continuous quality monitoring.
- [ ] drift monitoring.
- [ ] alerts/hooks.
- [ ] CI validation.
- [ ] OpenLineage export.
- [ ] plugin system.
- [ ] optional dependency groups.

---

# 125. ما الذي أعتبره الآن أعلى أولوية بعد كل المراجعات؟

إذا أردنا تجنب تضخم المشروع، فهذه الميزات هي الأكثر تميزًا ويجب أن تدخل مبكرًا:

## Tier 1 — Core Differentiators

1. Semantic + probabilistic type inference.
2. Issue taxonomy + Repair Triage.
3. Evidence-based recommendations.
4. Human-in-the-loop Guided Mode.
5. Before/After impact engine.
6. Pre/Post interactive EDA.
7. Reproducible operation graph.
8. Data Contract + schema evolution.
9. Multi-backend IR.
10. Validation plan with failing-row drill-down.
11. Idempotence + determinism assurance.
12. Leakage + temporal causality guards.

## Tier 2 — Major Competitive Advantages

13. Entity Resolution Workbench.
14. Unicode/Text Integrity.
15. Date ambiguity intelligence.
16. Privacy/PII layer.
17. Root-cause/upstream diagnosis.
18. Cleaning Drift + continuous monitoring.
19. Streaming preprocessing.
20. Column-level lineage.
21. Smart large-data visualization planner.
22. Rule-learning knowledge base.

## Tier 3 — Ecosystem Expansion

23. Synthetic Sandbox.
24. Spark/Dask distributed modes.
25. Organization-level rule registry.
26. OpenLineage interoperability.
27. Domain plugins.
28. Dataset Cards.
29. Benchmark suite.
30. CI/CD quality gates.

---

# 126. الخلاصة النهائية بعد البحث الإضافي

بعد هذا التدقيق، الهدف لم يعد بناء:

```text
Best Cleaning Library
```

بل بناء:

# **Data Preparation Intelligence & Reliability Platform**

المنصة تجمع أفضل الأفكار الموجودة في:

```text
Pandas / Polars / PyJanitor / DataPrep
YData Profiling / Sweetviz / Skimpy / Missingno
PyGWalker / D-Tale / Panel-style interactive grids
Pandera / Great Expectations / Soda / Pointblank / Frictionless
Scikit-learn / Feature-engine / skrub / category_encoders
miceforest / advanced imputation
PyOD / Cleanlab / Alibi Detect
RapidFuzz / recordlinkage / dedupe
ftfy / dateparser / semantic-field validators
whylogs / River
Presidio
Narwhals / Ibis / Arrow / DuckDB / Dask / Spark
OpenLineage
SDV (optional diagnostics)
```

لكن التفوق لا يأتي من جمع الوظائف فقط.

التفوق الحقيقي يأتي من الطبقة التي تربط بينها:

```text
Understand
→ Diagnose
→ Explain
→ Quantify uncertainty
→ Recommend alternatives
→ Estimate impact
→ Ask the user when necessary
→ Preview
→ Apply safely
→ Validate
→ Measure preservation
→ Test reproducibility
→ Track lineage
→ Monitor future data
```

وبذلك تصبح المكتبة ليست أداة تنظيف فقط، بل **نظام قرار موثوق لإعداد البيانات** يمكن استخدامه في Notebook، البحث الأكاديمي، ML، Econometrics، Data Engineering، والبيئات الإنتاجية.


---

# 138. سياسة المراجع والمصادر المعتمدة في بناء SmartPrep

هذه النسخة تجعل الخطة **Reference-Driven Blueprint** وليست مجرد قائمة أفكار. عند تنفيذ أي Module أو API أو واجهة أو خوارزمية، يجب ربط قرار التصميم بمصدر أو أكثر من الفئات التالية:

1. **Official Documentation**: المصدر الأول لتعريف السلوك وواجهات API والقيود الحالية.
2. **Official GitHub Repository**: لفحص المعمارية، الاختبارات، Issues، Changelog، Releases، وقرارات التصميم الفعلية.
3. **PyPI / Conda-forge**: للتحقق من الحزمة المنشورة، الإصدارات، المتطلبات، وحالة التوزيع.
4. **Standards / Specifications**: للـschema، contracts، lineage، serialization، metadata، interoperability.
5. **Peer-reviewed papers / canonical methodological references**: عندما تكون الميزة خوارزمية أو إحصائية وليست مجرد API.
6. **Benchmark repositories / issue trackers**: لاكتشاف نقاط الضعف الواقعية التي يعاني منها المستخدمون في الأدوات الموجودة.

> **قاعدة مهمة:** لا يجوز نسخ API أو كود أو UX من مشروع آخر دون مراعاة الرخصة. نستخلص الأفكار والأنماط التصميمية، ثم نبني تنفيذًا أصليًا مع مراجعة licenses لكل dependency أو code reuse محتمل.

## 138.1 ترميز المصادر داخل المشروع

يفضل إنشاء ملف داخلي مستقبلًا:

```text
references/
    sources.yaml
    algorithms.yaml
    licenses.yaml
    competitor_features.yaml
    papers.bib
```

وكل Feature في SmartPrep يمكن ربطها بمعرّفات مصادر مثل:

```yaml
feature: semantic_type_detection
sources:
  - DATAPROFILER_DOCS
  - DATAPREP_CLEAN
  - PANDERA_DOCS
  - SKRUB_DOCS
```

وهذا يسمح لاحقًا بتوليد Documentation وAcknowledgements وDesign Rationale آليًا.

---

# 139. خريطة المصادر المرجعية حسب طبقات المكتبة

## 139.1 Core DataFrame / Execution / Interoperability

### pandas
- Documentation: https://pandas.pydata.org/docs/
- GitHub: https://github.com/pandas-dev/pandas
- PyPI: https://pypi.org/project/pandas/
- نستخدمه مرجعًا لـ DataFrame semantics، missing values، dtypes، string/date operations، indexing، IO، interoperability.

### Polars
- Documentation: https://docs.pola.rs/
- GitHub: https://github.com/pola-rs/polars
- PyPI: https://pypi.org/project/polars/
- نستخدمه مرجعًا لـ expression API، lazy execution، query optimization، schema-aware transformations، high-performance tabular operations.

### Apache Arrow / PyArrow
- Documentation: https://arrow.apache.org/docs/python/
- GitHub: https://github.com/apache/arrow
- PyPI: https://pypi.org/project/pyarrow/
- مرجع للـcolumnar memory model، schema، null semantics، Parquet/IPC، zero-copy interoperability.

### DuckDB
- Documentation: https://duckdb.org/docs/
- GitHub: https://github.com/duckdb/duckdb
- PyPI: https://pypi.org/project/duckdb/
- مرجع لـSQL-on-files، pushdown، analytical execution، Parquet/CSV integration.

### Dask
- Documentation: https://docs.dask.org/
- DataFrame docs: https://docs.dask.org/en/latest/dataframe.html
- GitHub: https://github.com/dask/dask
- PyPI: https://pypi.org/project/dask/
- مرجع للـpartitioned/larger-than-memory/distributed DataFrame workflows.

### Apache Spark / PySpark
- Documentation: https://spark.apache.org/docs/latest/api/python/
- ML features: https://spark.apache.org/docs/latest/ml-features.html
- GitHub: https://github.com/apache/spark
- مرجع للـdistributed preprocessing، feature transformers، large-scale execution.

### Narwhals
- Documentation: https://narwhals-dev.github.io/narwhals/
- GitHub: https://github.com/narwhals-dev/narwhals
- PyPI: https://pypi.org/project/narwhals/
- مرجع مهم لبناء library تتعامل مع أكثر من dataframe backend دون coupling مباشر.

### Ibis
- Documentation: https://ibis-project.org/
- GitHub: https://github.com/ibis-project/ibis
- PyPI: https://pypi.org/project/ibis-framework/
- مرجع للـportable dataframe expressions وcompilation إلى أكثر من backend وقاعدة بيانات.

---

## 139.2 Profiling / Automated EDA / Data Understanding

### YData Profiling
- Documentation: https://docs.profiling.ydata.ai/
- GitHub: https://github.com/ydataai/ydata-profiling
- PyPI: https://pypi.org/project/ydata-profiling/
- ندرس منه alerts، profiling reports، missingness، correlations، type summaries، HTML reporting.

### Sweetviz
- GitHub: https://github.com/fbdesignpro/sweetviz
- PyPI: https://pypi.org/project/sweetviz/
- مرجع لـtarget-aware EDA، dataset comparison، feature association، high-density self-contained HTML report.

### DataProfiler
- Documentation: https://capitalone.github.io/DataProfiler/
- GitHub: https://github.com/capitalone/DataProfiler
- PyPI: https://pypi.org/project/DataProfiler/
- مرجع لـschema/statistical profiling، structured/unstructured profiling، semantic labels، PII/NPI detection، profile update/merge.

### Skimpy
- Documentation: https://aeturrell.github.io/skimpy/
- GitHub: https://github.com/aeturrell/skimpy
- PyPI: https://pypi.org/project/skimpy/
- مرجع لـcompact summaries وfast notebook profiling.

### missingno
- GitHub: https://github.com/ResidentMario/missingno
- PyPI: https://pypi.org/project/missingno/
- مرجع لـmissingness matrix/bar/heatmap/dendrogram وأفكار visual diagnosis للقيم المفقودة.

### AutoViz
- GitHub: https://github.com/AutoViML/AutoViz
- PyPI: https://pypi.org/project/autoviz/
- مرجع لـautomatic chart generation واختيار visualization تلقائيًا.

---

## 139.3 Interactive EDA / Visual Data Wrangling / UI

### PyGWalker / Graphic Walker
- Documentation: https://docs.kanaries.net/pygwalker
- GitHub: https://github.com/Kanaries/pygwalker
- Graphic Walker: https://github.com/Kanaries/graphic-walker
- PyPI: https://pypi.org/project/pygwalker/
- مرجع للـdrag-and-drop exploration، notebook embedding، interactive visual grammar، reusable specs، dataframe/connector exploration.

### D-Tale
- Documentation: https://dtale.readthedocs.io/
- GitHub: https://github.com/man-group/dtale
- PyPI: https://pypi.org/project/dtale/
- مرجع للـinteractive grid، filters، editing، column operations، charts، code export، web-based dataframe inspection.

### PandasGUI
- GitHub: https://github.com/adamerose/PandasGUI
- PyPI: https://pypi.org/project/pandasgui/
- مرجع لتجربة desktop-style dataframe exploration/editing.

### Panel / Tabulator
- Documentation: https://panel.holoviz.org/
- Tabulator: https://panel.holoviz.org/reference/widgets/Tabulator.html
- GitHub: https://github.com/holoviz/panel
- مرجع للـinteractive grids، callbacks، editors، streaming، patching، dashboard integration.

### Plotly Python
- Documentation: https://plotly.com/python/
- Animations: https://plotly.com/python/animations/
- GitHub: https://github.com/plotly/plotly.py
- مرجع للـinteractive charts، hover، zoom، selection، linked interactions، animation.

### Matplotlib
- Documentation: https://matplotlib.org/stable/
- GitHub: https://github.com/matplotlib/matplotlib
- مرجع للرسومات static والعلمية والتقارير PDF/PNG/SVG.

### Seaborn
- Documentation: https://seaborn.pydata.org/
- GitHub: https://github.com/mwaskom/seaborn
- مرجع للـstatistical visualization، distribution plots، categorical plots، pairwise visual exploration.

### Altair / Vega-Lite
- Documentation: https://altair-viz.github.io/
- GitHub: https://github.com/vega/altair
- Vega-Lite: https://vega.github.io/vega-lite/
- مرجع للـdeclarative visualization grammar والـselection/interaction specifications.

### HoloViews / Datashader
- HoloViews docs: https://holoviews.org/
- HoloViews GitHub: https://github.com/holoviz/holoviews
- Datashader docs: https://datashader.org/
- Datashader GitHub: https://github.com/holoviz/datashader
- مرجع للتعامل البصري مع البيانات كبيرة الحجم والـaggregation/rasterization بدل رسم ملايين النقاط مباشرة.

---

## 139.4 General Data Cleaning / Wrangling

### PyJanitor
- Documentation: https://pyjanitor-devs.github.io/pyjanitor/
- GitHub: https://github.com/pyjanitor-devs/pyjanitor
- PyPI: https://pypi.org/project/pyjanitor/
- مرجع لـclean method chaining، clean_names، reshape، conditional joins، date/currency helpers، readable cleaning pipelines.

### DataPrep.Clean
- Documentation: https://docs.dataprep.ai/user_guide/clean/introduction.html
- GitHub: https://github.com/sfu-db/dataprep
- PyPI: https://pypi.org/project/dataprep/
- مرجع للـsemantic/domain-specific cleaning: country، date، email، phone، URL، address، geographic coordinates، text، headers.

### AutoClean / py-AutoClean
- PyPI: https://pypi.org/project/py-AutoClean/
- مرجع لفكرة automated cleaning baseline، مع ضرورة التفوق عليها في explainability، safety، confidence، preview، human review.

---

## 139.5 Text Integrity / Fuzzy Matching / Entity Resolution

### RapidFuzz
- Documentation: https://rapidfuzz.github.io/RapidFuzz/
- GitHub: https://github.com/rapidfuzz/RapidFuzz
- PyPI: https://pypi.org/project/RapidFuzz/
- مرجع للـfast fuzzy matching وstring similarity.

### Python Record Linkage Toolkit
- Documentation: https://recordlinkage.readthedocs.io/
- GitHub: https://github.com/J535D165/recordlinkage
- PyPI: https://pypi.org/project/recordlinkage/
- مرجع للـblocking، comparison، classification، record linkage workflows.

### dedupe
- Documentation: https://docs.dedupe.io/
- GitHub: https://github.com/dedupeio/dedupe
- PyPI: https://pypi.org/project/dedupe/
- مرجع للـML-assisted entity resolution وduplicate detection.

### ftfy
- Documentation: https://ftfy.readthedocs.io/
- GitHub: https://github.com/rspeer/python-ftfy
- PyPI: https://pypi.org/project/ftfy/
- مرجع لإصلاح mojibake وUnicode/text encoding problems.

### Unidecode
- PyPI: https://pypi.org/project/Unidecode/
- GitHub: https://github.com/avian2/unidecode
- مرجع للـtransliteration، مع حذر خاص للغات غير اللاتينية وعدم استخدامها كـauto-fix افتراضيًا.

---

## 139.6 Dates / Semantic Fields / Domain Validation

### dateparser
- Documentation: https://dateparser.readthedocs.io/
- GitHub: https://github.com/scrapinghub/dateparser
- PyPI: https://pypi.org/project/dateparser/
- مرجع للـflexible/multilingual datetime parsing.

### python-dateutil
- Documentation: https://dateutil.readthedocs.io/
- GitHub: https://github.com/dateutil/dateutil
- PyPI: https://pypi.org/project/python-dateutil/
- مرجع لـdate parsing، relativedelta، timezone utilities.

### phonenumbers
- GitHub: https://github.com/daviddrysdale/python-phonenumbers
- PyPI: https://pypi.org/project/phonenumbers/
- مرجع لـphone parsing/validation/formatting/geography.

### email-validator
- GitHub: https://github.com/JoshData/python-email-validator
- PyPI: https://pypi.org/project/email-validator/
- مرجع للتحقق من email syntax/domain normalization بدل regex بسيط.

### usaddress
- GitHub: https://github.com/datamade/usaddress
- PyPI: https://pypi.org/project/usaddress/
- مثال مرجعي للـdomain-specific address parsing.

### libpostal
- GitHub: https://github.com/openvenues/libpostal
- مرجع عالمي نسبيًا لـaddress parsing/normalization، ويمكن الاستفادة من أفكاره دون جعله dependency أساسيًا.

### pycountry
- GitHub: https://github.com/pycountry/pycountry
- PyPI: https://pypi.org/project/pycountry/
- مرجع لأكواد الدول واللغات والعملات ISO.

### Pint
- Documentation: https://pint.readthedocs.io/
- GitHub: https://github.com/hgrecco/pint
- مرجع لـunit-aware quantities والتحويل بين الوحدات.

---

## 139.7 Machine-Learning Preprocessing / Feature Engineering

### scikit-learn
- Preprocessing docs: https://scikit-learn.org/stable/modules/preprocessing.html
- Imputation docs: https://scikit-learn.org/stable/modules/impute.html
- Compose/ColumnTransformer: https://scikit-learn.org/stable/modules/compose.html
- Pipeline: https://scikit-learn.org/stable/modules/compose.html#pipeline
- GitHub: https://github.com/scikit-learn/scikit-learn
- PyPI: https://pypi.org/project/scikit-learn/
- المرجع الأساسي لTransformer API، scaling، normalization، encoding، discretization، imputation، pipeline composition، leakage-safe fit/transform semantics.

### Feature-engine
- Documentation: https://feature-engine.trainindata.com/
- GitHub: https://github.com/feature-engine/feature_engine
- PyPI: https://pypi.org/project/feature-engine/
- مرجع للـimputation، encoding، transformations، outliers، discretization، feature creation/selection، datetime/time-series features.

### skrub
- Documentation: https://skrub-data.org/
- GitHub: https://github.com/skrub-data/skrub
- PyPI: https://pypi.org/project/skrub/
- مرجع للـmessy tabular data، dirty/high-cardinality strings، table vectorization، similarity/minhash-style encodings.

### category_encoders
- Documentation: https://contrib.scikit-learn.org/category_encoders/
- GitHub: https://github.com/scikit-learn-contrib/category_encoders
- PyPI: https://pypi.org/project/category-encoders/
- مرجع لمجموعة encoders المتقدمة مثل target، CatBoost، WOE، hashing، binary، leave-one-out، GLMM وغيرها.

### imbalanced-learn
- Documentation: https://imbalanced-learn.org/stable/
- GitHub: https://github.com/scikit-learn-contrib/imbalanced-learn
- PyPI: https://pypi.org/project/imbalanced-learn/
- مرجع لـSMOTE family، under/over-sampling، combined resampling، pipeline-safe imbalance preprocessing.

### Featuretools
- Documentation: https://docs.featuretools.com/
- GitHub: https://github.com/alteryx/featuretools
- PyPI: https://pypi.org/project/featuretools/
- مرجع للـautomated feature engineering وDeep Feature Synthesis في relational/event data.

---

## 139.8 Missing Data / Imputation

### scikit-learn.impute
- Documentation: https://scikit-learn.org/stable/modules/impute.html
- مرجع لـSimpleImputer، KNNImputer، IterativeImputer، MissingIndicator.

### miceforest
- Documentation/GitHub: https://github.com/AnotherSamWilson/miceforest
- PyPI: https://pypi.org/project/miceforest/
- مرجع لـmultiple imputation by chained equations باستخدام tree-based models.

### fancyimpute
- GitHub: https://github.com/iskandr/fancyimpute
- PyPI: https://pypi.org/project/fancyimpute/
- مرجع تاريخي لطرق KNN/SoftImpute/iterative matrix completion approaches.

### statsmodels MICE
- Documentation: https://www.statsmodels.org/stable/imputation.html
- GitHub: https://github.com/statsmodels/statsmodels
- مرجع إحصائي مهم للـMICE في السياقات البحثية.

---

## 139.9 Outliers / Anomalies / Data Errors

### PyOD
- Documentation: https://pyod.readthedocs.io/
- GitHub: https://github.com/yzhao062/pyod
- PyPI: https://pypi.org/project/pyod/
- مرجع شامل لعدد كبير من خوارزميات outlier/anomaly detection.

### Cleanlab
- Documentation: https://docs.cleanlab.ai/
- GitHub: https://github.com/cleanlab/cleanlab
- PyPI: https://pypi.org/project/cleanlab/
- مرجع لاكتشاف label issues، near duplicates، outliers، data quality issues على مستوى dataset.

### SciPy
- Documentation: https://docs.scipy.org/doc/scipy/
- GitHub: https://github.com/scipy/scipy
- مرجع للتحويلات والأساليب الإحصائية والـwinsorization/z-score/Box-Cox وغيرها.

---

## 139.10 Data Validation / Quality Rules

### Pandera
- Documentation: https://pandera.readthedocs.io/
- GitHub: https://github.com/unionai-oss/pandera
- PyPI: https://pypi.org/project/pandera/
- مرجع لـDataFrame schemas، checks، typing، validation، multi-backend validation including modern dataframe engines.

### Great Expectations
- Documentation: https://docs.greatexpectations.io/
- GitHub: https://github.com/great-expectations/great_expectations
- PyPI: https://pypi.org/project/great-expectations/
- مرجع لفلسفة expectations، validation results، checkpoints، data quality documentation، production workflows.

### Pointblank for Python
- Documentation: https://posit-dev.github.io/pointblank/
- GitHub: https://github.com/posit-dev/pointblank
- PyPI: https://pypi.org/project/pointblank/
- مرجع مهم جدًا للـchainable validation plans، warning/error/critical thresholds، interactive reports، extracting failing rows، Polars/Pandas/Ibis integration، CLI/CI use.

### Soda Core
- Documentation: https://docs.soda.io/
- GitHub: https://github.com/sodadata/soda-core
- PyPI: https://pypi.org/project/soda-core/
- مرجع لـdeclarative data quality checks وSQL/data-source oriented validation.

### Frictionless Framework
- Documentation: https://framework.frictionlessdata.io/
- GitHub: https://github.com/frictionlessdata/frictionless-py
- PyPI: https://pypi.org/project/frictionless/
- مرجع لـresource/schema/package concepts، extract/validate/transform، file/data contracts، tabular schema portability.

### Pydantic
- Documentation: https://docs.pydantic.dev/
- GitHub: https://github.com/pydantic/pydantic
- PyPI: https://pypi.org/project/pydantic/
- مرجع لـrecord/input validation، typed models، API boundary validation.

### Deequ
- GitHub: https://github.com/awslabs/deequ
- مرجع لـlarge-scale data quality verification على Spark وأفكار metrics/constraints/anomaly detection.

### TensorFlow Data Validation (TFDV)
- Documentation: https://www.tensorflow.org/tfx/data_validation/get_started
- GitHub: https://github.com/tensorflow/data-validation
- مرجع للـschema inference، anomalies، statistics، training-serving skew/drift concepts.

---

## 139.11 Continuous Data Quality / Observability / Drift

### whylogs
- Documentation: https://whylogs.readthedocs.io/
- GitHub: https://github.com/whylabs/whylogs
- PyPI: https://pypi.org/project/whylogs/
- مرجع للـlightweight statistical profiles، mergeable profiles، monitoring، constraints.

### Evidently
- Documentation: https://docs.evidentlyai.com/
- GitHub: https://github.com/evidentlyai/evidently
- PyPI: https://pypi.org/project/evidently/
- مرجع لـdata/ML monitoring، drift reports، test suites، dashboards/metrics.

### Deepchecks
- Documentation: https://docs.deepchecks.com/
- GitHub: https://github.com/deepchecks/deepchecks
- PyPI: https://pypi.org/project/deepchecks/
- مرجع لـdata integrity، train-test validation، drift، model/data checks.

### Alibi Detect
- Documentation: https://docs.seldon.ai/alibi-detect/
- GitHub: https://github.com/SeldonIO/alibi-detect
- PyPI: https://pypi.org/project/alibi-detect/
- مرجع لـoffline/online drift، outlier، adversarial detection، statistical detectors.

### River
- Documentation: https://riverml.xyz/
- GitHub: https://github.com/online-ml/river
- PyPI: https://pypi.org/project/river/
- مرجع للـonline/incremental preprocessing، streaming statistics، rolling transforms، drift detection.

---

## 139.12 Privacy / PII / Anonymization

### Microsoft Presidio
- Documentation: https://microsoft.github.io/presidio/
- GitHub: https://github.com/microsoft/presidio
- مرجع لـPII detection، recognizers، context-aware analysis، anonymization، structured/unstructured data.

### OpenDP
- Documentation: https://docs.opendp.org/
- GitHub: https://github.com/opendp/opendp
- مرجع للـprivacy-preserving transformations وDifferential Privacy.

### IBM diffprivlib
- Documentation: https://diffprivlib.readthedocs.io/
- GitHub: https://github.com/IBM/differential-privacy-library
- PyPI: https://pypi.org/project/diffprivlib/
- مرجع عملي لـdifferential privacy mechanisms/models.

### Anonymeter
- GitHub: https://github.com/statice/anonymeter
- PyPI: https://pypi.org/project/anonymeter/
- مرجع لتقييم privacy risk في synthetic/anonymized data.

---

## 139.13 Data Contracts / Schema Evolution / Specifications

### Open Data Contract Standard / Data Contract CLI
- CLI Documentation: https://cli.datacontract.com/
- Documentation: https://docs.datacontract.com/
- GitHub CLI: https://github.com/datacontract/datacontract-cli
- Specification repository: https://github.com/datacontract/datacontract-specification
- مرجع للـcontracts، schema + semantics + quality + SLA، lint/test/import/export، CI/CD enforcement، breaking-change checks.

### JSON Schema
- Specification: https://json-schema.org/specification
- GitHub organization: https://github.com/json-schema-org
- مرجع عام للـmachine-readable structural validation وschema evolution/interchange.

### Frictionless Table Schema
- Specification/docs: https://specs.frictionlessdata.io/table-schema/
- مرجع لوصف tabular fields، types، constraints، missing values، keys.

---

## 139.14 Lineage / Provenance / Metadata

### OpenLineage
- Documentation: https://openlineage.io/docs/
- GitHub: https://github.com/OpenLineage/OpenLineage
- مرجع مفتوح للـDataset/Job/Run lineage events والتكامل مع orchestration/data platforms.

### Marquez
- GitHub: https://github.com/MarquezProject/marquez
- Documentation: https://marquezproject.ai/
- مرجع لتخزين/عرض lineage metadata مبني حول OpenLineage concepts.

### DataHub
- Documentation: https://docs.datahub.com/
- GitHub: https://github.com/datahub-project/datahub
- مرجع للـmetadata catalog، lineage، schema metadata، ownership، data discovery.

### OpenMetadata
- Documentation: https://docs.open-metadata.org/
- GitHub: https://github.com/open-metadata/OpenMetadata
- مرجع إضافي للـmetadata/lineage/data quality integration.

---

## 139.15 Synthetic Data / Testing / Stress Testing

### SDV
- Documentation: https://docs.sdv.dev/sdv
- GitHub: https://github.com/sdv-dev/SDV
- PyPI: https://pypi.org/project/sdv/
- مرجع للـsynthetic tabular/relational data، metadata، quality evaluation، test-data generation.

### Faker
- Documentation: https://faker.readthedocs.io/
- GitHub: https://github.com/joke2k/faker
- PyPI: https://pypi.org/project/Faker/
- مرجع لتوليد بيانات domain-shaped بسيطة لاختبارات الـUI والـvalidation.

### Hypothesis
- Documentation: https://hypothesis.readthedocs.io/
- GitHub: https://github.com/HypothesisWorks/hypothesis
- PyPI: https://pypi.org/project/hypothesis/
- مرجع رئيسي لـproperty-based testing، وهو مهم جدًا لاختبار cleaning invariants وidempotence والedge cases.

---

# 140. مراجع خوارزمية ومنهجية يجب ربطها بالميزات العلمية

هذه الفئة لا تعتمد على مكتبة Python فقط، بل على مرجع المنهج نفسه.

## 140.1 Missing Data

- Rubin, D. B. — *Multiple Imputation for Nonresponse in Surveys*.
- Little, R. J. A. & Rubin, D. B. — *Statistical Analysis with Missing Data*.
- van Buuren, S. — *Flexible Imputation of Missing Data*.
- MissForest paper: Stekhoven & Bühlmann — non-parametric missing value imputation using random forest.
- MICE literature for chained equations.

**استخدامها:** عدم جعل Recommendation Engine يختار imputation فقط بسبب benchmark تقني؛ يجب أن يراعي MCAR/MAR/MNAR والهدف الاستدلالي والتحيز وعدم اليقين.

## 140.2 Outliers / Robust Statistics

- Tukey — Exploratory Data Analysis / boxplot principles.
- Huber & Ronchetti — Robust Statistics.
- Rousseeuw & Leroy — Robust Regression and Outlier Detection.
- Isolation Forest paper.
- Local Outlier Factor paper.

**استخدامها:** فصل detection عن treatment، وعدم جعل outlier = delete.

## 140.3 Categorical Encoding / Leakage

- Target encoding / empirical Bayes literature.
- CatBoost ordered target statistics literature.
- scikit-learn TargetEncoder implementation/documentation.

**استخدامها:** cross-fitting، leakage prevention، rare-category handling، uncertainty-aware encoding.

## 140.4 Drift / Two-sample testing

- Kolmogorov–Smirnov test literature.
- Population Stability Index (industry reference; يجب توضيح عدم وجود تعريف موحد واحد في الأدبيات).
- Maximum Mean Discrepancy (MMD) literature.
- Wasserstein distance / optimal transport references.
- ADWIN concept drift detector literature.

**استخدامها:** Drift Advisor لا يعتمد على metric واحدة ولا threshold عالمي واحد.

## 140.5 Entity Resolution

- Fellegi–Sunter record linkage framework.
- Probabilistic record linkage literature.
- Modern learned entity-resolution methods.

**استخدامها:** separation بين exact duplicates، fuzzy duplicates، entity resolution، conflict resolution.

---

# 141. Reference-to-Feature Matrix — ماذا نتعلم من كل مشروع؟

| الفئة | المصادر الأساسية | ما يجب أن يرثه SmartPrep | كيف يتفوق |
|---|---|---|---|
| Profiling | YData, DataProfiler, Skimpy | statistics, alerts, semantic profiling | diagnosis + repair recommendation + uncertainty + impact |
| Comparative EDA | Sweetviz | dataset/target comparison | pre/post-cleaning + treatment alternatives + statistical preservation |
| Interactive Exploration | PyGWalker | drag/drop, interactive plots | cleaning-first UX + every click reproducible + repair actions |
| Interactive Grid | D-Tale, Panel/Tabulator | edit/filter/select/inspect | issue badges + cell lineage + preview + undo + rule generation |
| Cleaning API | PyJanitor | readable chaining | semantic operations + safety classes + audit + backend portability |
| Semantic Cleaning | DataPrep, DataProfiler | field-aware parsing/validation | confidence + ambiguity + locale + domain rules + user confirmation |
| ML Preprocessing | sklearn | fit/transform, pipelines, ColumnTransformer | automatic recommendation + leakage detection + impact comparison |
| Dirty Categories | skrub, RapidFuzz | high-cardinality/string similarity | cluster/reconcile/approve + reusable organizational dictionary |
| Advanced Encoding | category_encoders | many encoder families | Encoding Advisor + leakage/risk/cardinality/model-aware selection |
| Missing Data | sklearn, miceforest, statsmodels | multiple strategies | missingness mechanism evidence + uncertainty + downstream sensitivity |
| Outliers | PyOD, SciPy | detection methods | ensemble evidence + contextual/domain distinction + no auto-delete |
| Validation | Pandera, GX, Pointblank, Soda | schemas/rules/reports | rules discovered from data + interactive repair loop + severity triage |
| Contracts | Frictionless, ODCS/Data Contract CLI | machine-readable expectations | schema evolution + semantic breaking-change detection + auto-generated rules |
| Observability | whylogs, Evidently, Deepchecks | drift/monitoring | cleaning drift + root-cause attribution + remediation suggestions |
| Streaming | River, Alibi Detect | online stats/drift | stateful cleaning + temporal leakage guard + streaming quality contracts |
| Privacy | Presidio, OpenDP | PII/privacy transforms | privacy-aware cleaning plan + impact/audit + reversible tokenization policies |
| Backend abstraction | Narwhals, Ibis | portable execution | semantic IR + capability negotiation + no silent fallback |
| Lineage | OpenLineage, DataHub | provenance | cell/column transformation lineage + decision provenance + user actions |
| Synthetic/Test | SDV, Hypothesis | synthetic data/property tests | benchmark corpus with known corruption ground truth |

---

# 142. مستودعات GitHub التي يجب مراقبتها أثناء التطوير

لا يكفي قراءة الوثائق مرة واحدة. يفضل إنشاء **Competitor Watchlist** ومراجعة Releases/Issues كل فترة، لأن بعض الأفكار تظهر أولًا في Issues وPRs قبل التوثيق الرسمي.

## Priority A — متابعة مستمرة

1. https://github.com/ydataai/ydata-profiling
2. https://github.com/Kanaries/pygwalker
3. https://github.com/man-group/dtale
4. https://github.com/capitalone/DataProfiler
5. https://github.com/pyjanitor-devs/pyjanitor
6. https://github.com/sfu-db/dataprep
7. https://github.com/unionai-oss/pandera
8. https://github.com/great-expectations/great_expectations
9. https://github.com/posit-dev/pointblank
10. https://github.com/scikit-learn/scikit-learn
11. https://github.com/feature-engine/feature_engine
12. https://github.com/skrub-data/skrub
13. https://github.com/cleanlab/cleanlab
14. https://github.com/yzhao062/pyod
15. https://github.com/narwhals-dev/narwhals
16. https://github.com/ibis-project/ibis
17. https://github.com/pola-rs/polars
18. https://github.com/duckdb/duckdb
19. https://github.com/whylabs/whylogs
20. https://github.com/evidentlyai/evidently
21. https://github.com/online-ml/river
22. https://github.com/SeldonIO/alibi-detect
23. https://github.com/microsoft/presidio
24. https://github.com/OpenLineage/OpenLineage
25. https://github.com/datacontract/datacontract-cli

## Priority B — متابعة حسب الـmodule

- Entity resolution: https://github.com/dedupeio/dedupe
- Record linkage: https://github.com/J535D165/recordlinkage
- Fuzzy text: https://github.com/rapidfuzz/RapidFuzz
- Unicode: https://github.com/rspeer/python-ftfy
- Date parsing: https://github.com/scrapinghub/dateparser
- Imputation: https://github.com/AnotherSamWilson/miceforest
- Imbalance: https://github.com/scikit-learn-contrib/imbalanced-learn
- Encoders: https://github.com/scikit-learn-contrib/category_encoders
- Feature engineering: https://github.com/alteryx/featuretools
- Distributed: https://github.com/dask/dask
- Arrow: https://github.com/apache/arrow
- Spark: https://github.com/apache/spark
- Visualization: https://github.com/plotly/plotly.py
- Panel: https://github.com/holoviz/panel
- Datashader: https://github.com/holoviz/datashader
- Synthetic: https://github.com/sdv-dev/SDV
- Property tests: https://github.com/HypothesisWorks/hypothesis

---

# 143. ماذا نفحص داخل GitHub وليس README فقط؟

عند دراسة المنافس، يجب فحص:

1. `README.md` — الصورة العامة والـquick start.
2. `/docs` — التفاصيل والـAPI design.
3. `pyproject.toml` / `setup.py` — dependencies وPython support وextras.
4. `CHANGELOG` / Releases — الاتجاه الحديث للمشروع.
5. Open Issues — المشاكل التي لم يحلها المنافس بعد.
6. Closed Issues — الحالات الواقعية وكيف عولجت.
7. Pull Requests — features القادمة وقرارات maintainers.
8. Tests — السلوك الحقيقي والedge cases.
9. Benchmarks — الأداء والذاكرة.
10. Architecture / ADRs إن وجدت.
11. License — ما يمكن استخدامه أو الاقتباس منه قانونيًا.
12. Security policy — handling للبيانات الحساسة.
13. CI matrices — الإصدارات المدعومة من Python/backends.
14. Discussions — طلبات المستخدمين التي يمكن تحويلها إلى competitive features.

**قيمة مضافة مقترحة:** الاحتفاظ بملف داخلي `competitive_gap_registry.yaml` يسجل لكل competitor:

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
last_reviewed: 2026-08-26
```

---

# 144. سجل الرخص Licensing Registry

قبل تنفيذ أي integration أو نسخ فكرة API أو تضمين code، يجب إنشاء جدول licenses فعلي. أمثلة يجب التحقق منها من المستودعات الرسمية وقت التنفيذ:

```text
Project                 License family
------------------------------------------------
scikit-learn            BSD-style
pandas                  BSD-style
Polars                  MIT
PyArrow                 Apache-2.0
DuckDB                   MIT
PyGWalker               Apache-2.0
DataProfiler            Apache-2.0
Pointblank              MIT
Ibis                     Apache-2.0
```

ولا نعتمد هذا الجدول كبديل عن فحص `LICENSE` في commit/tag المحدد الذي سنبني عليه.

يجب أن يحتوي المشروع مستقبلًا على:

```text
THIRD_PARTY_NOTICES.md
DEPENDENCY_LICENSES.json
REFERENCES.md
CITATION.cff
```

---

# 145. نظام الاستشهاد داخل Documentation الخاصة بالمكتبة

لكل Module متقدم، يفضل إضافة قسم:

```text
Design References
Algorithm References
Related Libraries
Why SmartPrep differs
```

مثال:

```text
MissingDataAdvisor

Related software:
- scikit-learn.impute
- miceforest
- statsmodels.imputation.mice

Methodological references:
- Rubin
- Little & Rubin
- van Buuren

SmartPrep extension:
- mechanism evidence
- uncertainty score
- treatment comparison
- downstream sensitivity
- user-review gate
```

وبذلك يستطيع الباحث أو المطور معرفة **لماذا صُممت الميزة بهذه الطريقة**، وليس فقط كيفية استخدامها.

---

# 146. Reference Coverage Gate قبل إصدار أي نسخة

لا تعتبر Feature مكتملة إلا إذا كان لها:

- [ ] Functional specification.
- [ ] At least one official implementation/reference reviewed.
- [ ] Relevant methodological reference when applicable.
- [ ] License review.
- [ ] Edge-case tests.
- [ ] Benchmark case.
- [ ] Explanation of how SmartPrep differs from existing tools.
- [ ] Documentation links.
- [ ] Reproducible example.
- [ ] Failure/abstention behavior.

ويضاف إلى CI فحص metadata بحيث لا يمكن Merge لFeature كبيرة دون `references` field في spec الخاص بها.

---

# 147. ملاحظة حول عبارة «كل المكتبات وكل GitHub»

لا توجد طريقة علمية لضمان حصر **كل** repository أو package على PyPI/GitHub؛ النظام البيئي مفتوح ويتغير يوميًا، وتوجد مشاريع تجريبية ومهجورة وforks لا حصر لها. لذلك الهدف العملي الصحيح هو:

> **Comprehensive functional coverage + representative best-in-class projects + continuously updated source registry.**

أي أننا نضمن أن **كل فئة وظيفية مهمة** في Cleaning / Preprocessing / Profiling / Validation / Quality / Observability / Interactive Wrangling / Privacy / Lineage / Contracts / Streaming / Big Data لها مراجع قوية، ثم نضيف أي مشروع جديد إذا قدم capability غير ممثلة.

ولهذا يجب أن تحتوي SmartPrep نفسها مستقبلًا على مهمة دورية داخل عملية التطوير:

```text
Competitor Discovery
→ Capability Extraction
→ Gap Classification
→ Architecture Review
→ Roadmap Candidate
```

ولا نضيف dependency أو feature لمجرد أنها موجودة؛ بل فقط إذا كانت تضيف **capability جديدة أو implementation lesson أو benchmark value**.

---

# 148. الخلاصة المرجعية النهائية

بعد إضافة هذه الطبقة، الخطة لا تقول فقط:

```text
ابنِ profiling أفضل من YData
```

بل تعطي المطور المسار المرجعي:

```text
YData docs + repository
→ identify profiling capabilities
→ DataProfiler semantic profiling
→ Sweetviz comparative EDA
→ SmartPrep diagnosis model
→ Treatment Recommendation Engine
→ Before/After Impact Engine
```

ولا تقول فقط:

```text
ادعم عدة backends
```

بل:

```text
Narwhals architecture
+ Ibis execution portability
+ Arrow interchange semantics
+ Polars lazy execution
+ DuckDB pushdown
→ SmartPrep Semantic Operation IR
→ Backend Capability Negotiation
→ No Silent Fallback
```

ولا تقول فقط:

```text
أضف validation
```

بل:

```text
Pandera schemas
+ Great Expectations expectations/workflows
+ Pointblank reports/thresholds/extracts
+ Soda declarative checks
+ Frictionless schema/resources
+ ODCS/Data Contract CLI
→ SmartPrep Validation + Contract + Repair Loop
```

وهذا هو المستوى المطلوب حتى تكون المكتبة **مبنية على معرفة النظام البيئي السابق، مع Architecture أصلية وقيمة مضافة قابلة للدفاع عنها تقنيًا وعلميًا**.

---

# 145. Two Primary Entry Points — الواجهتان الأساسيتان اللتان يجب أن يعرفهما كل مستخدم

هذه الإضافة يجب اعتبارها جزءًا مركزيًا من تجربة SmartPrep، لا مجرد aliases فوق وظائف داخلية. المستخدم المبتدئ أو الباحث الذي لا يريد التعامل مع عشرات الوحدات يجب أن يستطيع اختيار واحدة من طريقتين واضحتين فقط:

1. **Automatic Full Scan + Safe Clean**: المكتبة تفحص كل شيء، تعرض كل المشكلات، ثم تنتج نسخة نظيفة آليًا ضمن حدود السلامة.
2. **Guided Full Scan + User Decisions**: المكتبة تفحص كل شيء، ثم تسأل المستخدم عن القرارات السياقية أو الغامضة وتبني النسخة النظيفة وفق إجاباته.

يجب أن تستخدم الطريقتان محرك الفحص نفسه حتى لا تختلف جودة التشخيص بين Auto وGuided.

## 145.1 الوظيفة الأولى: `auto_prepare()` — افحص كل شيء وأنتج نسخة نظيفة

واجهة المستخدم المقترحة:

```python
import smartprep as sp

result = sp.auto_prepare(df)
```

أو باستخدام Project API:

```python
project = sp.Project(df)
result = project.auto_prepare()
```

هذه الوظيفة تنفذ دورة كاملة:

```text
Load / Register Data
        ↓
Full Dataset Scan
        ↓
Issue Inventory
        ↓
Severity + Confidence + Repairability
        ↓
Safe Automatic Repair Plan
        ↓
Preview / Internal Validation
        ↓
Apply Safe Repairs
        ↓
Post-Clean Validation
        ↓
Pre/Post EDA
        ↓
Clean Dataset + Reports + Audit + Unresolved Queue
```

يجب ألا يكون معنى `auto_prepare()` هو "غير البيانات بأي ثمن حتى تختفي كل التحذيرات". المعنى الصحيح هو:

> **افحص جميع الاختبارات المدعومة، أصلح تلقائيًا ما يمكن إصلاحه بثقة وسلامة، واترك الحالات غير المحسومة ظاهرة بدل اختراع تصحيح لها.**

### المخرجات

```python
result.clean_df
result.issues
result.fixed_issues
result.unresolved_issues
result.scan_report
result.before_report
result.after_report
result.comparison_report
result.audit_log
result.pipeline
result.data_health_before
result.data_health_after
```

ويمكن توفير shortcuts:

```python
clean_df = result.clean_df
result.show()
result.save("clean_data.xlsx")
result.export_report("report.html")
```

## 145.2 فحص شامل قبل التنظيف

`auto_prepare()` يجب أن يستدعي داخليًا محركًا موحدًا مثل:

```python
scan = project.full_scan()
```

أو:

```python
scan = project.scan(scope="all")
```

ويجب أن يغطي، بحسب نوع البيانات والسياق، على الأقل:

- schema and structural integrity.
- technical dtypes.
- semantic types.
- mixed physical types داخل العمود.
- parseability.
- missing values.
- hidden/sentinel missing values.
- conditional/structural missingness.
- exact duplicates.
- conflicting duplicate identifiers.
- near duplicates.
- entity-resolution candidates.
- invalid categorical values.
- whitespace/case inconsistencies.
- Unicode confusables / broken encoding.
- messy text.
- invalid dates.
- ambiguous dates.
- impossible dates.
- timezone/frequency/time-order problems.
- numeric range violations.
- percentages خارج النطاق.
- invalid signs.
- units/currency inconsistency.
- country/city/currency/domain consistency.
- candidate formula/invariant violations.
- cross-column logical contradictions.
- outliers and anomalies.
- rare categories.
- high cardinality.
- constant / near-constant columns.
- ID-like columns.
- leakage risks.
- target leakage when target is supplied.
- feature redundancy / correlation warnings.
- class imbalance when relevant.
- PII/privacy issues.
- schema drift when a reference is supplied.
- data drift when a reference is supplied.
- time-series gaps.
- panel duplicates/gaps/unbalancedness when relevant.
- readiness for analysis / econometrics / ML when a goal is supplied.

أي Detector جديد يضاف للمكتبة مستقبلًا يجب أن يستطيع تسجيل نفسه تلقائيًا داخل `full_scan()` عبر Plugin Registry.

## 145.3 مؤشر الفحص من 0% إلى 100%

أثناء `full_scan()` يجب أن يظهر للمستخدم مؤشر تقدم واضح:

```text
SmartPrep Full Scan

[███████████████████████-----------] 67%

✓ Schema                    complete
✓ Data types                complete
✓ Missingness               complete
✓ Duplicates                complete
✓ Text integrity            complete
✓ Datetime                  complete
→ Cross-column rules        running
○ Outliers                  pending
○ Privacy                   pending
○ Drift                     pending
○ Readiness                 pending
```

ثم:

```text
[██████████████████████████████████] 100%

Full scan completed.
47 issues detected.
18 safe auto-fixes available.
11 user-review decisions recommended.
18 informational / unresolved findings.
```

### معنى 100% مهم جدًا

`100%` لا يعني:

> "لقد أثبتنا أن البيانات خالية من أي خطأ ممكن في العالم".

هذا ادعاء غير علمي.

بل يعني:

> **اكتملت 100% من الاختبارات المفعلة والقابلة للتطبيق ضمن Scan Plan لهذه البيانات.**

لذلك يجب أن تعرض الواجهة أيضًا:

```text
Scan coverage: 100% of applicable enabled checks
Applicable checks: 183 / 201
Skipped checks: 18
Reasons: no target / no reference dataset / not time-series / missing domain contract
```

ويمكن إضافة:

```python
scan.coverage
scan.completed_checks
scan.skipped_checks
scan.not_applicable_checks
scan.failed_checks
```

وهذا يفصل بين **Execution Progress** و**Quality Score**.

## 145.4 مؤشرين مختلفين، لا مؤشرًا واحدًا مضللًا

يجب أن تعرض المكتبة على الأقل:

### A. Scan Progress

```text
0% → 100%
```

يقيس نسبة الاختبارات المنفذة.

### B. Data Health Score

```text
Data Health
Before: 61 / 100
After: 93 / 100
```

يقيس جودة البيانات وفق الأبعاد المعرفة في المشروع.

وقد يظهر أيضًا:

```text
Completeness       88
Validity           95
Consistency        90
Uniqueness         99
Integrity          92
Semantic Quality   86
ML Readiness       91
```

بذلك لا يخلط المستخدم بين "الفحص اكتمل 100%" و"البيانات صحيحة 100%".

## 145.5 Auto Repair Policy

بعد اكتمال الفحص، يصنف `RepairTriageEngine` كل مشكلة:

```text
SAFE_AUTO_FIX
AUTO_FIX_WITH_LOG
USER_CONFIRMATION_REQUIRED
DOMAIN_RULE_REQUIRED
AMBIGUOUS
UNRESOLVED
DO_NOT_TOUCH
```

الإعداد الافتراضي لـ`auto_prepare()`:

```python
result = project.auto_prepare(
    confidence_threshold=0.98,
    repair_policy="safe"
)
```

وتنفذ فقط:

```text
SAFE_AUTO_FIX
+
AUTO_FIX_WITH_LOG عندما تحقق policy شروط السلامة
```

أما البقية فتبقى في:

```python
result.unresolved_issues
```

ولا تختفي من التقرير.

### مثال

```text
Trailing whitespace
→ auto fix

"ALGERIA" / "algeria"
→ auto normalize if semantic confidence is high

"Tourismm" → "Tourism"
→ review unless rule already approved

31/02/2025
→ detect as invalid, but do not invent correct date

Two conflicting rows with same invoice_id
→ do not delete automatically
```

## 145.6 خيار الحصول على النسخة النظيفة مباشرة

لتجربة المستخدم البسيطة جدًا:

```python
clean_df = sp.clean(df)
```

لكن `sp.clean()` يجب أن تكون shortcut لـSafe Auto Mode، لا cleaning عدواني.

ويمكن:

```python
clean_df, report = sp.clean(df, return_report=True)
```

أو:

```python
result = sp.clean(df, detailed=True)
```

مع إبقاء API المتقدمة في `Project`.

---

# 146. الوظيفة الثانية: `guided_prepare()` — المكتبة تفحص، ثم تسأل المستخدم

هذه الوظيفة مخصصة للحالات التي يريد المستخدم فيها التحكم في قرارات التنظيف والمعالجة:

```python
result = sp.guided_prepare(df)
```

أو:

```python
project = sp.Project(df)
result = project.guided_prepare()
```

الدورة:

```text
Full Scan 0 → 100%
        ↓
Problem Ranking
        ↓
Safe automatic suggestions
        ↓
Interactive Question Queue
        ↓
User decisions
        ↓
Preview before each consequential repair
        ↓
Apply
        ↓
Validate
        ↓
Post-clean EDA
        ↓
Clean Dataset + Decision Log + Reproducible Pipeline
```

## 146.1 Guided Question Queue

الواجهة لا تسأل سؤالًا عن كل قيمة، بل تجمع القرارات الذكية حسب المشكلة.

مثال:

```text
Issue 4 of 17
Column: annual_revenue
Problem: 8.4% missing values

Recommended treatments
1. Group median           score 92
2. Iterative imputation   score 88
3. KNN                    score 82
4. Keep missing + flag    score 80
5. Drop rows              score 41

Recommended: Group median
Confidence: 0.91

Why?
- variable is strongly right-skewed
- missingness varies by sector
- group-median preserves distribution better than global median

What do you want to do?

[Use recommendation]
[Choose another method]
[Compare methods]
[Preview]
[Define custom rule]
[Leave unresolved]
```

## 146.2 أسئلة حسب نوع المشكلة

### Mixed data type

```text
Column "unit_price" contains:
82.1% numeric
14.7% numeric strings
2.4% currency strings
0.8% invalid text

Suggested canonical type: Monetary / Float

Choose:
- Convert safe values only
- Review invalid values
- Define parsing rule
- Keep original column + create cleaned column
- Ignore
```

### Missing values

```text
Choose treatment:
- Mean
- Median
- Group median
- Mode
- KNN
- Iterative
- Multiple imputation
- Interpolation
- Model-based
- Keep NA + indicator
- Drop
- Custom
```

لكن الخيارات المعروضة يجب أن تكون **context filtered**؛ لا تعرض interpolation لمتغير cross-sectional غير مرتب زمنيًا مثلًا.

### Duplicates

```text
Exact duplicate rows detected: 38
Conflicting duplicate IDs: 7

Exact duplicates:
- Remove duplicates
- Keep first
- Keep last
- Review

Conflicting IDs:
- Review pairs
- Merge using rules
- Choose source priority
- Keep unresolved
```

### Outliers

```text
- Keep
- Flag only
- Winsorize
- Cap/floor
- Transform
- Robust scaling
- Remove
- Domain-rule treatment
- Compare methods
```

ولا ينبغي أن يكون `Remove` هو الاختيار الافتراضي.

## 146.3 Question Prioritization

يجب ترتيب الأسئلة حسب dependency، لا حسب ترتيب الأعمدة.

مثال:

```text
Fix parsing
   ↓
Correct semantic type
   ↓
Recalculate missingness
   ↓
Detect outliers
   ↓
Choose imputation
```

فلا تسأل المستخدم عن outliers في `unit_price` قبل تحويل القيم النصية إلى أرقام.

هذا يستخدم `Issue Dependency Graph` الموجود في الخطة.

## 146.4 Three interaction styles

`guided_prepare()` يجب أن يدعم:

```python
project.guided_prepare(interface="notebook")
project.guided_prepare(interface="web")
project.guided_prepare(interface="terminal")
```

ومستقبلًا:

```python
project.guided_prepare(interface="desktop")
```

بحيث تعمل المكتبة حتى بدون واجهة رسومية كاملة.

## 146.5 Quick Guided Mode

لباحث لا يريد أسئلة كثيرة:

```python
result = project.guided_prepare(question_level="important_only")
```

المستويات:

```text
minimal
important_only
standard
strict
expert
```

### minimal

يسأل فقط عن High-risk decisions.

### expert

يسمح بالتحكم في كل Rule/Threshold/Algorithm تقريبًا.

---

# 147. الوضع الثالث الاختياري: `scan_only()`

رغم أن المطلوب الأساسي وضعان، يجب توفير وضع ثالث بسيط لا يعدل البيانات إطلاقًا:

```python
scan = sp.scan_only(df)
```

أو:

```python
scan = project.full_scan()
```

يعطي:

- issue inventory.
- full diagnostics.
- raw EDA.
- health score.
- recommendations.
- no mutation.

وهذا مهم للباحثين الذين يريدون تشخيص البيانات فقط قبل اتخاذ قرار.

---

# 148. Unified Result Object

يجب أن تعيد الطريقتان Auto وGuided نفس نوع الكائن:

```python
PreparationResult
```

ويحتوي:

```python
result.raw_df
result.clean_df

result.scan
result.issues
result.fixed_issues
result.remaining_issues
result.user_decisions

result.health_before
result.health_after
result.impact

result.before_eda
result.after_eda
result.compare_eda

result.pipeline
result.audit_log
result.lineage
result.contract
```

وبذلك يمكن للمستخدم الانتقال بسهولة من الوضع البسيط إلى المتقدم.

---

# 149. Suggested User-Facing API — واجهة نهائية شديدة الوضوح

يجب أن نستهدف تجربة مثل هذه:

```python
import smartprep as sp

df = sp.read("data.xlsx")

# 1. افحص فقط
scan = sp.scan(df)

# 2. افحص ونظف آليًا بشكل آمن
result_auto = sp.auto_prepare(df)
clean_auto = result_auto.clean_df

# 3. افحص ثم اسألني عن القرارات
result_guided = sp.guided_prepare(df)
clean_guided = result_guided.clean_df
```

وفي API الاختصارية:

```python
clean_df = sp.clean(df)
```

وفي الواجهة التفاعلية:

```python
sp.studio(df)
```

يظهر في البداية:

```text
How would you like to prepare this dataset?

[ Full Scan Only ]
[ Automatic Safe Cleaning ]
[ Guided Cleaning ]
[ Advanced Studio ]
```

هذه الشاشة يجب أن تكون نقطة البداية الافتراضية للمستخدم غير البرمجي.

---

# 150. Auto vs Guided — الفرق الرسمي في مواصفات المنتج

| Capability | `auto_prepare()` | `guided_prepare()` |
|---|---|---|
| Full scan | نعم | نعم |
| Progress 0–100% | نعم | نعم |
| Issue inventory | نعم | نعم |
| Severity/confidence | نعم | نعم |
| Recommendations | نعم | نعم |
| Safe auto-fixes | نعم | نعم |
| User questions | لا افتراضيًا | نعم |
| Ambiguous repairs | تبقى unresolved | يسأل المستخدم |
| Preview | داخلي/اختياري | أساسي |
| Compare treatments | اختياري | أساسي |
| Clean copy | نعم | نعم |
| Raw copy preserved | نعم | نعم |
| Before EDA | نعم | نعم |
| After EDA | نعم | نعم |
| Before/After report | نعم | نعم |
| Audit trail | نعم | نعم |
| Reproducible pipeline | نعم | نعم |
| Undo/versioning | نعم | نعم |

---

# 151. قاعدة غير قابلة للتفاوض: لا تدّعِ "نسخة بلا مشاكل" بطريقة مطلقة

تجربة المستخدم يمكن أن تقول:

```text
Clean version generated.
```

لكن التقرير التقني يجب أن يكون أدق:

```text
Applicable checks completed: 100%
Safe repairs applied: 32
Remaining unresolved issues: 4
Data Health: 58 → 96
```

إذا بقيت مشكلة لا يمكن حسمها دون معرفة domain، فلا يجوز للمكتبة أن تخفيها فقط لكي تعرض `100/100`.

يمكن عرض:

```text
Automation completeness: 100%
Resolved issues: 94%
Remaining review items: 6%
```

وهذا يجعل SmartPrep أكثر ثقة من أدوات التنظيف الآلي التي قد تغير البيانات بصمت.

---

# 152. Acceptance Tests لهاتين الوظيفتين

قبل إصدار `auto_prepare()` يجب أن تنجح الاختبارات التالية:

- [ ] جميع الـdetectors القابلة للتطبيق تدخل Scan Plan.
- [ ] Progress يصل إلى 100% فقط عند اكتمال Scan Plan.
- [ ] skipped checks تظهر مع سبب.
- [ ] raw dataframe لا تتغير in-place افتراضيًا.
- [ ] safe repairs فقط تنفذ في default auto mode.
- [ ] ambiguous repairs لا تنفذ بصمت.
- [ ] clean copy تحفظ منفصلة عن raw copy.
- [ ] كل تعديل يظهر في audit log.
- [ ] كل تعديل قابل لإعادة الإنتاج من pipeline.
- [ ] before/after validation يعمل تلقائيًا.
- [ ] unresolved issues لا تختفي من التقرير.
- [ ] idempotence test يمر على pipeline القياسية.
- [ ] rollback يعيد النسخة السابقة.

وقبل إصدار `guided_prepare()`:

- [ ] نفس Scan Plan المستخدم في Auto Mode.
- [ ] الأسئلة مرتبة حسب dependency.
- [ ] لا تعرض خيارات غير ملائمة للسياق.
- [ ] recommendation مرفقة بالسبب والثقة والمخاطر.
- [ ] Preview متاح للقرارات المؤثرة.
- [ ] المستخدم يستطيع اختيار custom rule.
- [ ] المستخدم يستطيع ترك المشكلة unresolved.
- [ ] كل إجابة تتحول إلى reproducible operation.
- [ ] decisions محفوظة في audit/history.
- [ ] إعادة تشغيل pipeline لا تتطلب إعادة الإجابة عن الأسئلة الموافق عليها سابقًا ما لم تتغير البيانات/القواعد.

---

# 153. القيمة المضافة التنافسية لهذه الواجهة

الهدف ليس فقط أن نملك دالة `clean(df)`؛ توجد أدوات كثيرة توفر one-command cleaning.

القيمة المضافة هي أن الوظيفة الواحدة تجمع:

```text
FULL DIAGNOSIS
+
100% CHECK EXECUTION VISIBILITY
+
SEMANTIC / STRUCTURAL / STATISTICAL / DOMAIN CHECKS
+
SAFE REPAIR TRIAGE
+
PRE/POST EDA
+
IMPACT MEASUREMENT
+
UNRESOLVED ISSUE DISCLOSURE
+
AUDIT + LINEAGE
+
REPRODUCIBLE PIPELINE
```

والوظيفة الموجهة تضيف فوق ذلك:

```text
HUMAN DECISION QUEUE
+
CONTEXT-AWARE OPTIONS
+
METHOD COMPARISON
+
PREVIEW
+
LEARNED PROJECT RULES
```

بهذا تصبح الواجهتان البسيطتان نقطة دخول إلى كامل المنصة بدل أن تكونا wrappers سطحية.


# 100. Automatic Mode Escalation, Warnings, and Guided Handoff

## 100.1 Core principle

Automatic preparation must never create the impression that every detected problem has been safely resolved. The automatic workflow should complete all high-confidence, low-risk operations, but it must explicitly surface unusual, ambiguous, domain-dependent, conflicting, or unsupported issues.

The system therefore follows this rule:

> Auto mode may finish successfully even when unresolved issues remain, but it must never hide them.

The final automatic result must distinguish between:

- `RESOLVED_AUTOMATICALLY`
- `RESOLVED_WITH_LOG`
- `WARNING`
- `REVIEW_RECOMMENDED`
- `GUIDED_MODE_REQUIRED`
- `DOMAIN_EXPERT_REQUIRED`
- `UNRESOLVED`
- `UNSUPPORTED`

## 100.2 New primary behavior

```python
result = sp.auto_prepare(df)
```

The function performs the complete applicable scan, applies safe repairs, validates the result, and then evaluates whether any issues remain that should be escalated.

The result object must expose:

```python
result.clean_df
result.health_score
result.scan_coverage
result.warnings
result.notes
result.review_items
result.guided_items
result.unresolved_issues
result.unsupported_issues
result.auto_fixed_issues
result.audit_log
result.before_report
result.after_report
result.comparison_report
result.pipeline
```

## 100.3 Automatic completion states

Auto mode should not end with a single binary `success=True/False` result. It should expose a richer completion state:

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

Examples:

```text
Status: CLEAN_WITH_WARNINGS
Scan coverage: 100%
Automatically resolved: 37 issues
Warnings: 4
Guided review recommended: 2
Unresolved: 1
```

or:

```text
Status: GUIDED_REVIEW_REQUIRED

Automatic safe cleaning completed.
However, 8 issues cannot be resolved safely without user input.

Recommended next step:
Open Guided Mode for unresolved issues only.
```

## 100.4 Warning severity system

Warnings should have structured severity levels rather than plain text messages:

```text
INFO
NOTICE
WARNING
HIGH_WARNING
CRITICAL_REVIEW
BLOCKING
```

Each warning should include:

```text
Issue ID
Issue type
Affected columns
Affected rows
Severity
Confidence
Why it was flagged
Why auto mode did not repair it
Possible treatments
Recommended action
Whether Guided Mode can resolve it
Whether a domain expert may be required
```

Example:

```text
WARNING DQ-184

Issue:
Conflicting duplicate identifiers

Column:
invoice_id

Affected records:
18

Severity:
HIGH_WARNING

Confidence:
99.8%

Reason:
The same identifier appears in multiple rows with different values.

Automatic action:
None

Why:
Deleting or merging records could destroy valid information.

Recommended action:
Open Guided Mode and choose a duplicate-resolution policy.
```

## 100.5 Unusual problem detector

The automatic engine should maintain a separate class for problems that do not match known standard rules with sufficient confidence.

Suggested concept:

```text
UnusualIssueDetector
```

It should flag cases such as:

- patterns not seen in the built-in issue taxonomy;
- values that violate several weak rules simultaneously;
- unexpected combinations of semantic types;
- sudden schema or distribution changes;
- unknown categorical conventions;
- mixed units with uncertain conversion;
- formula inconsistencies where the intended business formula is unknown;
- contradictory duplicate identifiers;
- possible encoding corruption not safely reversible;
- unexplained sentinel-like values;
- suspicious new categories;
- suspicious relationship breaks between columns;
- ambiguous dates;
- unexpected locale changes;
- values that may be valid domain exceptions;
- custom objects or unsupported nested structures;
- operations for which the active backend has no safe implementation.

The system should be allowed to say:

```text
Unknown / unusual data-quality pattern detected.
Automatic repair was intentionally skipped.
```

This is preferable to guessing.

## 100.6 Guided Mode handoff

The automatic result should directly support:

```python
guided = result.open_guided()
```

or:

```python
guided = sp.guided_prepare(
    result,
    only="unresolved"
)
```

This should preserve:

- the original dataset;
- the auto-cleaned intermediate version;
- all scan results;
- all already accepted automatic repairs;
- issue IDs;
- evidence;
- recommendations;
- audit history;
- user preferences already known for the project.

The user must not have to restart the complete analysis from zero.

## 100.7 Guided review queue generated by Auto Mode

At the end of auto mode, the system builds a prioritized queue:

```text
Guided Review Queue

1. Conflicting invoice IDs              CRITICAL
2. Ambiguous date formats               HIGH
3. Possible accounting-rule violation   HIGH
4. Uncertain category merge             MEDIUM
5. New currency-country pattern         NOTICE
```

Prioritization should consider:

```text
severity
confidence
number of affected records
possible information loss
business impact
statistical impact
downstream model impact
privacy/security implications
whether later operations depend on the decision
```

## 100.8 Smart escalation rules

Suggested defaults:

```text
confidence >= 0.98 and low risk
    -> SAFE_AUTO_FIX

confidence >= 0.90 and reversible
    -> AUTO_FIX_WITH_LOG

confidence 0.75-0.90
    -> WARNING + REVIEW_RECOMMENDED

confidence < 0.75
    -> GUIDED_MODE_REQUIRED

high information-loss risk
    -> GUIDED_MODE_REQUIRED regardless of confidence

domain/business-rule ambiguity
    -> DOMAIN_RULE_REQUIRED

irreversible/destructive operation
    -> USER_CONFIRMATION_REQUIRED

unsupported operation
    -> UNSUPPORTED + alternative suggestions
```

These thresholds must be configurable rather than hard-coded as universal truths.

## 100.9 Automatic mode should explain what it did NOT do

A mandatory section of the report should be:

```text
What Auto Mode Did Not Change
```

Example:

```text
Auto Mode intentionally left the following unchanged:

- 9 conflicting duplicate invoice IDs
- 3 impossible dates with no inferable correction
- 14 possible outliers with legitimate-value probability
- 5 category pairs requiring semantic confirmation
- 1 suspected accounting formula mismatch
```

This prevents users from confusing `clean_df` with a perfectly verified dataset.

## 100.10 Clean dataset naming

The automatic output should support explicit naming that reflects confidence:

```python
result.clean_df
result.auto_clean_df
result.review_ready_df
```

A stronger label such as `verified_df` should only be available after all blocking and required-review items are resolved or explicitly waived.

For example:

```python
verified = result.finalize(
    require_no_blocking_issues=True
)
```

## 100.11 Interactive notification design

In SmartPrep Studio, completion of auto mode should show a summary panel:

```text
Automatic Preparation Completed

Scan coverage                     100%
Data health                       61 -> 91
Safe fixes applied                42
Warnings                           6
Review recommended                 4
Guided review required             2
Blocking issues                    0

[Open Clean Data]
[View Before/After Report]
[Review Warnings]
[Continue in Guided Mode]
[Export Current Pipeline]
```

If blocking issues exist:

```text
Automatic preparation stopped before finalization.
3 blocking issues require a decision.

[Resolve in Guided Mode]
[Inspect Issues]
[Export Partial Result]
```

## 100.12 Notification center

The UI should include a persistent `Data Quality Notification Center` with tabs:

```text
All
Auto-fixed
Warnings
Needs review
Blocking
Unresolved
Unsupported
```

Every notification should link directly to:

- affected rows;
- affected column;
- diagnostic visualization;
- explanation;
- treatment alternatives;
- preview;
- guided question.

## 100.13 Warning-aware reports

Every exported report, including PDF and interactive HTML, should include a prominent summary:

```text
Automatic Cleaning Status

Scan complete: YES
Scan coverage: 100%
Automatic repairs complete: YES
All issues resolved: NO
Manual review required: YES
```

The PDF must never bury unresolved critical issues in an appendix.

Interactive reports should allow clicking a warning to open the corresponding evidence and affected rows.

## 100.14 Optional stop policies

Users should be able to configure how strict Auto Mode is:

```python
sp.auto_prepare(
    df,
    on_warning="continue",
    on_high_warning="continue",
    on_critical="stop",
    on_ambiguous="guided",
)
```

Presets could include:

```text
fast
balanced
safe
research
regulated
```

For example, `research` should be conservative about transformations that may alter distributions or inferential properties.

## 100.15 Auto-to-Guided continuity requirement

A critical acceptance requirement is:

> Auto Mode and Guided Mode must be two interfaces over the same preparation engine, not two separate implementations.

Therefore every automatic decision must be representable as a guided decision card, and every guided decision must be representable in the reproducible pipeline.

## 100.16 New acceptance tests

The project must include tests verifying that:

- Auto Mode never silently discards unresolved issues.
- Every ambiguous issue produces a warning or escalation record.
- Destructive operations above the configured risk threshold require confirmation.
- Guided Mode can resume directly from an Auto Mode result.
- Already-applied safe fixes are not repeated incorrectly when Guided Mode starts.
- Issue IDs remain stable through the Auto -> Guided transition where possible.
- The final report distinguishes scan completion from cleaning completeness.
- `100% scan coverage` never implies `100% data correctness`.
- Unsupported problems are surfaced rather than ignored.
- Warnings appear in HTML, PDF, notebook, and programmatic result objects.
- A user can export a partially cleaned dataset while preserving unresolved-issue metadata.
- A dataset cannot be labeled `verified` while blocking issues remain unless the user explicitly waives them and the waiver is audited.

## 100.17 Recommended top-level API

The primary public API should therefore be:

```python
import smartprep as sp

# 1. Diagnosis only
scan = sp.scan(df)

# 2. Safe automatic preparation
auto = sp.auto_prepare(df)

# Inspect escalation state
print(auto.status)
print(auto.warnings)
print(auto.guided_items)

# 3. Continue only unresolved/ambiguous cases interactively
if auto.needs_guided_review:
    guided = auto.open_guided()

# 4. Or start fully guided from the beginning
guided = sp.guided_prepare(df)

# 5. Advanced visual workspace
sp.studio(df)
```

This four-entry design should be treated as a central usability requirement of SmartPrep.
