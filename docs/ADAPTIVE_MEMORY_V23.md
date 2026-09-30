# APCS v2.3 Adaptive Memory Policy

Status: **v0.1 prior — requires real-use calibration**

This engine is designed for programming-skill maintenance, not flashcard
memorization. It borrows the useful concepts of **stability** and
**retrievability**, but deliberately does not copy another learner's or a
flashcard system's fitted parameters into APCS practice.

## Why the old fixed schedule is retired

A fixed sequence such as:

```text
1d -> 3d -> 7d -> 30d -> 60d -> 90d
```

assumes that:
- every Skill decays at the same rate;
- every successful review gives the same evidence;
- repeated same-problem success equals delayed transfer;
- review count is a proxy for durable mastery.

Those assumptions are not appropriate for programming practice.

The v2.3 scheduler therefore has **no fixed review-count graduation**.

## Memory unit

```text
Skill x Track
```

Examples:

```text
S22_Prefix_Sum x Reading
S22_Prefix_Sum x Implementation
```

This is intentionally different from permanent per-problem scheduling.

A Problem is an evidence instrument. The durable memory estimate belongs to
the Skill/Track that the attempt actually observed.

## State

The first implementation stores/derives:

- `stability_days`: elapsed time at which estimated recall is 90%;
- `retrievability`: estimated recall probability today;
- evidence count;
- successful retrieval count;
- lapse count;
- latest outcome;
- scheduler policy version.

Retrievability uses the transparent curve:

```text
R(t, S) = 0.9 ^ (t / S)
```

This keeps the meaning of Stability easy to inspect and test.

## Evidence quality

A PASS is not automatically strong evidence.

The update considers:

- Outcome: PASS / PARTIAL / FAIL;
- Assistance A0-A5;
- Independent vs assisted;
- novelty:
  - transfer;
  - delayed retest;
  - mixed;
  - new;
  - seen;
  - same-problem repeat;
- actual elapsed time since prior evidence.

Important behavior:

```text
45d later + fresh transfer + A0 + independent + PASS
  >> evidence strength

same day + same problem + PASS
  >> weak long-term evidence
```

A same-day repeat is capped so it cannot artificially inflate Stability.

## Why successful delayed retrieval grows Stability more

A successful retrieval when estimated retrievability has already declined is
more informative than an immediate repeat. The v0.1 update therefore gives
more growth when:

```text
1 - retrievability
```

is larger, while applying diminishing returns as existing Stability grows.

This is a deliberately simple prior. It is not claimed to be the final
human-memory equation.

## Failure behavior

A failure reduces Stability and increments lapses.

It does **not** erase all prior learning. A Skill that was stable for months
and is missed once retains more residual Stability than a newly learned Skill.

There is no permanent `Graduated` state.

## Desired retention

The current default prior is:

```text
target retention = 0.88
```

This is intentionally configurable.

Higher desired retention creates shorter intervals and more review work.
The system will eventually calibrate target retention and model parameters
against the learner's real evidence/time history rather than manually chasing
a theoretical maximum.

## Workload governor

Scheduling is constrained by **time capacity**, not by the number of due
items.

Default prior:

```text
Review target     30%
Review hard max   35%
Protected new learning >= 60%
```

For a 60-minute APCS session:

```text
review budget = 18 min
```

A backlog of 10 or 1000 review candidates does not increase that budget.

Deferred candidates are:

```text
deferred
```

not:

```text
debt / missed homework
```

They are ranked again the next time capacity is available.

## Review priority

The selector is intentionally transparent:

1. recent failure;
2. curriculum importance;
3. lower retrievability;
4. greater overdueness;
5. cheaper task that fits the remaining budget.

No hidden "mastery score" is used for ordering.

## Long-term scaling

The design explicitly prevents:

```text
more solved problems
=> linearly more permanent reviews
```

As a Skill matures, maintenance should move toward:

```text
representative transfer
mixed practice
mock / contest evidence
```

rather than permanently re-solving every historical Problem.

One valid mixed attempt may generate several separate Evidence events only
when each Skill/Track was actually observable.

## Research basis

The design direction is informed by:

- Cepeda et al. (2008), spacing research showing that useful spacing depends
  on the desired retention horizon rather than one universal gap:
  https://pubmed.ncbi.nlm.nih.gov/19076480/
- FSRS / DSR concepts of Difficulty, Stability, and Retrievability:
  https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm
- Anki's FSRS guidance that desired retention trades directly against review
  workload, and that very high retention becomes expensive:
  https://docs.ankiweb.net/deck-options.html
- Settles & Meeder (2016), Half-Life Regression, showing the value of fitting
  memory models to real learner histories rather than relying only on fixed
  hand-picked schedules:
  https://aclanthology.org/P16-1174/

## Important limitation

Those sources do **not** establish that flashcard-trained FSRS parameters are
optimal for programming problem solving.

Therefore v0.1 uses:

- interpretable state;
- conservative priors;
- explicit evidence quality;
- versioned policy;
- deterministic tests.

After sufficient real APCS use, calibration should use the learner's own:

- elapsed intervals;
- PASS / PARTIAL / FAIL;
- assistance;
- fresh vs seen task;
- Skill / Track;
- time cost;
- lapses.

The model should then be changed only if held-out prediction/workload results
improve.

## v0.1 acceptance invariants

- no fixed sequence of review days;
- no fixed-count graduation;
- same-day repeated success gives little long-term credit;
- assistance weakens evidence;
- delayed independent transfer is strong evidence;
- a lapse reduces but does not erase mature memory;
- daily review budget is bounded by capacity;
- 1000 due candidates cannot create 1000 reviews today;
- new-learning time stays protected.
