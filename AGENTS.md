# Antigravity Agent Governance — National Electricity Grid Analytics Data Warehouse

## Project Overview
This project is an academic group data warehouse engineering project for the **National Electricity Grid Analytics Data Warehouse — Sri Lanka** developed by a team of six undergraduate software engineers. The warehouse models and analyzes historical generation, dispatch, capacity, consumption, and solar/meteorological data.

## Fundamental Principles
1. **Never Proceed to New Phases Without Explicit User Approval**:
   - Current phase is **Phase 0 (Foundation)**.
   - Do NOT implement warehouse fact or dimension tables in Phase 0.
   - Do NOT implement web frontend applications.
2. **Read Architecture & Docs Before Writing Code**:
   - Always consult [system-overview.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/architecture/system-overview.md), [implementation-plan.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/implementation-plan.md), and [test-strategy.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/testing/test-strategy.md).
3. **Plan Changes First**:
   - Provide a concise plan before performing non-trivial modifications.
4. **Test-Driven Development (TDD)**:
   - Write failing automated tests (Red) before writing implementation code (Green), then refactor.
5. **Database Schema Controlled Exclusively via Migrations**:
   - Never run raw ad-hoc DDL directly on production or development databases.
   - Never modify an existing applied migration file. Always create a new sequential forward migration.
6. **Data Integrity & Domain Physics**:
   - **Never fabricate** electricity measurements, demand data, or citations.
   - **Never mix units**: Active power (MW) is instantaneous demand/rate; energy output is MWh or GWh ($1\text{ GWh} = 1{,}000\text{ MWh}$).
   - **Never treat missing measurements as zero** ($0\text{ MW}$ is a shutdown/blackout; missing data is `NULL`/unknown).
   - **Preserve provenance**: Original raw files must remain immutable with SHA-256 hashes recorded.
   - **Preserve time zones**: Sri Lanka Standard Time is UTC+05:30. Always record timezone-aware timestamps.
7. **Security & Secrets**:
   - Never commit passwords, tokens, API keys, or credentials to Git. Use environment variables and `.env.example`.
8. **Verification Evidence**:
   - Never claim tests passed without executing them and presenting actual CLI output.
   - Explain all test failures and corrective actions taken.

## Modular Rules Reference
All agents must adhere to the rules in `.agents/rules/`:
- [architecture.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/architecture.md)
- [postgresql.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/postgresql.md)
- [data-engineering.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/data-engineering.md)
- [data-quality.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/data-quality.md)
- [testing.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/testing.md)
- [security.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/security.md)
- [git-workflow.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/git-workflow.md)
- [documentation.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/documentation.md)
