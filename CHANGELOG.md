# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Official support for Python 3.13, 3.14 and 3.15 (CI test matrix now covers
  3.12, 3.13, 3.14 and 3.15).
- Django 6.0 and 6.1 support.

### Changed
- Widened Django dependency range to `>=5.2,<7` (Django 6.x is required for
  Python 3.14/3.15 support).
- Raised djangorestframework floor to 3.18, the first release supporting
  Django 6.x and Python 3.15.

### Fixed
- Test fixtures now reference content types by natural key instead of
  hard-coded primary keys, which broke on Django 6.x.

## [0.1.3] - 2026-10-28

## [0.1.2] - 2026-10-28

## [0.1.1] - 2026-10-28

### Added
- REST API router (admin-only) exposing subscriptions, lines, events and resources.
- Semantic Versioning via `scripts/bump_version.py`.
- Expanded test coverage (managers, signals, API views, resource model and integration).
