# Contributing to SmartPrep

## The one rule that matters

**A detector is not complete until it ships with a negative control.**

False positives are the primary failure mode of automated cleaning tools. A
detector that finds every real instance of a problem and also flags twenty
legitimate values has made the data worse, because it trains users to dismiss
the output.

So every pull request adding detection must include:

1. A positive test proving it finds the problem.
2. A negative test proving it leaves a *similar-looking but legitimate* value
   alone.

The canonical example: `Manufacturıng` (dotless i, U+0131) must be caught, and
`Algérie` must not. Both contain a non-ASCII character. Only one is damage.

## Setup

```bash
git clone https://github.com/merwanroudane/smartprep
cd smartprep
pip install -e ".[dev]"
pytest
```

## Before opening a pull request

```bash
pytest
ruff check src tests
ruff format --check src tests
mypy
```

## Design constraints

These are frozen in `_ARCHITECTURE_DECISIONS.md` and are not open to casual
change. If your work requires breaking one, say so explicitly in the pull
request and explain why.

- **Detectors never mutate.** `scan()` asserts this at runtime and raises if
  violated.
- **Detection confidence is not repair confidence.** Being sure a value is
  wrong says nothing about what the right value is. Only `repair_confidence`
  reaches the autonomy ladder.
- **Irreversible operations can never be `SAFE_AUTO_FIX`**, regardless of
  confidence. Row deletion, column deletion, outlier removal, entity merge and
  category merge are irreversible by definition.
- **Abstention is a valid outcome.** If no correct value is inferable, emit an
  issue with no treatment candidate. Do not invent one.
- **Report coverage separately from health.** Completing every check says
  nothing about whether the data is correct.

## Adding a detector

1. Implement the `Detector` protocol: a `name` attribute and a
   `detect(frame, **context) -> list[Issue]` method.
2. Decorate the class with `@register`.
3. Give every `TreatmentCandidate` an honest `repair_confidence`. Resist the
   urge to inflate it -- the ladder is the safety mechanism, and a padded
   number disables it.
4. Set `reversibility`, `information_loss_risk`, `domain_sensitivity` and
   `statistical_impact` accurately. These demote the repair class and are how
   the library stays safe when confidence is high but the operation is
   dangerous.
5. Write both tests.

## Baseline counts are a contract

`_STRESS_TEST_BASELINE.md` records verified counts from a real dataset. The
acceptance suite asserts them exactly.

If your change moves one of those numbers, that is a behaviour change. Update
the baseline document **and** explain the change in the pull request. Never
adjust a test to match new output without understanding why the output moved.

## Attribution

Contributions are authored by their contributors. Do not add generated-by or
assistant attribution to commits, code comments, documentation or release
notes.
