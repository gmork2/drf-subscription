# drf-subscription

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![CI](https://github.com/gmork2/drf-subscription/actions/workflows/ci.yml/badge.svg)](https://github.com/gmork2/drf-subscription/actions/workflows/ci.yml)

A generic subscription app for django.

## Features

- **Recurrence** — RFC 5545 recurrence rules powered by
  [python-dateutil](https://dateutil.readthedocs.io/) `rrule`
  (daily, weekly, monthly, yearly, intervals, counts, until, month/week
  day filters) with deterministic, non-mutating `occurrences()`.
- **Generic relations** — subscribe any model, attach resources to any
  model, snapshots stored as JSON.
- **Execution engine** — run callbacks and/or signed webhooks when an
  occurrence is active: signal accelerator plus a periodic dispatch
  (`subscription_dispatch` management command or Celery beat), with
  retries and full audit records (`ResourceExecution`).
- **Webhooks** — signed HMAC-SHA256 POSTs with configurable headers,
  timeout and host allowlist.
- **REST API** — CRUD endpoints, filters, `run`/`pause`/`resume`/
  `history` actions, pagination and configurable permissions.

See [docs/index.md](docs/index.md) for the full documentation.

## Usage example

Say your SaaS bills premium users on the **first day of every month**.
You already have a `User` model; this is all you need to schedule the
billing callback while the subscription is active:

```python
# billing/subscriptions.py
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from subscription.models import (
    Subscription, SubscriptionLine, SubscriptionEvent, Resource,
)


def subscribe_premium(user):
    user_ct = ContentType.objects.get_for_model(user)
    now = timezone.now()

    subscription = Subscription.objects.create(
        name=f'Premium - {user.username}',
        active=True,
        content_type=user_ct,
        object_pk=str(user.pk),
    )
    line = SubscriptionLine.objects.create(
        subscription=subscription,
        start=now,
        end=now + timedelta(days=365),   # one-year plan
    )
    # First day of every month, one day long.
    event = SubscriptionEvent.objects.create(
        subscription_line=line,
        start=now,
        end=now + timedelta(days=1),
        frequency='MONTHLY',
        by_month_day=[1],
    )
    Resource.objects.create(
        subscription_event=event,
        content_type=user_ct,
        object_pk=str(user.pk),
        callback='billing.tasks.charge_user',
    )
```

The callback receives the resource; the user is the generic relation
and `payload` holds the field snapshot:

```python
# billing/tasks.py
def charge_user(sender, instance, **kwargs):
    user = instance.content_object          # the subscribed User
    fields = instance.payload               # stored field values
    ...                                     # charge the card, send the invoice
```

To notify an external service instead, drop the `callback` and point
the resource at a webhook:

```python
    Resource.objects.create(
        subscription_event=event,
        content_type=user_ct,
        object_pk=str(user.pk),
        webhook_url='https://billing.example.com/hooks/premium/',
        webhook_secret='shared-secret',     # HMAC-SHA256 signature
    )
```

Finally, run the periodic dispatch (cron or Celery beat, see
[docs/index.md](docs/index.md)); it executes each resource once per
occurrence and keeps an audit trail in `ResourceExecution`:

```sh
python manage.py subscription_dispatch
```

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
