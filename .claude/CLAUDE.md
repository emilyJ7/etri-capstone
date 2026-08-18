# Project Instructions

## Scope

- Read `README.md` in full before planning or editing.
- Treat `server.py` as a minimal MCP reference, not the final product scope.
- Keep work inside this repository unless the user explicitly expands the scope.

## Working Rules

- Do not use subagents for code reading, searching, or implementation unless the user explicitly requests them.
- Read relevant files in full before describing or changing their behavior.
- Follow delegated calls and data transformations before making factual claims.
- Prefer the smallest change that satisfies the verified requirement.
- Write intention-revealing names and readable, formatter-compliant code.
- Do not add `Co-Authored-By` lines to commits.
- Do not create or run automated tests unless the user explicitly requests them. Static checks, compilation, linting, and schema validation remain allowed.
- Preserve unrelated user changes and never use destructive Git commands without explicit approval.

## Architecture

- Use Python 3.10 or later.
- Use the official Python MCP SDK for protocol handling.
- Keep MCP transport, OpenAlex integration, domain logic, and SQLite persistence separated.
- Use OpenAlex as the scholarly-data source.
- Use SQLite for saved papers, reports, and their relationships.
- Let the LLM decide how to analyze and compare papers.
- Let the MCP Server retrieve, validate, store, and return data.
- Preserve OpenAlex IDs, DOIs, and source URLs with every saved paper and report.
- Keep Tool names, descriptions, inputs, and outputs explicit enough for an LLM to choose correctly.

## Data and Security

- Never commit API keys, credentials, access tokens, or personal data.
- Read `OPENALEX_API_KEY` from the execution environment when provided.
- Do not invent missing OpenAlex fields or silently replace failures with empty success values.
- Bound list results so Tool output does not unnecessarily consume model context.

## Completion

- Verify the MCP Server starts through `stdio`.
- Verify the MCP Host discovers every intended Tool.
- Verify saved papers and reports remain available after the Server restarts.
- Report verified facts separately from assumptions and unverified behavior.
