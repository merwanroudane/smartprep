# References

SmartPrep is built on ideas proven by the existing Python data ecosystem. This
file records what was reviewed, what was learned, and what SmartPrep adds.

**No code was copied from any project listed here.** Ideas and design patterns
were studied; implementations are original. Where a project is a runtime
dependency, its license is recorded in the dependency section.

Each entry follows the same structure so the rationale for a design decision can
be traced back to its source.

---

## Profiling and automated EDA

### ydata-profiling
- Docs: https://docs.profiling.ydata.ai/
- Repository: https://github.com/ydataai/ydata-profiling

**Learned:** the value of a single-call comprehensive report; the alerts system;
the explicit position in its own documentation that an alert is not necessarily
a problem and that domain knowledge decides.

**SmartPrep adds:** the alert becomes the *start* of a workflow rather than its
end — evidence, severity, confidence, candidate treatments, expected impact,
and a triage decision about whether repair may proceed without asking.

### Sweetviz
- Repository: https://github.com/fbdesignpro/sweetviz

**Learned:** comparative EDA as a first-class idea — dataset vs dataset, train vs
test, target-aware analysis in a self-contained HTML report.

**SmartPrep adds:** the comparison axis becomes before vs after *cleaning*, so
the user can see what a repair decision did to distributions and relationships.

### DataProfiler (Capital One)
- Docs: https://capitalone.github.io/DataProfiler/
- Repository: https://github.com/capitalone/DataProfiler

**Learned:** semantic labelling at cell level; mergeable profiles; PII detection
integrated into profiling rather than bolted on.

**SmartPrep adds:** semantic type drives the *cleaning* path — a column detected
as a phone number gets parsing, validation and quarantine, not just a label.

### missingno
- Repository: https://github.com/ResidentMario/missingno

**Learned:** missingness deserves dedicated visual diagnostics — matrix, bar,
heatmap, dendrogram.

**SmartPrep adds:** missingness is classified by whether absence is
*structurally expected*. An unpaid invoice with no payment date is correct data,
not a defect, and must not be counted in a headline rate that drives imputation.

---

## Cleaning and wrangling

### pyjanitor
- Docs: https://pyjanitor-devs.github.io/pyjanitor/
- Repository: https://github.com/pyjanitor-devs/pyjanitor

**Learned:** a readable, chainable cleaning API with clear verb names, and the
principle of not hiding what is happening from the user.

**SmartPrep adds:** every operation carries metadata — reason, confidence, rows
affected, reversibility, audit id.

### DataPrep.Clean
- Docs: https://docs.dataprep.ai/user_guide/clean/introduction.html
- Repository: https://github.com/sfu-db/dataprep

**Learned:** cleaning should be driven by semantic type, not `dtype` — countries,
dates, emails, phone numbers and URLs each need their own logic.

**SmartPrep adds:** the semantic type is *inferred with a confidence*, and
parse outcomes are reported as success / ambiguous / invalid rather than
silently coerced.

### skrub
- Docs: https://skrub-data.org/
- Repository: https://github.com/skrub-data/skrub

**Learned:** dirty categorical data must be reconciled *before* encoding, or the
errors get encoded too.

**SmartPrep adds:** variant clusters are graded — mechanical merges (whitespace,
case, punctuation) are separated from semantic ones (spelling, language), and
only the former can be applied without confirmation.

---

## Validation and contracts

### Pandera
- Docs: https://pandera.readthedocs.io/
- Repository: https://github.com/unionai-oss/pandera

**Learned:** schema-first validation, lazy validation that collects all errors,
schema serialisation, and multi-backend design.

**SmartPrep adds:** schemas are *inferred and proposed* with evidence and
confidence, rather than written by hand from scratch.

### Great Expectations
- Docs: https://docs.greatexpectations.io/
- Repository: https://github.com/great-expectations/great_expectations

**Learned:** declarative expectations, reusable suites, production quality gates.

**SmartPrep adds:** a failed expectation links to root-cause clues, affected
records, candidate repairs and post-repair revalidation.

### Pointblank
- Docs: https://posit-dev.github.io/pointblank/
- Repository: https://github.com/posit-dev/pointblank

**Learned:** validation as a readable *plan* with warning / error / critical
thresholds, and the ability to extract failing rows rather than only a verdict.

**SmartPrep adds:** thresholds feed the same severity model used by detection, so
validation and diagnosis speak one language.

### Soda Core / Frictionless
- https://github.com/sodadata/soda-core
- https://framework.frictionlessdata.io/

**Learned:** data contracts as formal, versioned agreements; resource and schema
concepts beyond the DataFrame.

**SmartPrep adds:** an interactive cleaning session can be exported *as* a
contract, so exploratory work becomes a production gate.

---

## Preprocessing

### scikit-learn
- Preprocessing: https://scikit-learn.org/stable/modules/preprocessing.html
- Imputation: https://scikit-learn.org/stable/modules/impute.html

**Learned:** `fit`/`transform` separation as the mechanism that prevents
leakage; `Pipeline` and `ColumnTransformer` composition.

**SmartPrep adds:** recommendation — which transformer suits *this* column for
*this* goal, and why — plus a leakage guard that refuses to fit on combined
train and test data.

### feature-engine
- Docs: https://feature-engine.trainindata.com/

**Learned:** breadth of transformers with variable names preserved throughout.

**SmartPrep adds:** treatment comparison across alternatives on distortion,
stability, leakage risk and interpretability.

### category_encoders
- Docs: https://contrib.scikit-learn.org/category_encoders/

**Learned:** the encoder families beyond one-hot — target, CatBoost, WOE,
hashing, GLMM, leave-one-out.

**SmartPrep adds:** an advisor that selects among them using cardinality, sample
size, target type, leakage risk, model family and memory cost.

---

## Anomalies and data-centric quality

### PyOD
- Docs: https://pyod.readthedocs.io/

**Learned:** breadth of outlier algorithms; anomaly *scores* rather than binary
verdicts.

**SmartPrep adds:** an explicit distinction between a statistical outlier, a
rare-but-valid observation, a sentinel code and a data-entry error — and no
`remove_outliers()` default.

### Cleanlab
- Docs: https://docs.cleanlab.ai/

**Learned:** data quality is not only syntactic; label errors and near
duplicates are quality problems too.

**SmartPrep adds:** those findings share one issue inbox with schema,
missingness and duplicate findings instead of living in a separate system.

---

## Text, dates and entity resolution

| Project | Learned | SmartPrep adds |
|---|---|---|
| [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | Fast string similarity and ranked candidate matches | Similarity is one input among frequency, locale and semantic type; merges are proposed, never applied silently |
| [recordlinkage](https://github.com/J535D165/recordlinkage) / [dedupe](https://github.com/dedupeio/dedupe) | Blocking, pairwise comparison, probabilistic linkage | Conflicting records are never merged automatically; field-level provenance survives the merge |
| [ftfy](https://github.com/rspeer/python-ftfy) | Mojibake and encoding repair | Accented Latin letters are explicitly excluded from confusable detection — `Algérie` is correct French |
| [dateparser](https://github.com/scrapinghub/dateparser) / [dateutil](https://github.com/dateutil/dateutil) | Multi-format and locale-aware date parsing | Ambiguity is *reported*, not resolved by a `dayfirst` flag; invalid, ambiguous, format-conflicting and valid are four distinct outcomes |
| [pycountry](https://github.com/pycountry/pycountry) | ISO country, currency and language codes | Reference data modelled as an entity graph with aliases and transliterations, because a flat map under-reports conflicts |

---

## Execution and interoperability

| Project | Learned |
|---|---|
| [pandas](https://pandas.pydata.org/docs/) | DataFrame semantics, missing-value handling, IO |
| [Polars](https://docs.pola.rs/) | Expression API, lazy execution, query optimisation |
| [PyArrow](https://arrow.apache.org/docs/python/) | Columnar memory model, null semantics, zero-copy interchange |
| [DuckDB](https://duckdb.org/docs/) | SQL over files, predicate pushdown |
| [Narwhals](https://narwhals-dev.github.io/narwhals/) | Building a dataframe-agnostic library without coupling to one backend |
| [Ibis](https://ibis-project.org/) | Portable expressions compiled to many backends |

**SmartPrep adds:** a semantic operation IR with explicit backend capability
negotiation and a no-silent-fallback rule — if an operation requires
materialising a large dataset into pandas, the user is told the estimated cost
before it happens. *(Planned; not in v0.1.)*

---

## Observability, privacy and lineage

| Project | Learned |
|---|---|
| [whylogs](https://whylogs.readthedocs.io/) | Lightweight mergeable statistical profiles for continuous monitoring |
| [Evidently](https://docs.evidentlyai.com/) / [Deepchecks](https://docs.deepchecks.com/) | Drift reports and the report/test duality |
| [Alibi Detect](https://docs.seldon.ai/alibi-detect/) | Separating outliers, data drift, concept drift and online drift |
| [River](https://riverml.xyz/) | Incremental statistics; preprocessing without access to the future |
| [Presidio](https://microsoft.github.io/presidio/) | PII detection combining NER, regex, checksums and context |
| [OpenLineage](https://openlineage.io/docs/) | Dataset / Job / Run as a portable provenance model |

**SmartPrep adds:** *cleaning drift* — tracking whether the nature of the errors
requiring repair is itself changing over time, which points at an upstream
source change rather than a local data problem. *(Planned; not in v0.1.)*

---

## Methodological references

These inform algorithm choices rather than API design.

**Missing data**
- Rubin, D. B. *Multiple Imputation for Nonresponse in Surveys.*
- Little, R. J. A. & Rubin, D. B. *Statistical Analysis with Missing Data.*
- van Buuren, S. *Flexible Imputation of Missing Data.*
- Stekhoven & Bühlmann. MissForest — non-parametric missing value imputation
  using random forest.

*Applied as:* imputation is never selected on reconstruction error alone; the
missingness mechanism and the inferential goal must inform the choice.

**Outliers and robust statistics**
- Tukey, J. W. *Exploratory Data Analysis.*
- Huber, P. J. & Ronchetti, E. M. *Robust Statistics.*
- Rousseeuw, P. J. & Leroy, A. M. *Robust Regression and Outlier Detection.*
- Liu, Ting & Zhou. Isolation Forest.
- Breunig et al. LOF: Identifying Density-Based Local Outliers.

*Applied as:* detection is separated from treatment, and outlier never implies
delete.

**Categorical encoding and leakage**
- Micci-Barreca. A preprocessing scheme for high-cardinality categorical
  attributes.
- Prokhorenkova et al. CatBoost — ordered target statistics.

*Applied as:* cross-fitting is required for target-based encoders.

**Drift and two-sample testing**
- Kolmogorov–Smirnov test.
- Gretton et al. Maximum Mean Discrepancy.
- Bifet & Gavaldà. ADWIN.
- Population Stability Index — industry practice; note that no single canonical
  definition exists in the literature, which is why no universal threshold is
  applied.

**Entity resolution**
- Fellegi, I. P. & Sunter, A. B. A Theory for Record Linkage.

*Applied as:* exact duplicates, fuzzy duplicates and conflicting entities are
handled as three different problems.

---

## Runtime dependencies

| Package | License | Why |
|---|---|---|
| pandas | BSD-3-Clause | DataFrame implementation |
| numpy | BSD-3-Clause | Numerical kernels |
| openpyxl *(extra)* | MIT | Excel reading |

All are permissively licensed and compatible with Apache-2.0 distribution.
Licenses must be re-verified at the pinned version before each release.

---

## A note on completeness

No project can claim to have reviewed every package on PyPI; the ecosystem
changes daily. The standard applied here is **comprehensive functional coverage
plus best-in-class representatives per category**, with a registry that is
updated when a project offers a capability not already represented.
