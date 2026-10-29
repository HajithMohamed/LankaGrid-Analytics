---
trigger: always_on
description: Branching strategy, commit message standards, code reviews, and team collaboration rules
---
# Git Workflow & Team Collaboration Rules

## Branching Strategy
- **`main`**:
  - Protected release branch.
  - Contains only fully verified, production-ready code.
  - **No direct commits to `main`**.
- **`development`**:
  - Integration branch for completed and reviewed features.
  - Baseline branch for all feature and chore branches.
- **Feature Branches**:
  - Format: `<type>/<phase-or-feature-name>` or `<type>/member<N>-<feature>`
  - Examples:
    - `chore/phase-0-foundation`
    - `feat/member1-generation-etl`
    - `feat/member2-dispatch-schema`
    - `test/member6-data-quality`

## Commit Conventions (Conventional Commits)
All commit messages must follow the standard:
`<type>(<scope>): <short description in present tense>`
- Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `ci`
- Examples:
  - `chore(foundation): initialize repository structure and docker environment`
  - `feat(ingestion): implement pucl daily generation pdf parser`
  - `test(quality): add unit tests for missing value and outlier filters`

## Code Review & Merge Standards
- All changes must enter `development` through a Pull Request (PR) referencing [PULL_REQUEST_TEMPLATE.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.github/PULL_REQUEST_TEMPLATE.md).
- At least one peer review approval is required before merging.
- CI pipeline (lint, unit tests, integration tests) must pass with zero failures.
- Merge conflict resolution must be done on the feature branch via rebase or merge from `development` before merging into `development`.
