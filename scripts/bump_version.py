#!/usr/bin/env python3
"""Bump the project version following Semantic Versioning (semver.org).

Usage:
    uv run python scripts/bump_version.py <major|minor|patch> [--dry-run] [--commit] [--tag] [--push]
"""
import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = ROOT / "subscription" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"

VERSION_RE = re.compile(
    r'^__version__\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']',
    re.MULTILINE,
)


def read_current_version():
    text = INIT_FILE.read_text()
    match = VERSION_RE.search(text)
    if not match:
        sys.exit(f"Could not find __version__ in {INIT_FILE}")
    return tuple(int(part) for part in match.groups()), text


def compute_bump(major, minor, patch, part):
    if part == "major":
        return major + 1, 0, 0
    if part == "minor":
        return major, minor + 1, 0
    if part == "patch":
        return major, minor, patch + 1
    raise ValueError(f"Unknown part: {part}")


def update_changelog(new_version):
    if not CHANGELOG.exists():
        return
    content = CHANGELOG.read_text()
    unreleased = "## [Unreleased]"
    if unreleased not in content:
        return
    today = date.today().isoformat()
    content = content.replace(
        unreleased,
        f"{unreleased}\n\n## [{new_version}] - {today}",
        1,
    )
    CHANGELOG.write_text(content)


def commit_files(new_version):
    paths = [str(INIT_FILE)]
    if CHANGELOG.exists():
        paths.append(str(CHANGELOG))
    subprocess.run(["git", "add", *paths], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"chore(release): bump to v{new_version}"],
        check=True,
    )
    print(f"Committed version {new_version}")


def create_tag(new_version):
    tag = f"v{new_version}"
    subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], check=True)
    print(f"Created git tag {tag}")


def push():
    subprocess.run(["git", "push"], check=True)
    subprocess.run(["git", "push", "--tags"], check=True)
    print("Pushed commits and tags")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Bump the project version following Semantic Versioning."
    )
    parser.add_argument("part", choices=("major", "minor", "patch"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the new version without writing any files.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit the bumped files to git.",
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create an annotated git tag (vX.Y.Z) for the new version.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push commits and tags to the remote.",
    )
    args = parser.parse_args(argv)

    current, text = read_current_version()
    new_version = ".".join(str(part) for part in compute_bump(*current, args.part))

    if args.dry_run:
        print(f"Would bump {'.'.join(map(str, current))} -> {new_version}")
        return

    INIT_FILE.write_text(
        VERSION_RE.sub(f'__version__ = "{new_version}"', text, count=1)
    )
    update_changelog(new_version)
    print(f"Bumped {'.'.join(map(str, current))} -> {new_version}")

    if args.commit:
        commit_files(new_version)

    if args.tag:
        create_tag(new_version)

    if args.push:
        push()


if __name__ == "__main__":
    main()
