# llm zoomcamp 2026 code

A uv workspace: each module folder declares its own dependencies in its `pyproject.toml`, sharing one `uv.lock` and `.venv` at the root. Run `uv sync` at the root to install everything; add a dependency to a module with `uv add --package <module-name> <dep>`.

Run notebooks in VS Code directly, otherwise run `uv run jupyter notebook`.
