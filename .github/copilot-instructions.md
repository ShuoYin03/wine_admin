

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
