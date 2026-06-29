# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-29

First release of `the-primer` as a standalone implementation built on the
[`capillary-actions-sdk`](https://github.com/Allogy/capillary-actions-sdk).

### Changed

- **BREAKING:** Repackaged as `the-primer` (module `the_primer`). The project no
  longer vendors the SDK source under `capillary_actions_sdk`; it now declares
  `capillary-actions-sdk` as an external dependency and imports from it.
- Pedagogy models live in `the_primer.models` and **extend** the SDK's
  learner-interaction models (`KnowledgeConcept`, `KnowledgeGraph`,
  `LearnerProgress`) rather than modifying them in place.
- Engine imports updated to `the_primer.{enums,models,utils,loader,tutor,session_runner}`.
- Fixed `main.py` import (`the_primer.loader` — was a non-existent `yaml_loader`).

### Added

- YAML-driven tutoring engine: `loader`, `TutoringAgent`, `MasteryGate`, `SessionRunner`.
- Pedagogy enums: `BloomLevel`, `AssessmentModality`, `GateDecision`.
- Mastery/assessment models: `ConceptMasteryRecord`, `RubricScore`,
  `AssessmentResult`, `MasteryGateDecision`.
- Abstract-algebra example knowledge graph and Bloom/modality policies.

### Removed

- Vendored copy of the SDK (`src/capillary_actions_sdk/**`), its tests, and its
  architecture docs — these are owned by the `capillary-actions-sdk` repo.
