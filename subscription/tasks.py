"""
Scheduled execution engine for subscription resources.

The engine runs the callback (or webhook) of every active resource
whose event occurrence is currently active. Executions are recorded in
:class:`subscription.models.resource.ResourceExecution` for auditing and
idempotency (one successful execution per occurrence).

When Celery is installed, ``execute_resource`` becomes a Celery task
with automatic retry, and ``dispatch_due_resources`` enqueues work
asynchronously (falling back to synchronous execution when the broker
is unreachable). Without Celery the same functions run synchronously
and can be driven by the ``subscription_dispatch`` management command.
"""
import hashlib
import hmac
import json
import logging
import urllib.request
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from celery import shared_task

    CELERY_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on deployment
    CELERY_AVAILABLE = False


def _webhook_headers(resource) -> dict:
    headers = {
        'Content-Type': 'application/json',
        'X-Subscription-Resource': str(resource.pk),
    }
    extra = resource.webhook_headers or {}
    headers.update({str(k): str(v) for k, v in extra.items()})
    return headers


def send_webhook(resource, timeout: Optional[int] = None) -> None:
    """
    Send the resource payload to ``webhook_url`` as a signed POST.

    The request body is the JSON-encoded snapshot of the related
    object. When ``webhook_secret`` is set, the body is signed with
    HMAC-SHA256 and the signature is sent in the
    ``X-Subscription-Signature`` header.

    :param resource:
    :param timeout: request timeout in seconds (defaults to the
        ``SUBSCRIPTION_WEBHOOK_TIMEOUT`` setting or 30).
    :return:
    :raises Exception: on transport or HTTP errors; callers are
        responsible for retrying.
    """
    body = json.dumps(resource.payload).encode('utf-8')

    headers = _webhook_headers(resource)
    if resource.webhook_secret:
        signature = hmac.new(
            resource.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256,
        ).hexdigest()
        headers['X-Subscription-Signature'] = 'sha256=%s' % signature

    timeout = timeout if timeout is not None else getattr(
        settings, 'SUBSCRIPTION_WEBHOOK_TIMEOUT', 30
    )

    request = urllib.request.Request(
        resource.webhook_url,
        data=body,
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(
                'Webhook responded with status %s' % response.status
            )


def _run_resource_callback(resource) -> None:
    """
    Execute the callback and/or webhook configured on the resource.

    :param resource:
    :return:
    """
    from .signals import callback_receiver
    from .models import Resource

    if resource.webhook_url:
        send_webhook(resource)
    if resource.callback:
        callback_receiver(sender=Resource, instance=resource)


def execute_resource_now(resource, scheduled_for: Optional[datetime] = None):
    """
    Run a resource synchronously and record the outcome in a
    ``ResourceExecution``. Failures are recorded and never re-raised:
    the caller (or the Celery task) decides whether to retry.

    :param resource:
    :param scheduled_for: start of the occurrence this execution
        belongs to (idempotency key).
    :return: the execution record
    """
    from .models import ResourceExecution

    attempts = 1
    if scheduled_for is not None:
        attempts += ResourceExecution.objects.filter(
            resource=resource,
            scheduled_for=scheduled_for,
        ).count()

    execution = ResourceExecution.objects.create(
        resource=resource,
        status=ResourceExecution.STATUS_RUNNING,
        scheduled_for=scheduled_for,
        started_at=timezone.now(),
        attempts=attempts,
    )

    try:
        _run_resource_callback(resource)
    except Exception as exc:
        execution.status = ResourceExecution.STATUS_FAILED
        execution.error_message = str(exc)
        execution.finished_at = timezone.now()
        execution.save(update_fields=['status', 'error_message', 'finished_at'])
        logger.exception('Resource %s execution failed: %s', resource.pk, exc)
    else:
        execution.status = ResourceExecution.STATUS_SUCCEEDED
        execution.finished_at = timezone.now()
        execution.save(update_fields=['status', 'finished_at'])

    return execution


def run_resource(resource, scheduled_for: Optional[datetime] = None):
    """
    Execute a resource, asynchronously through Celery when available
    (with a synchronous fallback when the broker is unreachable).

    :param resource:
    :param scheduled_for: start of the occurrence this execution
        belongs to (idempotency key).
    :return: a (mode, execution) tuple; ``mode`` is ``'queued'`` (no
        execution record yet) or ``'executed'`` (the record).
    """
    if CELERY_AVAILABLE:
        try:
            execute_resource.apply_async(
                args=[resource.pk, scheduled_for],
                retry=False,
            )
        except Exception:
            logger.exception(
                'Unable to enqueue resource %s; running synchronously',
                resource.pk,
            )
        else:
            return 'queued', None

    return 'executed', execute_resource_now(resource, scheduled_for)


def _is_completed(resource, scheduled_for: datetime) -> bool:
    from .models import ResourceExecution

    return ResourceExecution.objects.filter(
        resource=resource,
        scheduled_for=scheduled_for,
        status=ResourceExecution.STATUS_SUCCEEDED,
    ).exists()


def dispatch_due_resources() -> dict:
    """
    Dispatch every active resource whose event occurrence is active and
    that has not been executed yet for that occurrence.

    :return: a summary with the dispatched, skipped and failed resource
        ids.
    """
    from .models import Resource, ResourceExecution

    results = {'dispatched': [], 'skipped': [], 'failed': []}

    resources = Resource.objects.active().select_related(
        'subscription_event__subscription_line__subscription'
    )
    for resource in resources:
        occurrence = resource.subscription_event.current
        if occurrence is None:
            continue

        scheduled_for = occurrence.start
        if _is_completed(resource, scheduled_for):
            results['skipped'].append(resource.pk)
            continue

        mode, execution = run_resource(resource, scheduled_for)
        if mode == 'executed' and \
                execution.status == ResourceExecution.STATUS_FAILED:
            results['failed'].append(resource.pk)
        else:
            results['dispatched'].append(resource.pk)

    return results


if CELERY_AVAILABLE:
    @shared_task(
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=getattr(
            settings, 'SUBSCRIPTION_CALLBACK_MAX_RETRIES', 3
        ),
    )
    def execute_resource(self, resource_id, scheduled_for=None):
        """
        Celery task wrapper around :func:`execute_resource_now`. Failed
        executions are re-raised so the task is retried automatically.
        """
        from .models import Resource, ResourceExecution

        resource = Resource.objects.get(pk=resource_id)
        execution = execute_resource_now(resource, scheduled_for)
        if execution.status == ResourceExecution.STATUS_FAILED:
            raise Exception(execution.error_message)
else:
    def execute_resource(resource_id, scheduled_for=None):
        """
        Synchronous fallback used when Celery is not installed.
        """
        from .models import Resource

        resource = Resource.objects.get(pk=resource_id)
        execute_resource_now(resource, scheduled_for)
