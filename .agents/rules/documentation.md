---
trigger: always_on
description: Documentation maintenance rules, requirements matrix tracking, and architecture synchronization
---
# Documentation Rules

## Living Documentation Requirements
1. **Synchronize Code and Documentation**:
   - Every architectural change, schema evolution, new data source integration, or pipeline addition must be documented immediately.
   - Never leave documentation updates as an afterthought.
2. **Standard Document Locations**:
   - `docs/architecture/`: System design, dimensional bus matrix, ETL flow diagrams.
   - `docs/assignment/`: Requirements tracking matrix, module mappings, deliverables.
   - `docs/data_sources/`: Source inventory, data dictionaries, profiling notes.
   - `docs/database/`: Schema data dictionaries, ER diagrams, migration changelogs.
   - `docs/testing/`: Test strategy, verification checklists, phase test reports.
   - `docs/team/`: Task allocations, member responsibilities, meeting decisions.
3. **Markdown Hyperlinking Standards**:
   - All internal code references, schemas, scripts, and documentation must use clickable file links: `[filename](file:///absolute/path/to/file)`.
   - Use forward slashes for all file links across platforms.
4. **Data Dictionary Completeness**:
   - Every column in every dimension and fact table must have an explicit description, data type, nullability, unit of measure (if numeric), and source lineage.
