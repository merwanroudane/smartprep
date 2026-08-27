# SmartPrep 1.0.0 — Corrections Only

**Scope:** SmartPrep `1.0.0`  
**Purpose:** Fix defects and inconsistencies in the current package only.  
**Out of scope:** New features, new backends, new analytical modules, new product capabilities, and all post-1.0 roadmap items.

---

# 1. Scope rule

This correction pass must follow one strict rule:

> **Do not add functionality. Make the existing `1.0.0` implementation, documentation, metadata, architecture records, and release claims agree with each other.**

Therefore this document deliberately excludes:

- Multi-backend execution
- new Polars/DuckDB/Arrow/Spark support
- new semantic packs
- new root-cause engine
- new plugin system
- new preprocessing algorithms
- new Studio features
- new visualization types
- new monitoring system
- any other feature planned for later releases

Those are enhancements, not defects in `1.0.0`.

---

# 2. Current technical baseline

The reviewed source distribution is technically strong.

The non-slow suite completed with:

```text
677 passed
51 skipped
11 deselected
0 failed
```

A focused suite covering the major 1.0 capabilities completed with:

```text
278 passed
0 failed
```

The 51 skips are associated with the external stress-test workbook that is intentionally not distributed inside the sdist.

Therefore there is no evidence from the executed test suites of a failing core feature that needs emergency algorithmic repair.

The real corrections found are primarily **release consistency, documentation/status accuracy, and maintenance hygiene**.

---

# 3. Correction priority summary

| ID | Correction | Severity | Type |
|---|---|---:|---|
| FIX-01 | Remove stale Studio statement saying implemented features do not exist | **P0** | Public documentation |
| FIX-02 | Update stale `AD-010` implementation status | **P1** | Architecture documentation |
| FIX-03 | Remove impossible `Planned (v0.9)` status from Multi-backend capability | **P1** | Release metadata |
| FIX-04 | Clarify benchmark terminology so implemented performance budgets are not confused with a future comparative benchmark suite | **P2** | Documentation |
| FIX-05 | Re-run generated capability/documentation consistency checks after corrections | **P1** | Regression prevention |
| FIX-06 | Verify rebuilt PyPI long description before publishing the patch | **P1** | Release QA |
| FIX-07 | Re-run full package/release gates after documentation and metadata changes | **P1** | Release QA |

No new feature should be attached to any of these fixes.

---

# 4. FIX-01 — Public README/PyPI Studio contradiction

## Problem

The capability table correctly reports that the following are implemented:

```text
Faceting and multi-series composition
Visual Workflow Builder / Pipeline Canvas
Entity resolution
Time-series and panel diagnostics
```

However, a later Studio paragraph still states that some of these capabilities:

```text
do not exist yet
```

In particular, the stale wording refers to:

- Visual Workflow
- Faceting
- Multi-series composition

This is a real defect because the same stable release contradicts itself.

The code, tests, capability registry and later architecture decisions indicate that these features are implemented.

## Why it matters

This is public-facing documentation on PyPI.

A user can read:

```text
Implemented
```

and then a few paragraphs later read:

```text
does not exist yet
```

That reduces confidence in the stable release even though the implementation itself is correct.

## Required correction

Delete the obsolete claim.

Replace the Studio description with wording that reflects the current implementation only.

### Suggested replacement

```markdown
### Studio

SmartPrep 1.0 includes the visual analytics foundation introduced in
earlier releases together with faceting, multi-series composition and
the Visual Workflow / Pipeline Canvas.

The Studio shares the same Core operations, audit semantics and
analytical results used by the code-first API. Visual filtering and
selection affect the current view; they do not silently mutate the
underlying dataset.

The portable HTML Studio uses analytical compositions produced by
Python and does not embed a second dataframe-processing engine in
JavaScript.
```

## Do not do

Do not use this correction as a reason to implement a new Live Studio.

That would be a new feature.

## Acceptance test

Search the final README/PyPI description for obsolete phrases such as:

```text
do not exist yet
not yet implemented
not started
```

and verify that none refers to a capability currently marked `Implemented`.

---

# 5. FIX-02 — Stale `AD-010` status

## Problem

`_ARCHITECTURE_DECISIONS.md` contains historical text in `AD-010` describing capabilities such as:

- workflow
- pipeline canvas
- faceting
- multi-series
- entity resolution
- time-series diagnostics
- panel diagnostics

as absent.

That was true when the decision was originally written.

It is no longer the current state of `1.0.0`.

Later ADRs and the implementation show that these capabilities subsequently landed.

## Why it matters

Architecture Decision Records should preserve historical reasoning, but readers must be able to distinguish:

```text
state when decision was written
```

from:

```text
current implementation state
```

Otherwise the architecture documentation contradicts the code.

## Required correction

Do **not** delete the historical decision.

Preserve the original reasoning and explicitly date/label the old implementation state.

### Recommended pattern

```markdown
## AD-010 — ...

**Decision status:** Accepted  
**Historical implementation status:** This section originally described
the state at the v0.6 stage.

**Current implementation status (1.0.0):** The staged build order has
been completed through the 1.0 release. Visual Workflow / Pipeline
Canvas, faceting, multi-series composition, entity resolution,
time-series diagnostics and panel diagnostics are now implemented.
See the later architecture decisions for their final design.
```

If the document already links the later ADRs, preserve those links.

## Do not do

Do not rewrite the historical rationale to make it appear that the final implementation existed when AD-010 was originally written.

The goal is historical accuracy plus current-status clarity.

## Acceptance test

A reader opening AD-010 should immediately understand:

1. what was decided at that time;
2. what was absent at that time;
3. what is implemented now;
4. which later ADRs supersede the old implementation-status notes.

---

# 6. FIX-03 — Invalid `Planned (v0.9)` metadata

## Problem

The capability registry/current documentation contains a future capability with metadata equivalent to:

```text
Multi-backend execution — Planned (v0.9)
```

The current package is:

```text
1.0.0
```

A capability cannot remain planned for an already-passed pre-1.0 milestone.

## Why it matters

This is a metadata consistency defect.

It does **not** mean Multi-backend must be implemented now.

The error is the obsolete milestone number.

## Required correction

Since the user does not want to commit this feature to the current release, the safest correction is:

```text
Planned
```

without assigning a version.

If the registry requires a nullable milestone:

```python
planned_for=None
```

or the equivalent supported representation.

If the registry requires a string, use a neutral future value only if the project has already formally chosen one.

Do not invent `v1.1`, `v1.2`, etc. merely to silence the inconsistency.

## Preferred final presentation

```text
Multi-backend execution | Planned
```

## Do not do

Do not implement Multi-backend as part of this correction.

Do not add empty adapters merely to make the status look more advanced.

Do not promise a release number that has not been decided.

## Acceptance test

The final public documentation must contain no feature marked as planned for a version lower than the currently published `1.0.0`.

---

# 7. FIX-04 — Benchmark terminology ambiguity

## Problem

The package contains actual tests for performance/regression budgets.

At the same time, roadmap/documentation language may refer to a broader future:

```text
Benchmark Suite
```

These are not the same thing.

The current tests measure internal performance/scaling budgets.

They are not necessarily a full comparative benchmark against other libraries.

## Required correction

Rename/document the existing concept precisely.

Recommended terminology:

```text
Performance Regression Budgets — Implemented
```

If a broader comparative benchmark remains mentioned anywhere, call it:

```text
Comparative Benchmark Suite — Planned
```

or remove the future item from current release documentation if it is unnecessary.

## Do not do

Do not build a new benchmark framework in this correction release.

This is a terminology/documentation correction only.

## Acceptance test

A reader should not infer that SmartPrep currently ships a complete cross-library comparative benchmark merely because `tests/test_benchmarks.py` exists.

---

# 8. FIX-05 — Capability Registry consistency verification

## Problem

The Capability Registry was introduced specifically to prevent capability/documentation drift.

The stale Studio prose demonstrates that a capability table can be synchronized while free-form prose still becomes outdated.

## Required correction

This correction does not require a new product feature.

At minimum:

1. update the stale prose;
2. run the existing capability-registry tests;
3. inspect every occurrence of capability-status language in README;
4. verify it agrees with the registry.

If a small test can be added without changing product behavior, it is acceptable to strengthen documentation regression coverage.

For example, a test may assert that known obsolete statements are absent.

This is maintenance/test hardening, not a new user-facing feature.

## Acceptance criteria

The following sources should agree:

```text
Capability Registry
README capability table
README descriptive prose
CHANGELOG current release
Architecture current-status notes
public API
```

---

# 9. FIX-06 — Rebuild and inspect PyPI long description

## Problem

Fixing `README.md` in the repository is insufficient if the next package uploaded to PyPI still renders stale or malformed text.

## Required correction procedure

After editing README:

```bash
python -m build
python -m twine check --strict dist/*
```

Then inspect the built metadata/long description before upload.

Confirm that the rendered package description no longer contains the obsolete Studio paragraph.

Also verify:

- headings render correctly;
- code fences are intact;
- tables render;
- links remain valid;
- capability statuses are current.

## Acceptance test

The README in the source tree, the README packaged in the sdist/wheel, and the PyPI long description must communicate the same capability state.

---

# 10. FIX-07 — Full release-gate rerun

Even though the identified corrections are mostly documentation/metadata changes, the patch release should still pass the normal release gates.

## Required checks

Run the complete project test suite according to the repository's documented release procedure.

At minimum verify:

```text
pytest
ruff
mypy
build
twine check --strict
clean-environment install
```

Use the exact commands already defined by the project rather than introducing a new release process.

## Why

A documentation-only change can still accidentally affect:

- package inclusion
- metadata
- README rendering
- capability-registry tests
- source distribution contents

## Acceptance criteria

No regression from the verified `1.0.0` baseline.

---

# 11. Stress-test workbook skips

## Current observation

The review produced:

```text
51 skipped
```

because `data_project.xlsx` is intentionally not distributed inside the source package.

This is **not currently classified as a defect**.

## Required action

No code change is required solely because of these skips.

However, before publishing a patch, the maintainer should run the private/full stress-test suite in the development/release environment where the workbook is available.

## Do not do

Do not add the real workbook to the public sdist merely to remove skip counts unless it is intentionally licensed and appropriate to distribute.

---

# 12. Slow tests

The review command excluded:

```text
11 slow tests
```

during the main fast run.

This is also **not a defect**.

These tests represent performance budgets.

## Required action before release

Run them in the project's intended release/CI environment if that is part of the release gate.

Do not weaken thresholds merely to make the patch pass.

---

# 13. `ruff` / `mypy` independent verification note

During the external review runtime, `ruff` and `mypy` were not independently available as executables.

The project declares them in development dependencies.

This is **not a discovered package defect**.

## Required action

The maintainer should execute the project's normal:

```text
ruff
mypy
```

checks in the release environment.

No code modification is justified unless those checks actually report an error.

---

# 14. Corrections that should NOT be made

The following items from the broader roadmap are explicitly excluded from this patch.

## Do not add Multi-backend

No:

- Polars execution layer
- DuckDB execution layer
- Arrow execution layer
- Spark execution layer
- Ibis execution layer

in this correction pass.

## Do not add new Studio capabilities

No:

- Live Studio
- new chart types
- new linked-selection engine
- new visual grammar
- new animation system

unless fixing an actual existing regression.

## Do not add new cleaning capabilities

No:

- new detectors
- new semantic packs
- new imputation methods
- new encoders
- new anomaly algorithms

in this patch.

## Do not add new platform layers

No:

- plugin ecosystem
- observability platform
- root-cause engine
- hosted documentation application

as part of the correction release.

Those belong to later feature versions.

---

# 15. Recommended patch version

Because the discovered problems are primarily documentation/status/metadata consistency issues, a patch release is appropriate:

```text
1.0.1
```

The patch should be deliberately small.

Suggested release theme:

> **SmartPrep 1.0.1 — Stable Release Consistency Fixes**

---

# 16. Recommended `1.0.1` CHANGELOG entry

```markdown
## 1.0.1

### Fixed

- Corrected stale Studio documentation that described faceting,
  multi-series composition and Visual Workflow as unavailable even
  though they are implemented in the 1.0 release.
- Updated the historical AD-010 implementation-status note so that it
  no longer describes the old v0.6 feature state as the current state.
- Removed the obsolete `v0.9` milestone from the planned multi-backend
  capability.
- Clarified the distinction between implemented performance-regression
  budgets and any future comparative benchmark suite.
- Revalidated capability documentation and release metadata against the
  current 1.0 implementation.
```

Do not list new features in this patch.

---

# 17. Suggested correction sequence

Use this order:

```text
1. README / PyPI prose
        ↓
2. Capability metadata
        ↓
3. AD-010 current-status note
        ↓
4. Benchmark terminology
        ↓
5. Documentation consistency checks
        ↓
6. Full tests
        ↓
7. Slow/private stress tests
        ↓
8. ruff + mypy
        ↓
9. build wheel + sdist
        ↓
10. twine check --strict
        ↓
11. clean-venv installation
        ↓
12. inspect built README/metadata
        ↓
13. publish 1.0.1
```

---

# 18. Definition of Done for the correction release

`1.0.1` is ready when all of the following are true:

- [ ] No public paragraph says an implemented 1.0 capability does not exist.
- [ ] AD-010 clearly distinguishes historical state from current 1.0 state.
- [ ] No capability is marked `Planned (v0.9)`.
- [ ] Performance budgets are not mislabeled as a complete comparative benchmark suite.
- [ ] Capability registry tests pass.
- [ ] README consistency checks pass.
- [ ] Main test suite passes.
- [ ] Slow release tests pass in the intended environment.
- [ ] Private stress-test regression suite passes where the workbook is available.
- [ ] `ruff` passes.
- [ ] `mypy` passes.
- [ ] wheel builds.
- [ ] sdist builds.
- [ ] `twine check --strict` passes for both artifacts.
- [ ] clean virtual-environment install succeeds.
- [ ] installed package reports `1.0.1`.
- [ ] built long description has been manually inspected.
- [ ] PyPI page after publication shows the corrected text.

---

# 19. What is a real blocker?

Based on the reviewed package and executed tests, no verified core algorithmic failure currently blocks `1.0.0`.

The most important verified defect is:

> **the stable release's public documentation contradicts its implemented capability state.**

That should be corrected promptly because it affects the credibility and clarity of the release.

The other confirmed corrections are maintenance/status consistency issues rather than broken cleaning algorithms.

---

# 20. Final correction list

For the current package, fix only these items:

### P0

**1. Correct the stale Studio paragraph in README/PyPI.**

### P1

**2. Correct AD-010 current implementation status.**

**3. Remove the obsolete `v0.9` planned milestone.**

**4. Revalidate all capability/status claims against the registry.**

**5. Rebuild and verify PyPI metadata.**

**6. Run all release gates before publishing the patch.**

### P2

**7. Clarify performance-budget vs comparative-benchmark terminology.**

Everything else belongs to later feature releases.

---

# 21. Final recommendation

Do **not** expand SmartPrep in this pass.

The appropriate action is:

```text
SmartPrep 1.0.0
      ↓
Consistency / documentation / metadata corrections
      ↓
Regression verification
      ↓
SmartPrep 1.0.1
```

The objective of `1.0.1` should be:

> **Make every statement surrounding the stable release accurately describe the functionality that already exists, without changing SmartPrep's product scope.**

That is the cleanest and safest correction strategy for the current package.
