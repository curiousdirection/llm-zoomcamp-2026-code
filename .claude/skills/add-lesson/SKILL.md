---
name: add-lesson
description: Add a course lesson to its module's lesson notebook (<module>/lesson/lesson.ipynb) - copies the lesson's markdown verbatim with python blocks as unrun code cells, scaffolds the module folder on first use, and checks the lesson's helper files and imports. Use when the user asks to add/prep/start a lesson, given a llm-zoomcamp GitHub URL like .../04-evaluation/02-ground-truth.md or a lesson number.
---

# Add a lesson to the lesson notebook

Lessons only. Never use this for homework (see CLAUDE.md: no hints for homework).

## 1. Resolve the lesson

- From a URL `https://github.com/DataTalksClub/llm-zoomcamp/blob/main/<module>/<NN>-<slug>.md`,
  take `<module>` and `<NN>`. Given only a number, use the module currently being worked on.
- Read the **local** copy at `course/<module>/<NN>-<slug>.md` (a git subtree of the course repo),
  don't fetch it. If it's missing, the subtree is probably stale: suggest the
  `git subtree pull` command from README.md and ask before running it.
- Lesson numbers aren't always contiguous (module 4: 01-06, then 11-15). `course/<module>/module.yaml`
  is the source of truth.

## 2. Scaffold the module (first lesson of a module only)

Skip if `<module>/` exists. Otherwise mirror `02-vector-search` / `04-evaluation`:

- `<module>/pyproject.toml` with `name` = module folder minus the number prefix
  (`04-evaluation` -> `evaluation`), `version = "0.1.0"`, `requires-python = ">=3.12"`, `dependencies = []`.
- Add `<module>` to `members` in the root `pyproject.toml` `[tool.uv.workspace]`.
- Add the deps from `course/<module>/code/pyproject.toml` with
  `uv add --package <name> <deps...>`. Leave out `jupyter`: the root dev group provides it.
- Copy `ingest.py` and `rag_helper.py` from the most recent module's `lesson/` folder. These are
  our versions, and they differ from the course's (e.g. `rag_helper.py` defaults to `gpt-6-luna`).

## 3. Append the lesson

From the repo root:

```bash
python3 .claude/skills/add-lesson/build_notebook.py <module> <NN> [<NN> ...]
```

It creates the notebook with the module header cell if needed, and skips lessons already present.
Do a dry run with `--notebook /tmp/x.ipynb` if unsure. Never hand-edit the copied text: keep it
verbatim, including the course's model names in code (e.g. `gpt-5.4-mini`).

## 4. Check what the lesson needs

Read the lesson's python blocks and any `wget`/download instructions, then:

- Make sure every local module it imports (`ingest`, `rag_helper`, `evaluation_utils`, ...) is in
  `<module>/lesson/`, and that third-party imports resolve:
  `cd <module>/lesson && uv run python -c "import ..."`.
- For a missing helper, first check for a copy in `course/<module>/code/` or an earlier module's
  `lesson/`. To download one, **ask first**. Then download into a fresh `mktemp -d`, diff it
  against the `course/` copy, read it, and only then move it into `lesson/`.
  Known issue: the lessons' `cohorts/2026/<module>/code/...` URLs return 404; the files are at
  `https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/main/<module>/code/<file>`.
- Point out mismatches the user will hit, e.g. helpers that default to a different model than ours,
  or hardcoded prices (`calc_price`) that only fit the course's model.

## 5. Report

Say how many cells were added (and how many are code), what was scaffolded or copied, and what
is still missing. Don't run the notebook cells (the user runs them) and don't commit.
