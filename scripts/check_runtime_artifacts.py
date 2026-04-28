from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT_FILES = {
    ".env.example",
    ".gitignore",
    "README.md",
    "db.sqlite3",
    "gen_requirements.py",
    "icona-128.png",
    "icona-256.png",
    "icona-512.png",
    "icona-64.png",
    "icona.png",
    "icona.svg",
    "manage.py",
    "requirements.txt",
    "start.bat",
}
BLOCKED_EXTENSIONS = {".csv", ".log", ".tmp", ".bak", ".swp", ".doc", ".docx"}
BLOCKED_NAME_FRAGMENTS = (
    "created_teacher_accounts_",
    "teacher_credentials_store",
)
BLOCKED_PREFIXES = ("~$",)
BLOCKED_DIRECTORIES = (
    Path("media"),
    Path("logs"),
)


def _git_output(args: list[str]) -> list[str]:
    process = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        print(process.stderr.strip() or f"git {' '.join(args)} failed", file=sys.stderr)
        return []
    return [line.strip() for line in process.stdout.splitlines() if line.strip()]


def _collect_candidates(all_files: bool) -> list[Path]:
    if all_files:
        tracked = _git_output(["ls-files"])
        return [Path(p) for p in tracked]
    staged = _git_output(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    return [Path(p) for p in staged]


def _is_blocked(path: Path) -> str | None:
    path_str = path.as_posix().lower()
    name = path.name
    lower_name = name.lower()

    for blocked_dir in BLOCKED_DIRECTORIES:
        if path.parts[: len(blocked_dir.parts)] == blocked_dir.parts:
            return f"directory '{blocked_dir.as_posix()}/' is runtime-only"

    if name in ALLOWED_ROOT_FILES:
        return None

    if len(path.parts) == 1:
        if lower_name.startswith(BLOCKED_PREFIXES):
            return "temporary office file"
        if any(part in lower_name for part in BLOCKED_NAME_FRAGMENTS):
            return "generated credential/export artifact"
        if path.suffix.lower() in BLOCKED_EXTENSIONS:
            return f"blocked root extension '{path.suffix}'"

    if "created_teacher_accounts_" in path_str or "teacher_credentials_store" in path_str:
        return "generated credential/export artifact"

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Block runtime/export artifacts from repo.")
    parser.add_argument("--all", action="store_true", help="check all tracked files (for CI)")
    args = parser.parse_args()

    blocked: list[tuple[Path, str]] = []
    for candidate in _collect_candidates(all_files=args.all):
        reason = _is_blocked(candidate)
        if reason:
            blocked.append((candidate, reason))

    if not blocked:
        return 0

    print("Blocked runtime/export artifacts detected:")
    for path, reason in blocked:
        print(f" - {path.as_posix()}: {reason}")
    print("Move generated/runtime files out of repository root and media before commit.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
