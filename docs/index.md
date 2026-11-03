# drf-subscription

A generic subscription app for Django: model any recurring or one-time
plan on top of any of your models, attach actions (callbacks or
webhooks) and let the engine run them when their period is active.

## Concepts

```
Subscription ──< SubscriptionLine ──< SubscriptionEvent ──< Resource ──< ResourceExecution
```

- **Subscription** — a named, generic relation to any model
  (the subscriber). Just a container for lines.
- **SubscriptionLine** — a start/end interval within a subscription.
- **SubscriptionEvent** — an interval that may repeat (RFC 5545
  recurrence rules) inside a line. One-time when `frequency` is empty.
- **Resource** — links an event to another model (the subject), stores
  a snapshot of its fields (`content_object_fields`), and defines the
  actions to run: a local `callback` (dotted path) and/or a
  `webhook_url`.
- **ResourceExecution** — audit record of every run attempt (status,
  timestamps, error, retry attempts).

## Quickstart

```sh
uv sync
uv run python manage.py migrate
```

Include the app in `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'subscription',
]
```

Mount the API (admin-only by default):

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path('api/', include('subscription.api')),
]
```

Create a daily subscription that runs a callback:

```python
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from subscription.models import (
    Subscription, SubscriptionLine, SubscriptionEvent, Resource,
)

user_ct = ContentType.objects.get_for_model(User)
now = timezone.now()

subscription = Subscription.objects.create(
    name='daily digest', active=True,
    content_type=user_ct, object_pk=str(user.pk),
)
line = SubscriptionLine.objects.create(
    subscription=subscription,
    start=now, end=now + timedelta(days=30),
)
event = SubscriptionEvent.objects.create(
    subscription_line=line,
    start=now, end=now + timedelta(hours=1),
    frequency='DAILY', interval=1,
)
resource = Resource.objects.create(
    subscription_event=event,
    content_type=user_ct, object_pk=str(user.pk),
    callback='myapp.tasks.send_digest',
)
```

## Recurrence (RFC 5545)

Recurrence is powered by
[python-dateutil](https://dateutil.readthedocs.io/) `rrule`. Fields on
`SubscriptionEvent`:

| Field | Meaning |
|---|---|
| `frequency` | `SECONDLY` … `YEARLY`; empty for one-time events |
| `interval` | every N periods (default 1) |
| `count` | total number of occurrences |
| `until` | latest start date (inclusive) |
| `by_month_day` | `[1..31]`; negative values count from month end |
| `by_week_day` | `['MO'..'SU']` or `[0..6]` (Monday first) |

A recurring event needs `end` (the duration of every occurrence) and a
bound: `until`, `count`, or a subscription line with an end date.
Occurrences never extend past the line end.

Useful helpers:

- `event.occurrences()` — deterministic generator of all occurrences
  (no mutation, no `now` dependency).
- `event.current` — the occurrence active right now (or `None`).
- `event.build_rrule()` — the underlying dateutil rule.
- `MonthlySubscriptionEvent` / `DailySubscriptionEvent` proxies set
  `frequency` for you.

The legacy `recurrence` duration field and the `events` property are
deprecated; `events` still works but emits a `DeprecationWarning`.

## Execution engine

Resources run their `callback` and/or `webhook_url` when their event
occurrence is active. Two complementary mechanisms:

1. **Signal accelerator** — when a related model is saved, ready
   resources run immediately. Signals are connected automatically after
   migrations (`AppConfig` + `post_migrate`, idempotent via
   `dispatch_uid`) and dynamically when a resource is created.
2. **Periodic dispatch** — the reliable path, driven by time:

```sh
uv run python manage.py subscription_dispatch
```

Run it from cron, or with Celery beat (see `sample/` for a working
setup):

```python
CELERY_BEAT_SCHEDULE = {
    'subscription_dispatch': {
        'task': 'sample.tasks.dispatch_subscription_resources',
        'schedule': crontab(minute='*/1'),
    },
}
```

When Celery is installed, resources are enqueued with automatic retry
(`SUBSCRIPTION_CALLBACK_MAX_RETRIES`, default 3, exponential backoff)
and the dispatch falls back to synchronous execution when the broker is
unreachable. Executions are idempotent: one successful run per
occurrence (`scheduled_for`).

## Webhooks

Set `webhook_url` on a resource to POST the JSON snapshot
(`content_object_fields`) to an external service. With `webhook_secret`,
the body is signed with HMAC-SHA256 and sent in the
`X-Subscription-Signature: sha256=<hex>` header; `webhook_headers`
adds extra headers and `X-Subscription-Resource` carries the resource
id.

Settings:

- `SUBSCRIPTION_WEBHOOK_TIMEOUT` — request timeout in seconds (default
  30).
- `SUBSCRIPTION_WEBHOOK_ALLOWED_HOSTS` — optional list of allowed
  webhook hostnames (SSRF guard; only `http(s)` URLs are valid).

## REST API

Admin-only by default; override with
`SUBSCRIPTION_PERMISSION_CLASSES` (list of dotted paths):

```python
SUBSCRIPTION_PERMISSION_CLASSES = [
    'rest_framework.permissions.IsAuthenticated',
]
```

Endpoints:

- `GET/POST /api/subscriptions/` — filter `?active=true|false&name=`
- `GET/PUT/PATCH/DELETE /api/subscriptions/{id}/`
- `/api/subscription-lines/` — filter `?subscription=&started=&finished=`
- `/api/subscription-events/` — filter `?line=&frequency=`
- `/api/resources/` — filter `?active=&subscription=`
- `POST /api/resources/{id}/run/` — run now (202 when queued)
- `POST /api/resources/{id}/pause/` / `resume/`
- `GET /api/resources/{id}/history/` — execution records

Responses are paginated (`?page=`, `?page_size=`).

OpenAPI schemas can be generated with
[drf-spectacular](https://drf-spectacular.readthedocs.io/) if desired;
it is not a dependency.

## Extending

- Subclass the concrete models via the abstract bases
  (`AbstractGenericObjectResource`, `AbstractInterval`,
  `AbstractPeriodicEvent`); the shipped models stay abstract when
  `subscription` is not in `INSTALLED_APPS`.
- Custom callbacks receive the resource: `def my_callback(sender,
  instance, **kwargs)`. `instance.content_object` is the subject and
  `instance.payload` its field snapshot.
