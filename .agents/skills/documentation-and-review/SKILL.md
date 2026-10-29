---
name: documentation-and-review
description: >-
  Provides procedures for compiling data dictionaries, writing Architecture Decision Records (ADR),
  capturing test execution evidence, auditing peer code contributions, and preparing university assignment deliverables.
  Use when documenting architectural decisions, creating data dictionaries, or conducting peer reviews.
---

# Documentation and Review Skill

## When to Use This Skill
Use this skill when recording architecture decisions, maintaining data dictionaries, conducting peer code reviews, compiling test execution evidence, and synthesizing final university assignment documentation.

## Documentation Procedures

### 1. Architecture Decision Records (ADR)
For significant design choices (e.g. Kimball constellation vs single star, 15-minute grain vs hourly grain, PostgreSQL 18 partitioning):
1. Create a markdown record in `docs/architecture/adr/`:
   - Title: `ADR-00X: <Decision Name>`
   - Status: Proposed | Accepted | Deprecated | Superseded
   - Context: Problem statement and academic requirements.
   - Decision: The chosen technical approach and technical rationale.
   - Consequences: Trade-offs, positive impacts, and negative limitations.

### 2. Comprehensive Data Dictionaries
For every table in the warehouse:
1. Document in `docs/database/data-dictionary.md`:
   - Table Name and Schema
   - Business Purpose & Kimball Classification (Fact, Dimension, Outrigger)
   - Grain statement
   - Column attributes: Column Name, Data Type, Nullable, Primary/Foreign Key, Unit of Measure, Default Value, Description, Source Lineage.

### 3. Test Evidence Capture
1. Always capture unedited CLI execution outputs from tests, linters, and database queries.
2. Store reports in `docs/testing/`:
   - Command invoked
   - Timestamp of execution
   - Environment details (OS, Python version, Docker version, PostgreSQL version)
   - Test results count (Passed, Failed, Skipped)
   - Coverage percentage

### 4. Code Review Checklist
Before approving any Pull Request into `development`:
- [ ] Conforms to TDD: Unit/integration tests added and passing.
- [ ] No hardcoded secrets, passwords, or live credentials.
- [ ] Migrations are additive and follow sequential naming.
- [ ] Python code passes `ruff check` and `mypy`.
- [ ] Data transformations adhere to Lecture 6 preprocessing rules.
- [ ] Documentation updated to reflect changes.

## Expected Outputs
- Completed ADRs in `docs/architecture/adr/`
- Up-to-date data dictionary in `docs/database/`
- Verified test evidence in `docs/testing/`
- Signed-off Pull Request reviews

## Verification Steps
1. Verify all markdown internal links are valid and resolve to actual files.
2. Confirm test evidence logs contain zero simulated or placeholder outputs.
