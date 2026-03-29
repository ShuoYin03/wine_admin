# Copilot Instructions

## Response Instructions
- Always use Chinese for responses and always use English for code.

## Coding Instructions

### TypeScript
- Always use TypeScript strict mode (`"strict": true` in tsconfig). This is already configured.
- Every function must have explicit return type annotations.
- Never use `any` — use `unknown` for truly unknown data and narrow with type guards.
- Always type API response shapes with explicit `type` or `interface`.
- Prefer `type` for plain data shapes, `interface` for extensible contracts.

### Python
- Always add full type annotations to every function signature (parameters and return type).
- Use `from __future__ import annotations` at the top of files for forward references.
- Use `X | None` union syntax (Python 3.10+) over `Optional[X]`.
- Use `list[X]`, `dict[K, V]`, `tuple[X, Y]` built-in generics (Python 3.9+) over `typing.List`, `typing.Dict`, etc.
- Run `mypy --strict` to enforce type checking. There should be no mypy errors in committed code.
- Pydantic models must always declare field types explicitly — no bare `= None` without a type.

### General
- No implicit `any` in TypeScript, no missing type annotations in Python.
- When adding new functions or methods, always include types before committing.
- **No backward-compat shims**: Frontend and backend share a single contract. Never write conversion/normalization helpers that translate old formats to new ones. Fix the source (the sender) instead. If a format is standardized, enforce it at the origin.

## Development Instructions
- For new features, write unit tests covering typical cases, edge cases, and error cases.
- For bug fixes, add a test that reproduces the bug before fixing it, then verify the test passes after the fix.
- Use descriptive test names that explain what the test is verifying.
- When modifying existing code, ensure all existing tests still pass and add new tests if the behavior changes.
- Run linters and formatters (e.g., ESLint, Prettier for TypeScript; Black, Flake8 for Python) before committing code.
- For API routes, include tests for both successful responses and expected error conditions (e.g., invalid input, server errors).
- Remember to use virtual environments for Python dependencies and to keep `requirements.txt` or `Pipfile` updated with any new packages.
