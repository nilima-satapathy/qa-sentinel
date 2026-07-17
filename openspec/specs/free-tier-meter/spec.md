# free-tier-meter Specification

## Purpose
TBD - created by archiving change realtime-chat-quality-gate. Update Purpose after archive.
## Requirements
### Requirement: Track free-tier usage from this app
The system SHALL track token and/or request usage for cloud model calls made by this application (chat and optional judge).

#### Scenario: Usage increments after chat call
- **WHEN** a successful cloud chat completion returns token usage
- **THEN** the tracked daily usage increases by those tokens (or by one request if tokens are missing)

### Requirement: Display remaining free budget
The system SHALL display remaining free-tier budget for the current day in the UI.

#### Scenario: Sidebar meter
- **WHEN** the user views the chat UI
- **THEN** a free-tier meter shows remaining vs configured daily limit
- **AND** the meter uses configurable defaults suitable for free tiers (e.g. Groq)

### Requirement: Low budget warning
The system SHALL warn the user when free-tier budget is nearly exhausted.

#### Scenario: Below 10% remaining
- **WHEN** remaining free tokens fall below 10% of the daily limit
- **THEN** the UI shows a low-budget warning
- **AND** recommends disabling the AI judge or using golden offline mode

