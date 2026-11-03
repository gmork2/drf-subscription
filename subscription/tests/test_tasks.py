from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from io import StringIO

from subscription.models import (
    Resource,
    ResourceExecution,
    Subscription,
    SubscriptionEvent,
    SubscriptionLine,
)
from subscription.tasks import dispatch_due_resources, execute_resource_now


def make_user(username):
    return User.objects.create_user(username=username, password='pass')


def make_chain(user, active=True):
    ct = ContentType.objects.get_for_model(User)
    now = timezone.now()
    subscription = Subscription.objects.create(
        name='test',
        active=active,
        content_type=ct,
        object_pk=str(user.pk),
    )
    line = SubscriptionLine.objects.create(
        subscription=subscription,
        start=now - timedelta(days=1),
        end=now + timedelta(days=1),
    )
    event = SubscriptionEvent.objects.create(
        subscription_line=line,
        start=now - timedelta(days=1),
        end=None,
    )
    resource = Resource.objects.create(
        subscription_event=event,
        content_type=ct,
        object_pk=str(user.pk),
        callback='dummy.path',
        active=True,
    )
    return resource


class ExecuteResourceNowTestCase(TestCase):
    @mock.patch('subscription.signals.import_string')
    def test_records_successful_execution(self, mock_import):
        callback = mock.Mock()
        mock_import.return_value = callback
        user = make_user('exec-ok')
        resource = make_chain(user)

        execution = execute_resource_now(resource, timezone.now())

        self.assertEqual(execution.status, ResourceExecution.STATUS_SUCCEEDED)
        self.assertIsNotNone(execution.finished_at)
        callback.assert_called_once()
        self.assertEqual(resource.executions.count(), 1)

    @mock.patch('subscription.signals.import_string')
    def test_records_failed_execution(self, mock_import):
        callback = mock.Mock(side_effect=RuntimeError('boom'))
        mock_import.return_value = callback
        user = make_user('exec-fail')
        resource = make_chain(user)

        execution = execute_resource_now(resource, timezone.now())

        self.assertEqual(execution.status, ResourceExecution.STATUS_FAILED)
        self.assertEqual(execution.error_message, 'boom')
        self.assertIsNotNone(execution.finished_at)

    @mock.patch('subscription.signals.import_string')
    def test_attempts_counts_previous_failures(self, mock_import):
        mock_import.return_value = mock.Mock(side_effect=RuntimeError('boom'))
        user = make_user('exec-attempts')
        resource = make_chain(user)
        scheduled_for = timezone.now()

        first = execute_resource_now(resource, scheduled_for)
        second = execute_resource_now(resource, scheduled_for)

        self.assertEqual(first.status, ResourceExecution.STATUS_FAILED)
        self.assertEqual(second.status, ResourceExecution.STATUS_FAILED)
        self.assertEqual(resource.executions.count(), 2)
        self.assertEqual(resource.executions.latest('created_at').attempts, 2)


class DispatchDueResourcesTestCase(TestCase):
    @mock.patch('subscription.signals.import_string')
    def test_enqueues_when_broker_available(self, mock_import):
        mock_import.return_value = mock.Mock()
        user = make_user('dispatch-enqueue')
        resource = make_chain(user)

        with mock.patch(
            'subscription.tasks.execute_resource.apply_async'
        ) as mock_apply:
            results = dispatch_due_resources()

        self.assertIn(resource.pk, results['dispatched'])
        mock_apply.assert_called_once()
        # Not executed inline: no execution record was created.
        self.assertEqual(resource.executions.count(), 0)

    @mock.patch('subscription.signals.import_string')
    def test_falls_back_to_synchronous_execution(self, mock_import):
        callback = mock.Mock()
        mock_import.return_value = callback
        user = make_user('dispatch-fallback')
        resource = make_chain(user)

        with mock.patch(
            'subscription.tasks.execute_resource.apply_async',
            side_effect=Exception('broker down'),
        ):
            results = dispatch_due_resources()

        self.assertIn(resource.pk, results['dispatched'])
        callback.assert_called_once()
        execution = resource.executions.get()
        self.assertEqual(execution.status, ResourceExecution.STATUS_SUCCEEDED)

    @mock.patch('subscription.signals.import_string')
    def test_skips_already_executed_occurrence(self, mock_import):
        callback = mock.Mock()
        mock_import.return_value = callback
        user = make_user('dispatch-skip')
        resource = make_chain(user)
        scheduled_for = resource.subscription_event.current.start

        ResourceExecution.objects.create(
            resource=resource,
            status=ResourceExecution.STATUS_SUCCEEDED,
            scheduled_for=scheduled_for,
        )

        with mock.patch(
            'subscription.tasks.execute_resource.apply_async'
        ) as mock_apply:
            results = dispatch_due_resources()

        self.assertIn(resource.pk, results['skipped'])
        callback.assert_not_called()
        mock_apply.assert_not_called()
        self.assertEqual(resource.executions.count(), 1)

    @mock.patch('subscription.signals.import_string')
    def test_ignores_inactive_resources(self, mock_import):
        callback = mock.Mock()
        mock_import.return_value = callback
        user = make_user('dispatch-inactive')
        resource = make_chain(user, active=False)

        results = dispatch_due_resources()

        self.assertEqual(results['dispatched'], [])
        callback.assert_not_called()


class SubscriptionDispatchCommandTestCase(TestCase):
    @mock.patch('subscription.signals.import_string')
    def test_command_runs_without_error(self, mock_import):
        mock_import.return_value = mock.Mock()
        user = make_user('command')
        make_chain(user)

        with mock.patch(
            'subscription.tasks.execute_resource.apply_async',
            side_effect=Exception('broker down'),
        ):
            out = StringIO()
            call_command('subscription_dispatch', stdout=out)

        self.assertIn('Dispatched:', out.getvalue())
