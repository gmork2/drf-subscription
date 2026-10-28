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

Releases are a two-step process handled by two GitHub Actions workflows:

1. **Bump version** (Actions → Bump version → Run workflow): choose `patch`,
   `minor` or `major`. It bumps the version, updates the changelog, commits,
   tags and pushes.
2. **Publish** (Actions → Publish → Run workflow): builds the package, publishes
   it to PyPI and creates the GitHub Release for the current version.

Alternatively, you can do it locally — bumping and pushing triggers the Publish
workflow automatically:

```sh
uv run python scripts/bump_version.py patch --commit --tag --push
```

## PyPI publishing setup

Publication uses **Trusted Publishing** (recommended) or an API token.

### Trusted Publishing (recommended)

1. On PyPI, go to your project → **Settings → Publishing**.
2. Click **Add a new trusted publisher** and fill in:
   - **Owner**: `gmork2`
   - **Repository**: `drf-subscription`
   - **Workflow name**: `publish.yml`
   - **Environment name**: leave blank
3. Save.

Only `publish.yml` publishes to PyPI, so a single trusted publisher is enough.

### API token (alternative)

Create an API token on PyPI and add it as a GitHub Actions secret named
`PYPI_TOKEN`. If set, it takes precedence over trusted publishing.
