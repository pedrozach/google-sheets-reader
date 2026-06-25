---
name: python-standards
description: Use when writing Python code, generating Python functions, or reviewing Python files.
---

# Python Standards

## Environment
- Python 3.11+
- Package manager: pip
- Virtual env: .venv in project root

## Style
- Follow PEP 8
- Use type hints on all function signatures
- Use f-strings, not .format() or %
- Prefer pathlib over os.path

## Testing
- Use pytest (not unittest)
- Fixtures in conftest.py
- File naming: test_*.py
- Parametrize when testing multiple inputs

## Imports
- stdlib → third-party → local (isort default)
- Absolute imports only
