# APCS v2.3 Curriculum Publish Pipeline

This pipeline keeps Notion editable without making live Notion draft state a runtime dependency.

## Flow

```text
Notion authoring
  -> normalized authoring export
  -> tools/curriculum_compiler.py validate
  -> deterministic compile
  -> reviewed Git snapshot
  -> CI
  -> VS Code runtime
```

The compiler deliberately has **no Notion API dependency**. Extraction and runtime publication are separate concerns.

## Normalized authoring bundle

Top-level shape:

```json
{
  "schema_version": "v2.3-authoring-1",
  "curriculum_version": "2026-09-30-draft",
  "skills": [],
  "problems": [],
  "placements": []
}
```

### Skill

A Skill is a curriculum concept/technique node.

Required runtime fields:

- `uid`
- `name`
- `unit`
- `path_stage`
- `path_order`
- at least one `track`
- valid prerequisite references

Tracks are currently:

- `Reading`
- `Implementation`

Prerequisites must form an acyclic graph.

### Problem

A Problem stores intrinsic/calibrated metadata.

Fields include:

- `pb_uid`
- `problem_id`
- `title`
- source/judge platform
- URL when available
- calibrated `D1`–`D5`
- publish lifecycle

Publish lifecycle:

```text
Draft
Published
Retired
```

Only `Published` problems enter the runtime snapshot.

A Published problem must have calibrated Difficulty.

A normal Published problem must have at least one Placement. An assessment-only benchmark may set:

```json
"assessment_only": true
```

and remain unplaced.

### Placement

Role is a property of curriculum use, not an intrinsic permanent Problem property.

A Placement contains:

- stable `placement_uid`
- `pb_uid`
- one `primary_skill`
- zero or more `supporting_skills`
- Role
- optional Lesson UID
- optional Lesson order

Current accepted Roles:

- Worked Example
- Guided Drill
- Core Independent
- Transfer Challenge
- Mock

A primary Skill cannot also appear in supporting Skills.

## Commands

Validate a normalized authoring export:

```bash
python3 tools/curriculum_compiler.py validate curriculum/source.v23.json
```

Compile a deterministic runtime snapshot:

```bash
python3 tools/curriculum_compiler.py compile \
  curriculum/source.v23.json \
  curriculum/published.v23.json
```

Check that an existing published snapshot is current:

```bash
python3 tools/curriculum_compiler.py check \
  curriculum/source.v23.json \
  curriculum/published.v23.json
```

## Why source and published data are separate

Notion authoring is allowed to contain incomplete Draft work.

The runtime is not.

For example:

- Draft problem with no Difficulty: allowed.
- Published problem with no Difficulty: rejected.
- Placement pointing to a missing Skill: rejected.
- cyclic Skill prerequisites: rejected.
- duplicate published external Problem identity: rejected.

This avoids turning every unfinished authoring edit into a production runtime incident.

## Current migration status

The compiler and publish invariants are implemented before any destructive Notion migration.

The next live-data step is:

1. extract current Skill Map / Problem Bank into the normalized authoring shape;
2. run validation;
3. inspect every rejection;
4. repair authoring semantics rather than weakening the validator;
5. publish the first real curriculum snapshot.

Do not automatically convert old repository Tags or Notion fields merely to make validation pass.

## Long-term rule

If a new field changes deterministic runtime behavior, it belongs in the versioned Git contract or compiled snapshot.

If a field exists mainly to explain, teach, author, or reflect, it can remain Notion-native.

