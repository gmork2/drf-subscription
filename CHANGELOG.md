# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-03

### Added
- Official support for Python 3.13, 3.14 and 3.15 (CI test matrix now covers
  3.12, 3.13, 3.14 and 3.15).
- Django 6.0 and 6.1 support.
- RFC 5545 recurrence rules powered by `python-dateutil` on
  `SubscriptionEvent` (`frequency`, `interval`, `count`, `until`,
  `by_month_day`, `by_week_day`), with deterministic non-mutating
  `occurrences()` and O(log n) `current`.
- `ResourceExecution` audit model and execution engine
  (`subscription.tasks`): Celery task with automatic retry,
  `subscription_dispatch` management command, and idempotent dispatch
  (one successful run per occurrence).
- Signed webhooks on resources (`webhook_url`, `webhook_secret`,
  `webhook_headers`, HMAC-SHA256 signature, host allowlist).
- REST API: filters, pagination, `run`/`pause`/`resume`/`history`
  actions on resources, and configurable permissions via
  `SUBSCRIPTION_PERMISSION_CLASSES`.
- Migrations for all models (data migration converts legacy
  `recurrence` values and `content_object_fields` literals).

### Changed
- Widened Django dependency range to `>=5.2,<7` (Django 6.x is required for
  Python 3.14/3.15 support).
- Raised djangorestframework floor to 3.18, the first release supporting
  Django 6.x and Python 3.15.
- `content_object_fields` is now a JSONField (was TextField with
  Python literals).
- `GenericSerializer.from_model` no longer mutates shared class state.
- Signal wiring moved from middleware to `AppConfig` + `post_migrate`
  with `dispatch_uid`; `SubscriberMiddleware` removed.
- `SubscriptionEvent.unique_together` replaced by `UniqueConstraint`.
- `SubscriptionEventQuerySet.current` compares full datetimes.

### Fixed
- Test fixtures now reference content types by natural key instead of
  hard-coded primary keys, which broke on Django 6.x.

### Deprecated
- `SubscriptionEvent.events` (use `occurrences()`).
- The legacy `recurrence` DurationField (removed; use the rule fields).

### Removed
- `subscription.middleware.SubscriberMiddleware`.

## [0.1.3] - 2026-10-28

## [0.1.2] - 2026-10-28

## [0.1.1] - 2026-10-28

### Added
- REST API router (admin-only) exposing subscriptions, lines, events and resources.
- Semantic Versioning via `scripts/bump_version.py`.
- Expanded test coverage (managers, signals, API views, resource model and integration).
