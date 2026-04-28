# Repository Policy

## No Runtime Artifacts

Runtime and generated files must never be committed into git history.

Blocked categories:

- credential exports (`created_teacher_accounts_*.csv`, `teacher_credentials_store.csv`);
- runtime uploads (`media/`);
- local logs and temp files (`*.log`, `*.tmp`, `~$*.docx`);
- ad-hoc office/text exports in repository root (`*.csv`, `*.doc`, `*.docx`).

Enforcement:

- pre-commit hook `no-runtime-artifacts` runs `scripts/check_runtime_artifacts.py`;
- CI also runs `python scripts/check_runtime_artifacts.py --all`.

If a runtime artifact was already committed, remove it from HEAD and then rewrite history with `git filter-repo` before public release.
