# TESTING

Behavior audit and regression checklist. Run each in a real `freeai` session.
Record actual tokens next to expected. Any command that should cost zero but
does not is a bug in the Day 26 / Day 31 category: it is not routed before the
planner. Fix with its own numbered day (symptom, root cause, fix, test).

For every zero-token command confirm three things:

1. Present in `commands.get_available_commands()`.
2. Intercepted in `main.task_loop` before `planner.generate_plan` runs
   (via `_run_builtin`, `_FREETEXT`, `_SWITCH`, `_ASSIST`, or the `index` guard).
3. Token dashboard shows zero.

## Commands (expected: 0 tokens)

| Command | Expected | Actual |
|---------|----------|--------|
| `model list` | 0 | |
| `model pull <name>` | 0 (download, no model tokens) | |
| `model use <name>` | 0 | |
| `model remove <name>` | 0 | |
| `config` | 0 | |
| `config --assistance <level>` | 0 | |
| `mode low\|full\|ultra` | 0 | |
| `assistance <level>` | 0 | |
| `history` | 0 | |
| `clear` | 0 | |
| `index` | embed cost only, 0 chat | |
| `done` | 0 | |
| `help` | 0 | |
| `switch model to <name>` | 0 | |
| skill invoke (e.g. `personal`) | 0 | |

## Free-text routing (expected: 0 tokens)

Same request phrased as plain text must route zero-token, not reach planner.

| Input | Routes to | Expected | Actual |
|-------|-----------|----------|--------|
| `list models` | `model list` | 0 | |
| `show models` | `model list` | 0 | |
| `models` | `model list` | 0 | |
| `show history` | `history` | 0 | |
| `clear` | `clear` | 0 | |
| `help` | `help` | 0 | |

## Destructive confirmation still fires

| Action | Expect prompt |
|--------|---------------|
| `run_command rm ...` | yes, DESTRUCTIVE | |
| `run_command dd ...` | yes | |
| `write_file` over existing | yes, diff shown | |
| `delete_file` | yes | |
| `git_push` | yes, remote + branch shown | |

## Inverse case (must reach planner)

Genuine free-text coding task must NOT over-match into routing. Confirm it
reaches `generate_plan` and spends tokens.

| Input | Expected |
|-------|----------|
| `add a --verbose flag to the cli` | plan generated, tokens > 0 |
| `refactor rag.py chunking` | plan generated, tokens > 0 |

## Plan quality (Day 33c + Day 34)

- `list models` as free text costs zero tokens.
- Real multi-file task plan never exceeds four steps.
- No step is a generic process phase (identify requirements, analyze codebase,
  review, test, push as standalone).
- Every step line under six words, no article, not capitalized as a full
  sentence, no trailing period.
- Final step is `verify and commit` (review, test, push merged).
