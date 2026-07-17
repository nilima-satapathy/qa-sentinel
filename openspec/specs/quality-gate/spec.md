# quality-gate Specification

## Purpose
TBD - created by archiving change realtime-chat-quality-gate. Update Purpose after archive.
## Requirements
### Requirement: Per-answer quality evaluation
The system SHALL run a quality gate on every assistant answer before the turn is considered complete.

#### Scenario: Gate runs after model answer
- **WHEN** the chat SUT returns an answer for a user question
- **THEN** the quality gate evaluates that answer
- **AND** produces a status of PASS, WARN, or FAIL
- **AND** produces one or more human-readable reasons

### Requirement: Offline policy layer (L1)
The system SHALL always apply free offline policy checks to every answer.

#### Scenario: Critical policy failure
- **WHEN** an answer violates a critical safety/policy rule (e.g. providing malware instructions, fabricating production secrets)
- **THEN** the gate status is FAIL
- **AND** reasons identify the policy category

#### Scenario: Answer too short
- **WHEN** an answer is empty or shorter than the configured minimum length
- **THEN** the gate status is FAIL or WARN per policy
- **AND** a reason indicates insufficient content

### Requirement: Golden match layer (L2)
The system SHALL apply golden-set metrics when the user question matches a golden case.

#### Scenario: Matched golden question
- **WHEN** the user question matches a golden dataset case
- **THEN** the gate computes must_include and reference_overlap scores
- **AND** compares them to configured live thresholds
- **AND** includes those scores in the gate result

#### Scenario: Unmatched free-form question
- **WHEN** the user question does not match a golden case
- **THEN** L2 golden metrics are skipped or marked not applicable
- **AND** L1 (and optional L3) still run

### Requirement: Optional AI-as-judge layer (L3)
The system SHALL support an optional free-tier LLM-as-judge evaluation that can be toggled by the user.

#### Scenario: Judge disabled
- **WHEN** the AI judge toggle is off
- **THEN** no judge model call is made
- **AND** the gate still returns a status from offline layers

#### Scenario: Judge enabled
- **WHEN** the AI judge toggle is on and a free-tier API is available
- **THEN** the system makes a second model call with a fixed judge prompt
- **AND** parses a structured score and reasons
- **AND** merges the judge outcome into the aggregate gate status

### Requirement: Transparent presentation
The system SHALL display the assistant answer together with the gate outcome (not hide the answer solely because of FAIL, except optional redaction for critical safety content if configured).

#### Scenario: Failed gate still shows answer with badge
- **WHEN** the gate status is FAIL for a non-critical redaction case
- **THEN** the UI still shows the answer
- **AND** shows a FAIL badge and reasons

