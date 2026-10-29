---
trigger: always_on
description: Test-Driven Development (TDD) enforcement, test suites, and execution verification
---
# Testing Rules & TDD Protocol

## Test-Driven Development (TDD)
1. **Red → Green → Refactor**:
   - Write a failing test first that specifies the contract or behavioral expectation.
   - Run the test suite and confirm the failure with exact failure messages.
   - Write the minimal production code necessary to pass the test.
   - Run the test suite and confirm it passes.
   - Refactor code and tests to maintain clean, idiomatic architecture while ensuring tests stay green.

## Honest Execution Evidence
- **Never claim a test passed without running it**.
- Always execute the actual test command (e.g. `pytest tests/unit/...`) and present the terminal output.
- If a test fails, clearly explain why it failed, what root cause was identified, and the exact corrective action taken.
- Do NOT write placeholder tests with `pass` or `assert True`. Tests must make meaningful assertions on data transformations, boundary conditions, and database constraints.

## Test Categorization & Isolation
- **Unit Tests (`tests/unit/`)**:
  - Offline, in-memory, ultra-fast.
  - Zero external network dependencies.
  - Test parser logic, date parsing, unit conversion, schema validation, and config loading.
- **Integration Tests (`tests/integration/`)**:
  - Test live interactions with PostgreSQL running in Docker.
  - Test database connection pools, migration execution, transactional rollbacks, and warehouse inserts.
- **Data Quality Tests (`tests/data_quality/`)**:
  - Test assertions against raw fixtures and transformed data frames.
  - Verify null rates, range bounds, foreign key completeness, and outlier filters.
- **Test Fixtures (`tests/fixtures/`)**:
  - Small, synthetic, representative test files (CSV, XLSX, JSON) used exclusively for automated test discovery and CI reproducibility.
