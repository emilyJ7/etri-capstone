# Engineering Rules

- Do not use subagents for code reading, searching, or implementation unless the user explicitly requests them.
- Read relevant files in full before explaining or changing their behavior.
- Follow imports, calls, data transformations, and consumers before making factual claims.
- Separate verified facts, assumptions, and unknowns.
- Prefer the smallest change that satisfies the verified requirement.
- Do not add abstractions or edge-case handling without demonstrated present value.
- Write code whose intent is clear from its names, structure, and types.
- Use readable formatting instead of dense one-line implementations.
- Reuse established project patterns before introducing parallel implementations.
- Keep responsibilities separated and avoid duplicated rules that can drift.
- Never commit secrets, credentials, access tokens, or personal data.
- Preserve unrelated user changes.
- Never run destructive Git commands without explicit approval.
- Do not add `Co-Authored-By` lines to commits.
- Do not create or run automated tests unless the user explicitly requests them.
- Static checks, compilation, linting, formatting, diff checks, and schema validation remain allowed.
- Report completion only after verifying the implemented behavior or clearly stating what remains unverified.
