## ADDED Requirements

### Requirement: Persist chat turns with gate results
The system SHALL persist each completed turn including question, answer, gate status, scores, latency, tokens, and model.

#### Scenario: Turn saved after gate
- **WHEN** a turn completes with an answer and gate result
- **THEN** a record is written to local SQLite storage
- **AND** can be retrieved for the current session history

### Requirement: Session quality summary
The system SHALL expose a simple session-level summary of gate outcomes.

#### Scenario: Session pass count
- **WHEN** the user has completed one or more gated turns in the session
- **THEN** the UI shows how many turns passed vs total (e.g. 3/4 PASS)

### Requirement: Portfolio evidence export
The system SHALL allow exporting recent turns for portfolio evidence.

#### Scenario: CSV export available
- **WHEN** turn history exists
- **THEN** the user can export turns to CSV including gate status and scores
