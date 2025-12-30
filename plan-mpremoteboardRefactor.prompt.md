Plan: Unify Jupyter runner with MPRemoteBoard

Goal
- Refactor Jupyter-side command execution to reuse MPRemoteBoard/runner while keeping Jupyter-friendly streaming, parsing, and state handling.
The MPRemoteBoard is the most recent and complete code , but has diverged in implementation from the older IPyRemoteBoard and lacks support for Jupyter-specific features like streaming output to cells and populating SLists.

Steps
1) Centralize command construction
- Add a helper (e.g., build_cmd) to MPRemoteBoard to assemble mpremote invocations (connect/resume) from string or list input.
- Use it in both run_command (CLI path) and run_command_ipython (Jupyter path) to avoid diverging prefixes/resume handling.

2) Extract a shared executor
- Lift core process/timeout/log loop from runner.run into a reusable executor that accepts pluggable line handlers and tag sets.
- Preserve current defaults for CLI mode so existing behavior remains unchanged.

3) Rebuild ipython_run on top of the executor
- Provide Jupyter-specific tags (errors/warnings/reset + trace/meminfo filters), streaming, and SList population with hide_meminfo and follow controls.
- Keep store_output semantics for the IPython namespace.

4) Update IPyRemoteBoard.run_command_ipython
- Delegate to the shared executor with Jupyter handlers and auto-connect/resume flags, honoring timeout and follow semantics.
- Apply the same tenacity retries as CLI (or make retries configurable to avoid long waits in notebooks).

5) Unify tag definitions
- Consolidate tag presets in one module (CLI defaults + Jupyter extras) so both runners pull from the same source without duplicating constants.

Open question
- Should Jupyter execution default to the same retry policy as CLI, or be opt-in to keep notebooks responsive?
