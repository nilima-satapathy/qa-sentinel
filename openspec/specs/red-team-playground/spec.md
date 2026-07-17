# red-team-playground Specification

## Purpose
TBD - created by archiving change realtime-chat-quality-gate. Update Purpose after archive.
## Requirements
### Requirement: Attack example prompts
The system SHALL provide one-click example prompts derived from red-team / adversarial cases for demos.

#### Scenario: Inject red-team prompt
- **WHEN** the user clicks a red-team example in the UI
- **THEN** the corresponding adversarial question is submitted as a chat turn
- **AND** the resulting answer is quality-gated like any other turn

### Requirement: Safety demo narrative
The system SHALL support demonstrating both safe refusals and policy failures.

#### Scenario: Safe refusal can pass
- **WHEN** an adversarial prompt is asked and the model refuses appropriately
- **THEN** the gate MAY return PASS or WARN based on policy (refusal is not automatically FAIL)

#### Scenario: Unsafe compliance fails
- **WHEN** an adversarial prompt is asked and the model complies with disallowed content
- **THEN** the gate returns FAIL
- **AND** reasons cite the policy violation

