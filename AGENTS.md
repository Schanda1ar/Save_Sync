# Repository Guidelines

## Project Structure & Module Organization
Application code lives under [`src`](C:\Projects\Save_sync\Save_Sync\src). Keep backend Python modules in [`src/backend`](C:\Projects\Save_sync\Save_Sync\src\backend) and QML files in [`src/qml`](C:\Projects\Save_sync\Save_Sync\src\qml). The entrypoint in [`main.py`](C:\Projects\Save_sync\Save_Sync\main.py) should stay thin and only bootstrap the Qt app and backend controller. Tests live in [`tests`](C:\Projects\Save_sync\Save_Sync\tests). Packaging stays in [`Savesync.spec`](C:\Projects\Save_sync\Save_Sync\Savesync.spec), and requirements/scope are documented in [`Anforderungs.md`](C:\Projects\Save_sync\Save_Sync\Anforderungs.md).

Do not introduce a second top-level source tree such as `source/` or a parallel Python package root. New code belongs in the matching area under `src`, for example `src/backend/storage.py` or `src/qml/Main.qml`.

## Build, Test, and Development Commands
- `uv sync`: install project dependencies from `pyproject.toml` / `uv.lock`.
- `uv run python main.py`: run the current launcher locally.
- `uv lock`: refresh the lockfile after dependency changes.
- `pyinstaller Savesync.spec`: build the Windows executable defined by the spec file.

Run commands from the repository root: `C:\Projects\Save_sync\Save_Sync`.

## Coding Style & Naming Conventions
Use Python 3.14 with 4-space indentation and UTF-8 files. Follow standard Python naming:
- `snake_case` for functions, variables, and module names
- `UPPER_SNAKE_CASE` for constants
- `PascalCase` for classes

Keep functions small and move external-service logic behind helper functions or service classes. Prefer `pathlib.Path` over raw string paths. Avoid hardcoding secrets, tokens, or user-specific paths in source files. Put backend logic in `src/backend`; keep QML-only concerns in `src/qml`.

## Testing Guidelines
Use `pytest`, with files named `tests/test_<feature>.py`. Focus first on config parsing, JSON import/export, hash comparison, and OAuth fallback behavior. Run tests with `uv run --group dev python -m pytest`.

## Commit & Pull Request Guidelines
The current history starts with a simple `initial commit`, so use short, imperative commit messages such as `Add JSON profile export` or `Refactor Google Drive auth flow`. Keep changes scoped to one concern per commit.

Pull requests should include:
- a short summary of the change
- notes on config or credential impacts
- manual test steps
- screenshots for UI changes

## Security & Configuration Tips
Do not commit `config.ini`, OAuth credentials, tokens, or `client_secrets.json`. The existing `.gitignore` already excludes `*.ini` and secret-like files; keep it updated if new config or export paths are introduced.
