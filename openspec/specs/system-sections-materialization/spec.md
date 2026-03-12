# system-sections-materialization Specification

## Purpose
TBD - created by archiving change phase-4-g1-g3-async-closure. Update Purpose after archive.
## Requirements
### Requirement: System sections are materialized during system creation
The system SHALL create section records in the `system_sections` table when a new system is created, based on the project's thesis schema.

#### Scenario: Sections created from thesis schema outline
- **WHEN** a new system is created and the project has `thesis_schema_json.outline` defined
- **THEN** system SHALL create section records matching the outline structure with `section_key`, `title`, and `order_index`

#### Scenario: Sections created from thesis schema chapters
- **WHEN** a new system is created and the project has `thesis_schema_json.chapters` but no outline
- **THEN** system SHALL create section records derived from chapters array

#### Scenario: Sections created from default skeleton
- **WHEN** a new system is created and the project has neither outline nor chapters in thesis schema
- **THEN** system SHALL create 4 default section records: Introduction, Methods, Results, Discussion

### Requirement: Section materialization is idempotent
The system SHALL NOT create duplicate section records if sections already exist for a system.

#### Scenario: Sections already exist
- **WHEN** section materialization is triggered for a system that already has sections
- **THEN** system SHALL skip section creation and return existing sections

### Requirement: Section records contain required fields
Each materialized section record SHALL contain `system_id`, `section_key`, `title`, `order_index`, and audit fields.

#### Scenario: Section record structure
- **WHEN** a section is materialized
- **THEN** the record SHALL have non-null `system_id`, `section_key`, `title`, `order_index`, `created_at`, `updated_at`

