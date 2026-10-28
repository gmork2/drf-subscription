# drf-subscription

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![CI](https://github.com/gmork2/drf-subscription/actions/workflows/ci.yml/badge.svg)](https://github.com/gmork2/drf-subscription/actions/workflows/ci.yml)

A generic subscription app for django.

## Installation

Dependencies are managed exclusively with [uv](https://docs.astral.sh/uv/):

```sh
uv sync
```

## REST API

The app ships a DRF router exposing these endpoints (admin-only by default):

- `/api/subscriptions/`
- `/api/subscription-lines/`
- `/api/subscription-events/`
- `/api/resources/`

## Versioning

This project follows [Semantic Versioning](https://semver.org/). The version is
kept in `subscription/__init__.py` (`__version__`) and read by `pyproject.toml`.
To bump it:

```sh
uv run python scripts/bump_version.py patch            # or minor / major
uv run python scripts/bump_version.py patch --tag      # and create the git tag vX.Y.Z
```

## Release

Publishing to PyPI is automatic: when a version change in `subscription/__init__.py`
is pushed to the default branch, GitHub Actions builds and publishes it to PyPI
(via trusted publishing).

You can trigger a release in two ways:

1. **From GitHub** — go to **Actions → Bump version → Run workflow** and choose
   `patch`, `minor` or `major`. It bumps the version, commits, tags, pushes and
   publishes.
2. **Locally** — bump and push; publication happens automatically:

```sh
uv run python scripts/bump_version.py patch --commit --tag --push
```
