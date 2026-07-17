# live-chat Specification

## Purpose
TBD - created by archiving change realtime-chat-quality-gate. Update Purpose after archive.
## Requirements
### Requirement: Realtime chat completion
The system SHALL accept a user question and return an assistant answer in a realtime chat UI without requiring a batch eval job.

#### Scenario: Successful free-tier completion
- **WHEN** the user submits a non-empty question and a valid free-tier API key is configured
- **THEN** the system calls an OpenAI-compatible chat endpoint
- **AND** displays the assistant answer in the conversation
- **AND** records latency and token usage when provided by the API

#### Scenario: Empty question rejected
- **WHEN** the user submits an empty or whitespace-only question
- **THEN** the system does not call the model
- **AND** prompts the user to enter a question

### Requirement: Software-testing assistant persona
The system SHALL use a system prompt that frames the assistant as a software testing / QA helper (not a general unrestricted agent).

#### Scenario: Domain persona applied
- **WHEN** a chat completion is requested
- **THEN** the request includes the software-testing assistant system prompt

### Requirement: Offline fallback without API key
The system SHALL support a demo path without cloud API keys.

#### Scenario: Golden match offline
- **WHEN** no API key is configured and the user question exactly matches a golden-set question
- **THEN** the system returns the golden reference answer
- **AND** labels the backend as golden (or equivalent)

#### Scenario: No key and no golden match
- **WHEN** no API key is configured and the question does not match a golden case
- **THEN** the system does not invent a live model answer
- **AND** shows guidance to configure a free-tier key or use a golden example question

### Requirement: Configurable free-tier provider
The system SHALL allow configuration of OpenAI-compatible base URL, API key, and model via environment variables.

#### Scenario: Groq free tier configuration
- **WHEN** `OPENAI_BASE_URL` points to Groq’s OpenAI-compatible API and a valid key and model are set
- **THEN** chat completions use that configuration

