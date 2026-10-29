---
name: test-driven-development
description: >-
  Provides procedures for Test-Driven Development (Red-Green-Refactor), test suite structuring,
  unit testing, database integration testing, ETL validation, and regression testing.
  Use when writing tests, implementing new features, or refactoring existing code.
---

# Test-Driven Development (TDD) Skill

## When to Use This Skill
Use this skill for all code modifications, bug fixes, data parsing modules, and database operations. No implementation code may be written without an accompanying failing test.

## The TDD Protocol

### Phase 1: Red (Failing Test First)
1. Formulate the contract and expected behavior:
   - What input data is provided?
   - What boundary conditions or errors should occur?
   - What is the exact expected output structure or database state?
2. Write a minimal test in `tests/unit/`, `tests/integration/`, or `tests/data_quality/`.
3. Execute the test:
   ```bash
   pytest tests/path/to/test_feature.py
   ```
4. **MANDATORY VERIFICATION**: Confirm that the test fails for the expected reason (e.g. `AssertionError`, `NotImplementedError`, `TableNotFoundError`).
5. Save the failure message as evidence.

### Phase 2: Green (Minimal Implementation)
1. Write the minimal production code necessary to satisfy the test.
2. Avoid premature optimization or implementing speculative features.
3. Re-execute the test command:
   ```bash
   pytest tests/path/to/test_feature.py
   ```
4. Confirm the test passes with green CLI output.

### Phase 3: Refactor
1. Review the newly written code for readability, type hints, error handling, and performance.
2. Ensure consistent naming conventions and modular separation.
3. Re-run the full test suite to guarantee zero regression:
   ```bash
   pytest
   ```

## Test Hierarchy
- **Unit Tests (`tests/unit/`)**:
  - Independent of external services.
  - Test pure transformation functions, regex parsers, checksum verifiers, and config loaders.
- **Integration Tests (`tests/integration/`)**:
  - Require the PostgreSQL container (`sl_grid_warehouse_test`).
  - Test connection pools, transaction rollbacks, SQL queries, and migrations.
- **Data Quality Tests (`tests/data_quality/`)**:
  - Test tabular datasets against domain rules (e.g. capacity limits, non-negative power, timestamp continuity).

## Verification Steps
1. Execute `pytest -v --cov=src` to check code coverage.
2. Confirm zero warnings or test failures.
3. Record the exact terminal execution log.
