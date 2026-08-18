---
name: interview
description: Clarify a requested MCP feature one question at a time and produce a self-contained project specification. Use when the user asks to define requirements, resolve ambiguity, plan a new Tool, or run /interview before implementation.
---

# Interview

Turn a vague feature request into a specification another LLM can implement without the conversation.

## Boundary

- Interview only. Do not edit code, create files, or begin implementation.
- Ask in the requester's language.
- Ask exactly one question per turn.
- Do not ask for facts available in the repository; inspect them directly.
- Stop when the requester confirms the specification.

## Questions

Resolve the highest-impact ambiguity first. Complete these fields:

1. Goal and user outcome
2. Intended user and research workflow
3. Tool responsibilities and boundaries
4. OpenAlex inputs and required outputs
5. SQLite data that must persist
6. Explicit non-goals
7. Observable completion criteria
8. Quality level and constraints
9. Assumptions and open risks

Present concrete options with one recommendation when the answer space is finite. Do not ask a question whose answer would not change the implementation.

## Specification

After confirmation, produce a self-contained `SPEC.md` draft with:

- Context
- Goal
- Non-goals
- User flow
- Functional requirements
- Tool contracts
- Persistence requirements
- Error behavior
- Completion criteria
- Constraints
- Assumptions
- Open risks

Show the draft in chat for approval before writing it into the repository. End after the confirmed specification; implementation is a separate task.
