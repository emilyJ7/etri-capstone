---
name: code-review
description: Review current changes and report only verified problems that require correction. Use when the user invokes /code-review or asks whether code changes are correct, safe, and maintainable.
---

# Code Review

Review engineering decisions strictly, but report only actionable defects supported by the implementation.

## Boundary

- Review only. Do not edit, commit, push, or deploy.
- Do not run automated tests unless the user explicitly asks.
- Do not manufacture findings or include optional improvements.
- Do not report praise, summaries, or style preferences.
- If no correction is required, report `수정이 필요한 문제 없음.`

## Evidence

1. Read the applicable `CLAUDE.md`, README, specification, and changed files in full.
2. Compare the change with the current default branch and neighboring implementation.
3. Follow calls, transformations, persistence, and error paths until behavior is verified.
4. Mark unverified behavior as unknown; do not turn it into a finding.

## Review Criteria

### Correctness and contracts

- End-to-end behavior matches the stated requirements and public contracts.
- Inputs, outputs, serialization, persistence, and consumers remain consistent.
- Null, optional, state, and error paths preserve the intended meaning.
- Error paths do not become false success, empty data, or misleading fallback results.

### Security and data integrity

- Authentication and authorization are enforced at the actual read and mutation boundaries.
- Secrets, credentials, and unrelated user data are not committed or exposed.
- Updates do not cause silent data loss, duplicate execution, or unintended cross-user access.

### Architecture and maintainability

- UI, domain logic, transport, persistence, and external integrations have clear ownership.
- Shared validation and transformation rules are not duplicated in ways that can drift.
- Added abstraction has a demonstrated current use and does not expand the task without value.
- Names, structure, comments, and documentation match the executed behavior.

## Findings

For each retained finding, provide only:

- Severity: blocking, major, or minor
- Smallest responsible location
- Verified mechanism
- Concrete impact
- Required outcome

Order findings by severity. Do not include a finding unless the causal path and impact are both concrete.
